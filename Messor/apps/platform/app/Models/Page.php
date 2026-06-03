<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * Page — the reader-facing one-pager synthesized for an event.
 *
 * READ-ONLY from the Backoffice. Curator owns the `public.pages` DDL and all
 * writes (ADR-0003). A page is "published" when `published_at` is non-null and
 * "unpublished" when null (migration 003 made the column nullable so the
 * Backoffice's publish/unpublish/drop commands have a clean toggle). The
 * Backoffice reads pages for moderation and issues RabbitMQ commands; Curator
 * performs the toggle.
 *
 * The id is a TEXT id (same value as event_id), not auto-increment.
 */
class Page extends Model
{
    protected $table = 'public.pages';

    protected $primaryKey = 'id';

    public $incrementing = false;

    protected $keyType = 'string';

    public $timestamps = false;

    protected $guarded = ['*']; // read-only: nothing is mass-assignable

    protected $casts = [
        'evidence_rail' => 'array',
        'entities' => 'array',
        'freshness_at' => 'datetime',
        'published_at' => 'datetime',
        'cost_cents' => 'integer',
    ];

    public function event(): BelongsTo
    {
        return $this->belongsTo(Event::class, 'event_id', 'id');
    }

    /**
     * A page is live when it carries a publish timestamp.
     */
    public function isPublished(): bool
    {
        return $this->published_at !== null;
    }
}
