<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * Alert — an operational alert raised by the scheduled evaluator (B11).
 *
 * Backoffice-owned (ADR-0001 / ADR-0003); lives in the `backoffice` schema. The
 * evaluator (`alerts:evaluate`) upserts rows keyed on `dedup_key` so a still
 * firing condition does not create a duplicate OPEN alert each run. Operators+
 * acknowledge them (status flip, audited B1).
 *
 * `context` is a secret-free jsonb bag of the metrics that tripped the rule.
 */
class Alert extends Model
{
    protected $table = 'alerts';

    /** Rule types. */
    public const TYPE_SCRAPE_LOW_SUCCESS = 'scrape_low_success';

    public const TYPE_STALE_OUTLET = 'stale_outlet';

    public const TYPE_OVER_BUDGET = 'over_budget';

    public const TYPE_PIPELINE_STALLED = 'pipeline_stalled';

    /** Severities. */
    public const SEVERITY_WARNING = 'warning';

    public const SEVERITY_CRITICAL = 'critical';

    /** Statuses. */
    public const STATUS_OPEN = 'open';

    public const STATUS_ACKNOWLEDGED = 'acknowledged';

    protected $fillable = [
        'type',
        'severity',
        'title',
        'message',
        'context',
        'dedup_key',
        'status',
        'acknowledged_at',
        'acknowledged_by',
    ];

    protected $casts = [
        'context' => 'array',
        'acknowledged_at' => 'datetime',
        'acknowledged_by' => 'integer',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /** Count of currently-open alerts (the bell badge). */
    public static function openCount(): int
    {
        return (int) static::query()->where('status', self::STATUS_OPEN)->count();
    }
}
