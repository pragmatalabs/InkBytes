<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Database\Factories\UserFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;

/**
 * Backoffice user — B2 (RBAC).
 *
 * `role` is one of {@see User::ROLES}. It is NOT hidden, so it rides along on
 * the Inertia-shared `$request->user()` and the React layer can hide/disable
 * gated controls. The server-side `role` middleware is the real gate; the UI
 * hiding is cosmetic only. See ADR-0005.
 */
#[Fillable(['name', 'email', 'password', 'role'])]
#[Hidden(['password', 'remember_token'])]
class User extends Authenticatable
{
    /** @use HasFactory<UserFactory> */
    use HasFactory, Notifiable;

    public const ROLE_ADMIN = 'admin';

    public const ROLE_OPERATOR = 'operator';

    public const ROLE_VIEWER = 'viewer';

    /** @var array<int, string> */
    public const ROLES = [self::ROLE_ADMIN, self::ROLE_OPERATOR, self::ROLE_VIEWER];

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
        ];
    }

    /** Admin — full access including keys, settings, audit log, user management. */
    public function isAdmin(): bool
    {
        return $this->role === self::ROLE_ADMIN;
    }

    /** Operator (or admin) — may run outlet / scraping / moderation mutations. */
    public function isOperator(): bool
    {
        return $this->role === self::ROLE_OPERATOR || $this->isAdmin();
    }

    /** Viewer — read-only. True only for the bare viewer role. */
    public function isViewer(): bool
    {
        return $this->role === self::ROLE_VIEWER;
    }

    /** Does this user hold (at least) the given role tier? */
    public function hasRole(string $role): bool
    {
        return match ($role) {
            self::ROLE_ADMIN => $this->isAdmin(),
            self::ROLE_OPERATOR => $this->isOperator(),
            self::ROLE_VIEWER => true, // any authenticated user clears the viewer tier
            default => false,
        };
    }
}
