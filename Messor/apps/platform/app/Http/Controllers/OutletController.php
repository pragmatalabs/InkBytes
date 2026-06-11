<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Concerns\PaginatesQueries;
use App\Models\AuditLog;
use App\Models\Outlet;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\StreamedResponse;
use Throwable;

/**
 * CRUD for the shared `public.outlets` catalogue.
 *
 * Curator owns the table DDL (ADR-0003); this controller only operates on
 * rows. Curator's startup seed is seed-if-empty, so admin edits here are not
 * overwritten on a Curator restart.
 */
class OutletController extends Controller
{
    use PaginatesQueries;

    private const VERTICALS = ['general', 'business', 'tech', 'politics'];

    /**
     * Allowed outlet regions — derived from config/regions.php (single source
     * of truth + naming rule). Extend regions there, not here.
     *
     * @return list<string>
     */
    private function regions(): array
    {
        return config('regions.allowed', ['global']);
    }

    /** Columns the outlet list may sort on (B7). */
    private const SORTABLE = ['display_name', 'id', 'region', 'language', 'vertical', 'priority', 'active'];

    public function index(Request $request): Response
    {
        $stats = $this->outletStats();

        // B7: server-side search (name/slug/url) + allowlisted sort. The catalogue
        // is small (~31 today) so we render the full filtered set without
        // pagination — keeping bulk-select-across-the-list simple — but search and
        // sort run in SQL so they scale and stay consistent with the other lists.
        [$sort, $dir] = $this->resolveSort($request, self::SORTABLE, 'priority', 'asc');

        $query = Outlet::query();
        $this->applySearch($query, $request->query('q'), ['name', 'id', 'url', 'display_name']);

        if ($sort !== null) {
            $query->orderBy($sort, $dir);
            // Stable secondary order so equal sort keys are deterministic.
            if ($sort !== 'display_name') {
                $query->orderBy('display_name');
            }
        }

        return Inertia::render('Outlets/Index', [
            'outlets' => $query
                ->get()
                ->map(function (Outlet $outlet) use ($stats): array {
                    $row = $stats[$outlet->id] ?? null;

                    return $this->present($outlet) + [
                        'article_count' => $row['article_count'] ?? 0,
                        'events_contributed' => $row['events_contributed'] ?? 0,
                        'last_scraped' => $row['last_scraped'] ?? null,
                    ];
                })
                ->values(),
            'options' => $this->options(),
            'filters' => $this->listState($request, $sort, $dir, $this->resolvePerPage($request, 25)),
        ]);
    }

    /**
     * Bulk activate / deactivate / delete selected outlets (B7).
     *
     * Operator+ (gated in routes), audited (B1). The action is applied in a
     * single transaction over the validated id list; each affected row gets a
     * per-row audit entry (outlet.updated / outlet.deleted) PLUS a summary row
     * (outlet.bulk_activated / outlet.bulk_deactivated / outlet.bulk_deleted)
     * carrying the affected ids — so the audit trail shows both the rollup and
     * the individual changes. Never alters DDL.
     */
    public function bulk(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'action' => ['required', Rule::in(['activate', 'deactivate', 'delete'])],
            'ids' => ['required', 'array', 'min:1'],
            'ids.*' => ['string', 'max:120'],
        ]);

        $action = $validated['action'];
        // De-dupe + only operate on ids that actually exist.
        $ids = array_values(array_unique($validated['ids']));
        $outlets = Outlet::query()->whereIn('id', $ids)->get();

        if ($outlets->isEmpty()) {
            return back()->with('error', 'No matching outlets to update.');
        }

        $affected = [];

        DB::transaction(function () use ($action, $outlets, &$affected): void {
            foreach ($outlets as $outlet) {
                $id = (string) $outlet->id;

                if ($action === 'delete') {
                    $before = $this->present($outlet);
                    $outlet->delete();
                    AuditLog::record('outlet.deleted', 'outlet', $id, $before, null);
                    $affected[] = $id;

                    continue;
                }

                $next = $action === 'activate';
                // Skip no-op toggles so the audit trail isn't noise.
                if ((bool) $outlet->active === $next) {
                    continue;
                }

                $before = $this->present($outlet);
                $outlet->active = $next;
                $outlet->save();
                AuditLog::record('outlet.updated', 'outlet', $id, $before, $this->present($outlet->refresh()));
                $affected[] = $id;
            }
        });

        $summaryAction = match ($action) {
            'activate' => 'outlet.bulk_activated',
            'deactivate' => 'outlet.bulk_deactivated',
            'delete' => 'outlet.bulk_deleted',
        };

        AuditLog::record($summaryAction, 'outlet', null, null, [
            'ids' => $affected,
            'count' => count($affected),
        ]);

        $verb = match ($action) {
            'activate' => 'activated',
            'deactivate' => 'deactivated',
            'delete' => 'deleted',
        };

        return redirect()
            ->route('outlets.index')
            ->with('success', count($affected)." outlet(s) {$verb}.");
    }

    /**
     * Per-outlet harvest stats, joined cross-schema from Curator's
     * `public.articles` (ADR-0003 — read-only; the Backoffice never writes it).
     *
     * Join key: `public.articles.outlet_id = public.outlets.id` (the slug).
     *
     * NOTE: this is article *volume + recency + events contributed*, not a
     * success rate. Curator's `public.articles` only holds successfully-scraped
     * articles; scrape attempts/failures live in Messor's run history (a future
     * B4), so a true success rate is not computable here.
     *
     * Defensive: if `public.articles` is unreachable (a non-Postgres test DB, or
     * Curator's schema not yet migrated) we return an empty map and the page
     * still renders with null/0 stats — mirrors the moderation/cost fallbacks.
     *
     * @return array<string, array{article_count:int, events_contributed:int, last_scraped:?string}>
     */
    private function outletStats(): array
    {
        try {
            $rows = DB::table('public.articles')
                ->select('outlet_id')
                ->selectRaw('count(*) AS article_count')
                ->selectRaw('max(scraped_at) AS last_scraped')
                ->selectRaw('count(DISTINCT event_id) AS events_contributed')
                ->groupBy('outlet_id')
                ->get();
        } catch (Throwable $e) {
            return [];
        }

        $stats = [];

        foreach ($rows as $row) {
            $stats[$row->outlet_id] = [
                'article_count' => (int) $row->article_count,
                'events_contributed' => (int) $row->events_contributed,
                'last_scraped' => $row->last_scraped
                    ? Carbon::parse($row->last_scraped)->toIso8601String()
                    : null,
            ];
        }

        return $stats;
    }

    public function store(Request $request): RedirectResponse
    {
        $data = $this->validateOutlet($request, null);

        $outlet = Outlet::query()->create($data);

        AuditLog::record('outlet.created', 'outlet', (string) $outlet->id, null, $this->present($outlet));

        return redirect()
            ->route('outlets.index')
            ->with('success', "Outlet \"{$data['display_name']}\" created.");
    }

    public function update(Request $request, string $outlet): RedirectResponse
    {
        $model = Outlet::query()->findOrFail($outlet);

        $before = $this->present($model);

        $data = $this->validateOutlet($request, $model->id);

        // The slug (id) is the natural key Curator/Messor join on — keep it stable.
        unset($data['id']);
        $model->update($data);

        AuditLog::record('outlet.updated', 'outlet', (string) $model->id, $before, $this->present($model->refresh()));

        return redirect()
            ->route('outlets.index')
            ->with('success', "Outlet \"{$model->display_name}\" updated.");
    }

    public function destroy(string $outlet): RedirectResponse
    {
        $model = Outlet::query()->findOrFail($outlet);
        $name = $model->display_name;
        $before = $this->present($model);
        $id = (string) $model->id;
        $model->delete();

        AuditLog::record('outlet.deleted', 'outlet', $id, $before, null);

        return redirect()
            ->route('outlets.index')
            ->with('success', "Outlet \"{$name}\" deleted.");
    }

    /**
     * Export every `public.outlets` row as a JSON download (B10).
     *
     * Read-only, so any authenticated role may call it. The payload is shaped to
     * match the Messor seed file `apps/scraper/data/outlets/outlets.json` exactly
     * (id, name, display_name, url, region, language, vertical, active, priority —
     * NO timestamps), so an exported file round-trips back through import and can
     * serve as / replace the seed. Streamed to keep memory flat. We never write
     * the seed file on disk — this is purely a download.
     */
    public function export(): StreamedResponse
    {
        $filename = sprintf('outlets_%s.json', Carbon::now()->format('Y-m-d_His'));

        return response()->streamDownload(function (): void {
            $rows = Outlet::query()
                ->orderBy('priority')
                ->orderBy('id')
                ->get()
                ->map(fn (Outlet $outlet): array => $this->seedShape($outlet))
                ->values()
                ->all();

            // Pretty-printed + unescaped slashes so the file is human-diffable and
            // byte-comparable with the hand-maintained seed.
            echo json_encode($rows, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
        }, $filename, [
            'Content-Type' => 'application/json',
            'Cache-Control' => 'no-store, no-cache',
        ]);
    }

    /**
     * Step 1 of import (B10): parse + validate an uploaded JSON file and return a
     * diff PREVIEW (create / update / errors) WITHOUT writing anything.
     *
     * Operator+ (gated in routes). The whole file is rejected with a clear error
     * if it is not a JSON array of objects. Each entry is validated against the
     * same enums/ranges as the CRUD; invalid rows are reported per-row but do not
     * block the valid ones — the admin sees the full diff and explicitly Applies.
     *
     * The validated, normalised entries are echoed back in the preview so the
     * confirm step (apply) re-validates the exact same payload rather than
     * trusting a round-trip of the raw upload.
     */
    public function importPreview(Request $request): RedirectResponse
    {
        $request->validate([
            'file' => ['required', 'file', 'max:5120', 'mimetypes:application/json,text/plain,text/json'],
        ]);

        $raw = $request->file('file')->get();
        $decoded = json_decode($raw, true);

        if (! is_array($decoded) || ! array_is_list($decoded)) {
            return back()->with('error', 'Import failed: the file must be a JSON array of outlet objects.');
        }

        $preview = $this->buildPreview($decoded);

        return back()->with('importPreview', $preview);
    }

    /**
     * Step 2 of import (B10): apply the upsert-by-id of the previously previewed,
     * validated rows. Operator+ (gated in routes), audited (B1).
     *
     * Re-validates every row server-side (never trusts the client preview), then
     * upserts ONLY the known columns into `public.outlets`, stamping updated_at.
     * Never adds/alters columns. Wrapped in a transaction so a partial failure
     * rolls back. Records an `outlet.imported` summary plus per-row
     * `outlet.created` / `outlet.updated` audit rows.
     */
    public function importApply(Request $request): RedirectResponse
    {
        $request->validate([
            'outlets' => ['required', 'array', 'min:1'],
        ]);

        $preview = $this->buildPreview($request->input('outlets'));

        if ($preview['errors'] !== []) {
            return back()->with('error', 'Import aborted: '.count($preview['errors']).' invalid row(s). Re-upload and fix them first.');
        }

        $created = 0;
        $updated = 0;
        $now = Carbon::now();

        DB::transaction(function () use ($preview, &$created, &$updated, $now): void {
            foreach ($preview['rows'] as $entry) {
                $data = $entry['data'];
                $existing = Outlet::query()->find($data['id']);

                if ($existing === null) {
                    $model = new Outlet;
                    $model->forceFill($data);
                    $model->created_at = $now;
                    $model->updated_at = $now;
                    $model->save();
                    $created++;

                    AuditLog::record('outlet.created', 'outlet', (string) $model->id, null, $this->present($model));
                } else {
                    $before = $this->present($existing);
                    // Keep the natural key stable; never rewrite the slug on update.
                    $changes = $data;
                    unset($changes['id']);
                    $existing->forceFill($changes);
                    $existing->updated_at = $now;
                    $existing->save();
                    $updated++;

                    AuditLog::record('outlet.updated', 'outlet', (string) $existing->id, $before, $this->present($existing->refresh()));
                }
            }
        });

        AuditLog::record('outlet.imported', 'outlet', null, null, [
            'created' => $created,
            'updated' => $updated,
        ]);

        return redirect()
            ->route('outlets.index')
            ->with('success', "Import applied: {$created} created, {$updated} updated.");
    }

    /**
     * Validate a list of decoded import entries into a create/update/error diff.
     *
     * Pure (no writes): looks up existing ids to classify create vs update, runs
     * each entry through the shared enum/range rules, and returns normalised data
     * for the apply step. Used by BOTH preview and apply so the two can never
     * diverge.
     *
     * @param  array<int, mixed>  $entries
     * @return array{rows: array<int, array{action:string, data:array<string,mixed>}>, summary: array{create:int, update:int, error:int, total:int}, errors: array<int, array{index:int, id:?string, messages:array<int,string>}>}
     */
    private function buildPreview(array $entries): array
    {
        // Existing ids (lower-cased) classify create vs update. Defensive: if
        // public.outlets is unreachable (non-Postgres test DB without the table)
        // we treat everything as a create — the apply path is what actually writes.
        try {
            $existingIds = Outlet::query()->pluck('id')->map(fn ($id) => Str::lower((string) $id))->all();
        } catch (Throwable $e) {
            $existingIds = [];
        }
        $existingIds = array_flip($existingIds);

        $rows = [];
        $errors = [];
        $create = 0;
        $update = 0;

        foreach ($entries as $index => $entry) {
            if (! is_array($entry)) {
                $errors[] = ['index' => $index, 'id' => null, 'messages' => ['Entry must be a JSON object.']];

                continue;
            }

            // Normalise the slug + language before validation so casing matches
            // what we store and how we classify create vs update.
            if (isset($entry['id']) && is_string($entry['id'])) {
                $entry['id'] = Str::lower(trim($entry['id']));
            }
            if (isset($entry['language']) && is_string($entry['language'])) {
                $entry['language'] = Str::lower(trim($entry['language']));
            }

            $validator = Validator::make($entry, $this->importRules());

            if ($validator->fails()) {
                $errors[] = [
                    'index' => $index,
                    'id' => is_string($entry['id'] ?? null) ? $entry['id'] : null,
                    'messages' => $validator->errors()->all(),
                ];

                continue;
            }

            $data = $validator->validated();
            $data['active'] = (bool) $data['active'];
            $data['priority'] = (int) $data['priority'];

            $isUpdate = isset($existingIds[$data['id']]);
            $isUpdate ? $update++ : $create++;

            $rows[] = [
                'action' => $isUpdate ? 'update' : 'create',
                'data' => $data,
            ];
        }

        return [
            'rows' => $rows,
            'errors' => $errors,
            'summary' => [
                'create' => $create,
                'update' => $update,
                'error' => count($errors),
                'total' => count($entries),
            ],
        ];
    }

    /**
     * Validation rules for a single imported outlet entry. Mirrors the CRUD
     * rules (same enums/ranges) but is uniqueness-agnostic: import is an
     * upsert-by-id, so a slug that already exists is an UPDATE, not a conflict.
     *
     * @return array<string, mixed>
     */
    private function importRules(): array
    {
        return [
            'id' => ['required', 'string', 'max:120', 'regex:/^[a-z0-9][a-z0-9_-]*$/'],
            'name' => ['required', 'string', 'max:200'],
            'display_name' => ['required', 'string', 'max:200'],
            'url' => ['required', 'url', 'max:500'],
            'region' => ['required', Rule::in($this->regions())],
            'language' => ['required', 'string', 'max:10'],
            'vertical' => ['required', Rule::in(self::VERTICALS)],
            'priority' => ['required', 'integer', 'between:1,3'],
            'active' => ['required', 'boolean'],
        ];
    }

    /**
     * The round-trip seed shape (matches apps/scraper/data/outlets/outlets.json):
     * the known data columns only, no timestamps. Key order mirrors the seed.
     *
     * @return array<string, mixed>
     */
    private function seedShape(Outlet $outlet): array
    {
        return [
            'id' => $outlet->id,
            'name' => $outlet->name,
            'display_name' => $outlet->display_name,
            'url' => $outlet->url,
            'region' => $outlet->region,
            'language' => $outlet->language,
            'vertical' => $outlet->vertical,
            'active' => (bool) $outlet->active,
            'priority' => (int) $outlet->priority,
        ];
    }

    /**
     * Validate and normalise an outlet payload.
     *
     * @param  string|null  $existingId  current id when updating; null on create
     * @return array<string, mixed>
     */
    private function validateOutlet(Request $request, ?string $existingId): array
    {
        $validated = $request->validate([
            'id' => [
                $existingId === null ? 'required' : 'nullable',
                'string',
                'max:120',
                'regex:/^[a-z0-9][a-z0-9_-]*$/',
                Rule::unique(Outlet::class, 'id')->ignore($existingId, 'id'),
            ],
            'name' => ['required', 'string', 'max:200'],
            'display_name' => ['required', 'string', 'max:200'],
            'url' => ['required', 'url', 'max:500'],
            'feed_url' => ['nullable', 'url', 'max:500'],
            'min_word_count' => ['nullable', 'integer', 'between:1,500'],
            'pulse' => ['nullable', 'boolean'],
            'region' => ['required', Rule::in($this->regions())],
            'language' => ['required', 'string', 'max:10'],
            'vertical' => ['required', Rule::in(self::VERTICALS)],
            'priority' => ['required', 'integer', 'between:1,3'],
            'active' => ['required', 'boolean'],
        ]);

        if ($existingId === null) {
            $validated['id'] = Str::lower($validated['id']);
        }

        $validated['language'] = Str::lower($validated['language']);

        return $validated;
    }

    /**
     * @return array<string, mixed>
     */
    private function present(Outlet $outlet): array
    {
        return [
            'id' => $outlet->id,
            'name' => $outlet->name,
            'display_name' => $outlet->display_name,
            'url' => $outlet->url,
            'feed_url' => $outlet->feed_url,
            'min_word_count' => $outlet->min_word_count !== null ? (int) $outlet->min_word_count : null,
            'pulse' => (bool) $outlet->pulse,
            'region' => $outlet->region,
            'language' => $outlet->language,
            'vertical' => $outlet->vertical,
            'active' => (bool) $outlet->active,
            'priority' => (int) $outlet->priority,
            'updated_at' => $outlet->updated_at?->toIso8601String(),
        ];
    }

    /**
     * @return array<string, array<int, string>>
     */
    private function options(): array
    {
        return [
            'regions' => $this->regions(),
            'verticals' => self::VERTICALS,
        ];
    }
}
