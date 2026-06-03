<?php

namespace App\Http\Controllers;

use App\Models\Outlet;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

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
        return Inertia::render('Outlets/Index', [
            'outlets' => Outlet::query()
                ->orderBy('priority')
                ->orderBy('display_name')
                ->get()
                ->map(fn (Outlet $outlet): array => $this->present($outlet))
                ->values(),
            'options' => $this->options(),
        ]);
    }

    public function store(Request $request): RedirectResponse
    {
        $data = $this->validateOutlet($request, null);

        Outlet::query()->create($data);

        return redirect()
            ->route('outlets.index')
            ->with('success', "Outlet \"{$data['display_name']}\" created.");
    }

    public function update(Request $request, string $outlet): RedirectResponse
    {
        $model = Outlet::query()->findOrFail($outlet);

        $data = $this->validateOutlet($request, $model->id);

        // The slug (id) is the natural key Curator/Messor join on — keep it stable.
        unset($data['id']);
        $model->update($data);

        return redirect()
            ->route('outlets.index')
            ->with('success', "Outlet \"{$model->display_name}\" updated.");
    }

    public function destroy(string $outlet): RedirectResponse
    {
        $model = Outlet::query()->findOrFail($outlet);
        $name = $model->display_name;
        $model->delete();

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
