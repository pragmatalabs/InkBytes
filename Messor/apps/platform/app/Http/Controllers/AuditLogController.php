<?php

namespace App\Http\Controllers;

use App\Models\AuditLog;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Read-only Audit Log viewer (B1, Gap 3).
 *
 * Lists backoffice.audit_logs newest-first with server-side pagination and
 * optional filters by `action` and/or `actor` (matches actor_name/email). This
 * screen never mutates anything — it only reads the append-only audit trail.
 */
class AuditLogController extends Controller
{
    private const PER_PAGE = 25;

    public function index(Request $request): Response
    {
        $filters = [
            'action' => trim((string) $request->query('action', '')),
            'actor' => trim((string) $request->query('actor', '')),
        ];

        $query = AuditLog::query()->orderByDesc('created_at')->orderByDesc('id');

        if ($filters['action'] !== '') {
            $query->where('action', $filters['action']);
        }

        if ($filters['actor'] !== '') {
            $needle = '%'.$filters['actor'].'%';
            $query->where(function ($q) use ($needle) {
                $q->where('actor_name', 'like', $needle)
                    ->orWhere('actor_email', 'like', $needle);
            });
        }

        $logs = $query
            ->paginate(self::PER_PAGE)
            ->withQueryString()
            ->through(fn (AuditLog $log): array => $this->present($log));

        return Inertia::render('AuditLog/Index', [
            'logs' => $logs,
            'filters' => $filters,
            // Distinct action values for the filter dropdown.
            'actions' => AuditLog::query()
                ->select('action')
                ->distinct()
                ->orderBy('action')
                ->pluck('action')
                ->values(),
        ]);
    }

    /**
     * @return array<string, mixed>
     */
    private function present(AuditLog $log): array
    {
        return [
            'id' => $log->id,
            'actor_name' => $log->actor_name,
            'actor_email' => $log->actor_email,
            'action' => $log->action,
            'target_type' => $log->target_type,
            'target_id' => $log->target_id,
            'before' => $log->before,
            'after' => $log->after,
            'ip' => $log->ip,
            'created_at' => $log->created_at?->toIso8601String(),
        ];
    }
}
