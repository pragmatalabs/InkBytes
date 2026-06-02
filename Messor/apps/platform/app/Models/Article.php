<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Article extends Model
{
    use HasFactory;

    protected $fillable = [
        'external_id',
        'uid',
        'source_id',
        'scrape_run_id',
        'article_url',
        'article_source',
        'title',
        'text',
        'summary',
        'authors',
        'keywords',
        'topics',
        'meta_categories',
        'entities',
        'language',
        'publish_date',
        'fetched_on',
        'last_updated_at',
        'metadata',
    ];

    protected $casts = [
        'authors' => 'array',
        'keywords' => 'array',
        'topics' => 'array',
        'meta_categories' => 'array',
        'entities' => 'array',
        'metadata' => 'array',
        'publish_date' => 'datetime',
        'fetched_on' => 'datetime',
        'last_updated_at' => 'datetime',
    ];

    public function source(): BelongsTo
    {
        return $this->belongsTo(Source::class);
    }

    public function scrapeRun(): BelongsTo
    {
        return $this->belongsTo(ScrapeRun::class);
    }
}
