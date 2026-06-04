<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\Outlet;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;
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
                    ? \Illuminate\Support\Carbon::parse($row->last_scraped)->toIso8601String()
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
