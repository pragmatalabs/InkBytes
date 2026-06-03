<?php

use App\Http\Controllers\Api\SourceApiController;
use Illuminate\Support\Facades\Route;

// Outlet catalogue (read-only), backed by the shared public.outlets table.
Route::get('/news-outlets', [SourceApiController::class, 'index']);

// NOTE: the legacy /scrapesessions, /articles/batch and /scrape/* endpoints
// were removed in Phase 1.2. They wrote to the dropped Laravel `scrape_runs`
// and `articles` tables (Phase 1.1 / ADR-0003); Curator now owns article
// ingestion via RabbitMQ, so these HTTP sinks no longer have a backing table.
