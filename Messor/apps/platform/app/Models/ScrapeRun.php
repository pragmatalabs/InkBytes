<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ScrapeRun extends Model
{
    use HasFactory;

    protected $fillable = [
        'run_code',
        'source_id',
        'started_at',
        'completed_at',
        'duration_seconds',
        'status',
        'articles_count',
        'failure_reason',
        'views_count',
        'last_viewed_at',
        'metadata',
    ];

    protected $casts = [
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
        'last_viewed_at' => 'datetime',
        'metadata' => 'array',
    ];

    public function source(): BelongsTo
    {
        return $this->belongsTo(Source::class);
    }
}
