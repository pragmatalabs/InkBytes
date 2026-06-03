<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasOne;

/**
 * Event — a cluster of articles about one newsworthy thing.
 *
 * READ-ONLY from the Backoffice. Curator owns the `public.events` DDL and all
 * writes (ADR-0003). The Backoffice reads events for the moderation screen and
 * issues RabbitMQ commands (publish/unpublish/drop, re-synthesize, re-cluster)
 * that Curator consumes and applies — it never writes this table directly.
 *
 * The id is a TEXT ULID, not an auto-increment integer.
 */
class Event extends Model
{
    protected $table = 'public.events';

    protected $primaryKey = 'id';

    public $incrementing = false;

    protected $keyType = 'string';

    public $timestamps = false;

    protected $guarded = ['*']; // read-only: nothing is mass-assignable

    protected $casts = [
        'source_count' => 'integer',
        'article_count' => 'integer',
        'created_at' => 'datetime',
        'first_seen_at' => 'datetime',
        'last_updated_at' => 'datetime',
    ];

    public function page(): HasOne
    {
        return $this->hasOne(Page::class, 'event_id', 'id');
    }
}
