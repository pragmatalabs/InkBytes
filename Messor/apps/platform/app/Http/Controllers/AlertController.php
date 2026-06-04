<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Concerns\PaginatesQueries;
use App\Models\Alert;
use App\Models\AuditLog;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Alerts (B11) — in-app view of operational alerts raised by the scheduled
 * `alerts:evaluate` evaluator, plus the acknowledge action.
 *
 * The list is read-only and visible to ALL authenticated roles (it is the bell
 * target). Acknowledge is OPERATOR+ (gated in routes/web.php) and audited (B1
 * `alert.acknowledged`). The evaluator owns creation; there is no create/edit/
 * delete surface here.
 */
class AlertController extends Controller
{
    use PaginatesQueries;

    /** Columns the alerts list may sort on (B7). */
    private const SORTABLE = ['created_at', 'severity', 'type', 'status'];

    public function index(Request $request): Response
    {
        [$sort, $dir] = $this->resolveSort($request, self::SORTABLE, 'created_at', 'desc');
        $perPage = $this->resolvePerPage($request, 25);

        $status = (string) $request->query('status', '');
        $type = (string) $request->query('type', '');

        $query = Alert::query();

        // Open-first by default so the actionable ones surface; otherwise honour
        // the requested sort.
        if ($sort === 'created_at') {
            $query->orderByRaw("(status = 'open') desc")
                ->orderBy('created_at', $dir);
        } else {
            $this->applySort($query, $sort, $dir);
            $query->orderByDesc('created_at');
        }

        if (in_array($status, [Alert::STATUS_OPEN, Alert::STATUS_ACKNOWLEDGED], true)) {
            $query->where('status', $status);
        }

        if (in_array($type, $this->types(), true)) {
            $query->where('type', $type);
        }

        $this->applySearch($query, $request->query('q'), ['title', 'message', 'dedup_key']);

        $alerts = $query
            ->paginate($perPage)
            ->withQueryString()
            ->through(fn (Alert $alert): array => $this->present($alert));

        return Inertia::render('Alerts/Index', [
            'alerts' => $alerts,
            'filters' => [
                ...$this->listState($request, $sort, $dir, $perPage),
                'status' => $status,
                'type' => $type,
            ],
            'options' => [
                'types' => $this->types(),
                'statuses' => [Alert::STATUS_OPEN, Alert::STATUS_ACKNOWLEDGED],
            ],
            'openCount' => Alert::openCount(),
        ]);
    }

    /**
     * Acknowledge an open alert. Operator+ (gated in routes), audited (B1).
     * Flips status → acknowledged and snapshots who/when. A no-op (already
     * acknowledged) returns without re-auditing.
     */
    public function acknowledge(Request $request, Alert $alert): RedirectResponse
    {
        if ($alert->status === Alert::STATUS_ACKNOWLEDGED) {
            return back()->with('error', 'Alert is already acknowledged.');
        }

        $before = $this->present($alert);

        $user = $request->user();
        $alert->update([
            'status' => Alert::STATUS_ACKNOWLEDGED,
            'acknowledged_at' => now(),
            'acknowledged_by' => $user?->getKey(),
        ]);

        AuditLog::record('alert.acknowledged', 'alert', (string) $alert->id, $before, $this->present($alert->refresh()));

        return back()->with('success', 'Alert acknowledged.');
    }

    /** @return array<int, string> */
    private function types(): array
    {
        return [
            Alert::TYPE_OVER_BUDGET,
            Alert::TYPE_STALE_OUTLET,
            Alert::TYPE_SCRAPE_LOW_SUCCESS,
            Alert::TYPE_PIPELINE_STALLED,
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function present(Alert $alert): array
    {
        return [
            'id' => $alert->id,
            'type' => $alert->type,
            'severity' => $alert->severity,
            'title' => $alert->title,
            'message' => $alert->message,
            'context' => $alert->context,
            'dedup_key' => $alert->dedup_key,
            'status' => $alert->status,
            'acknowledged_at' => $alert->acknowledged_at?->toIso8601String(),
            'acknowledged_by' => $alert->acknowledged_by,
            'created_at' => $alert->created_at?->toIso8601String(),
            'updated_at' => $alert->updated_at?->toIso8601String(),
        ];
    }
}
