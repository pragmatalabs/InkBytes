<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Request;
use Throwable;

/**
 * AuditLog — append-only record of state-changing admin actions (B1, Gap 3).
 *
 * Backoffice-owned (ADR-0001 / ADR-0003); lives in the `backoffice` schema.
 *
 * Write via the static {@see AuditLog::record()} helper from each mutation. The
 * write is BEST-EFFORT: any failure is caught and logged as a warning so an
 * audit hiccup can never 500 the underlying admin action.
 *
 * SECURITY: `before` / `after` must never contain secret material. Callers
 * dealing with secrets (e.g. ApiKeyController) pass only safe projections
 * (provider / label / masked last-4 / active) — never the raw or encrypted key.
 */
class AuditLog extends Model
{
    protected $table = 'audit_logs';

    // created_at is set explicitly at write time; there is no updated_at.
    public $timestamps = false;

    protected $fillable = [
        'actor_id',
        'actor_name',
        'actor_email',
        'action',
        'target_type',
        'target_id',
        'before',
        'after',
        'ip',
        'created_at',
    ];

    protected $casts = [
        'actor_id' => 'integer',
        'before' => 'array',
        'after' => 'array',
        'created_at' => 'datetime',
    ];

    /**
     * Record an audited action. Snapshots the authenticated user and request IP.
     *
     * Best-effort: never throws. A failure is logged and swallowed so the
     * underlying mutation still completes.
     *
     * @param  string       $action      e.g. "outlet.updated"
     * @param  string       $targetType  e.g. "outlet"
     * @param  string|null  $targetId    the target's natural id
     * @param  array<string, mixed>|null  $before  pre-change snapshot (secret-free)
     * @param  array<string, mixed>|null  $after   post-change snapshot (secret-free)
     */
    public static function record(
        string $action,
        string $targetType,
        ?string $targetId = null,
        ?array $before = null,
        ?array $after = null,
    ): void {
        try {
            $user = Auth::user();

            static::query()->create([
                'actor_id' => $user?->getKey(),
                'actor_name' => $user?->name,
                'actor_email' => $user?->email,
                'action' => $action,
                'target_type' => $targetType,
                'target_id' => $targetId,
                'before' => $before,
                'after' => $after,
                'ip' => Request::ip(),
                'created_at' => now(),
            ]);
        } catch (Throwable $e) {
            // An audit failure must never break the audited action.
            Log::warning('AuditLog::record failed', [
                'action' => $action,
                'target_type' => $targetType,
                'target_id' => $targetId,
                'error' => $e->getMessage(),
            ]);
        }
    }
}
