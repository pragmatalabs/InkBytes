<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Minimal user/role management (B2, RBAC — ADR-0005). Admin-only (gated by the
 * `role:admin` middleware on the routes).
 *
 * Lists backoffice.users and lets an admin change a user's role. Role changes
 * are audited via the B1 recorder. A safeguard blocks demoting the last
 * remaining admin so the Backoffice can never be locked out of its admin-only
 * surfaces (keys, settings, audit log, this screen).
 */
class UserController extends Controller
{
    public function index(): Response
    {
        return Inertia::render('Users/Index', [
            'users' => User::query()
                ->orderBy('name')
                ->get()
                ->map(fn (User $user): array => $this->present($user))
                ->values(),
            'roles' => User::ROLES,
        ]);
    }

    public function updateRole(Request $request, User $user): RedirectResponse
    {
        $validated = $request->validate([
            'role' => ['required', 'string', Rule::in(User::ROLES)],
        ]);

        $newRole = $validated['role'];
        $oldRole = $user->role;

        if ($newRole === $oldRole) {
            return redirect()
                ->route('users.index')
                ->with('success', "{$user->name} is already a {$newRole}.");
        }

        // Last-admin safeguard: never leave the Backoffice with zero admins.
        $demotingAnAdmin = $oldRole === User::ROLE_ADMIN && $newRole !== User::ROLE_ADMIN;

        if ($demotingAnAdmin && $this->adminCount() <= 1) {
            return redirect()
                ->route('users.index')
                ->with('error', 'Cannot remove the last admin. Promote another user to admin first.');
        }

        $user->update(['role' => $newRole]);

        AuditLog::record(
            'user.role_changed',
            'user',
            (string) $user->id,
            ['role' => $oldRole],
            ['role' => $newRole],
        );

        return redirect()
            ->route('users.index')
            ->with('success', "{$user->name} is now a {$newRole}.");
    }

    private function adminCount(): int
    {
        return User::query()->where('role', User::ROLE_ADMIN)->count();
    }

    /**
     * @return array<string, mixed>
     */
    private function present(User $user): array
    {
        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'role' => $user->role,
            'created_at' => $user->created_at?->toIso8601String(),
        ];
    }
}
