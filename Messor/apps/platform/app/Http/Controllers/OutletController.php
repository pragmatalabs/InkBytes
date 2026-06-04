<?php

namespace App\Http\Controllers;

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
    private const REGIONS = ['global', 'latam-dr', 'latam-mx', 'latam-co', 'latam-ar'];

    private const VERTICALS = ['general', 'business', 'tech', 'politics'];

    public function index(): Response
    {
        $stats = $this->outletStats();

        return Inertia::render('Outlets/Index', [
            'outlets' => Outlet::query()
                ->orderBy('priority')
                ->orderBy('display_name')
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
        ]);
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
            'region' => ['required', Rule::in(self::REGIONS)],
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
                Rule::unique('public.outlets', 'id')->ignore($existingId, 'id'),
            ],
            'name' => ['required', 'string', 'max:200'],
            'display_name' => ['required', 'string', 'max:200'],
            'url' => ['required', 'url', 'max:500'],
            'region' => ['required', Rule::in(self::REGIONS)],
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
            'regions' => self::REGIONS,
            'verticals' => self::VERTICALS,
        ];
    }
}
