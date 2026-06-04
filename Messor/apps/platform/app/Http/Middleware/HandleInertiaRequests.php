<?php

namespace App\Http\Middleware;

use App\Models\Alert;
use Illuminate\Http\Request;
use Inertia\Middleware;
use Throwable;

class HandleInertiaRequests extends Middleware
{
    /**
     * The root template that is loaded on the first page visit.
     *
     * @var string
     */
    protected $rootView = 'app';

    /**
     * Determine the current asset version.
     */
    public function version(Request $request): ?string
    {
        return parent::version($request);
    }

    /**
     * Define the props that are shared by default.
     *
     * @return array<string, mixed>
     */
    public function share(Request $request): array
    {
        $user = $request->user();

        return [
            ...parent::share($request),
            'auth' => [
                // `role` is not hidden on the model, so it rides along here.
                // The React layer reads `auth.user.role` to hide/disable gated
                // controls (cosmetic — the `role` middleware is the real gate).
                // See ADR-0005.
                'user' => $user,
            ],
            // B11: open-alert count for the header bell badge. Lazy closure so
            // the COUNT only runs when needed; best-effort (an unreachable/
            // un-migrated alerts table degrades to 0 rather than 500-ing every
            // page). Null when unauthenticated.
            'alerts' => [
                'open_count' => fn (): int => $user === null ? 0 : $this->openAlertCount(),
            ],
            'flash' => [
                'success' => fn () => $request->session()->get('success'),
                'error' => fn () => $request->session()->get('error'),
                // Outlet import diff preview (B10): create/update/error counts +
                // rows, flashed by OutletController@importPreview for the confirm
                // step. Transient — only present on the redirect after an upload.
                'importPreview' => fn () => $request->session()->get('importPreview'),
            ],
        ];
    }

    /** Open-alert count, degrading to 0 if the alerts table is unreachable. */
    private function openAlertCount(): int
    {
        try {
            return Alert::openCount();
        } catch (Throwable $e) {
            return 0;
        }
    }
}
