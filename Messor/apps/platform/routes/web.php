<?php

use App\Http\Controllers\AlertController;
use App\Http\Controllers\ApiKeyController;
use App\Http\Controllers\AuditLogController;
use App\Http\Controllers\CuratorSettingController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\EventModerationController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\ModelUsageController;
use App\Http\Controllers\OutletController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\RunHistoryController;
use App\Http\Controllers\RuntimeController;
use App\Http\Controllers\ScrapeResultsController;
use App\Http\Controllers\ScrapingJobController;
use App\Http\Controllers\UserController;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

Route::get('/', function () {
    return Inertia::render('Home', [
        'canLogin' => Route::has('login'),
        'canRegister' => Route::has('register'),
    ]);
})->name('home');

Route::middleware(['auth', 'verified'])->group(function () {
    // ── Read-only, all authenticated roles (no role middleware) ──────────────
    Route::get('/dashboard', DashboardController::class)->name('dashboard');

    // Outlets list is read-only; the mutations below are operator+.
    Route::get('/outlets', [OutletController::class, 'index'])->name('outlets.index');
    // Export the full catalogue as JSON (B10) — read-only, round-trips with the
    // Messor seed file. Any authenticated role; streamed download.
    Route::get('/outlets/export', [OutletController::class, 'export'])->name('outlets.export');

    // Scraping index/status/stream are read-only ops views; trigger is operator+.
    Route::get('/scraping', [ScrapingJobController::class, 'index'])->name('scraping.index');
    Route::get('/scraping/status', [ScrapingJobController::class, 'status'])->name('scraping.status');
    Route::get('/scraping/{id}/stream', [ScrapingJobController::class, 'stream'])->name('scraping.stream');
    // Short-poll log tail — returns new log lines since byte-offset `from` and closes immediately.
    // Replaces the blocking SSE stream so php artisan serve is free between 1.5s polls.
    Route::get('/scraping/{id}/tail', [ScrapingJobController::class, 'tail'])->name('scraping.tail');

    Route::get('/runtime', [RuntimeController::class, 'index'])->name('runtime.index');
    Route::get('/runtime/snapshot', [RuntimeController::class, 'snapshot'])->name('runtime.snapshot');

    // Scraping run history / time-series (B4) — read-only observability over
    // Messor's recent scrape sessions (live-read, defensive fetch). All roles.
    Route::get('/run-history', [RunHistoryController::class, 'index'])->name('run-history.index');

    // Scrape Results browser (B12.2) — read-only, cross-schema over Curator's
    // durable public.scrape_sessions (ADR-0006): per-session list + per-session
    // per-outlet detail. All authenticated roles; no mutations, no secrets.
    Route::get('/scrape-results', [ScrapeResultsController::class, 'index'])->name('scrape-results.index');
    Route::get('/scrape-results/{session}', [ScrapeResultsController::class, 'show'])->name('scrape-results.show');

    // Curator pipeline live-status — lightweight JSON for the status modal.
    // Polls Curator GET /status and returns it as JSON (no Inertia). All roles.
    Route::get('/api/curator-pipeline', [HealthController::class, 'curatorPipeline'])
        ->name('curator-pipeline');

    // Unified health dashboard (B6) — read-only observability across Postgres /
    // Curator / Messor / RabbitMQ. All authenticated roles; no role gate.
    Route::get('/health', [HealthController::class, 'index'])->name('health.index');

    // Alerts (B11) — in-app view of alerts raised by the scheduled
    // `alerts:evaluate` evaluator. Read-only list for all roles (the bell
    // target); the acknowledge POST below is operator+.
    Route::get('/alerts', [AlertController::class, 'index'])->name('alerts.index');

    // Moderation list is read-only review; the action POSTs below are operator+.
    Route::get('/moderation', [EventModerationController::class, 'index'])->name('moderation.index');

    // Model usage / cost dashboard — read-only aggregates over
    // backoffice.model_usage (Curator writes rows; Phase 2.2 / ADR-0003).
    Route::get('/model-usage', [ModelUsageController::class, 'index'])->name('model-usage.index');
    // CSV export of the filtered rows (B5). Same access as the cost page (all
    // authenticated roles); honours the same from/to range. Streamed.
    Route::get('/model-usage/export', [ModelUsageController::class, 'export'])->name('model-usage.export');

    // ── Operator + admin: outlet / scraping / moderation MUTATIONS ───────────
    // (B2 RBAC — ADR-0005). Server middleware is the real gate; UI hiding is
    // cosmetic.
    Route::middleware('role:operator')->group(function () {
        // Outlets CRUD — bound to the shared public.outlets catalogue (Curator
        // owns the DDL, the Backoffice owns the row operations). See ADR-0003.
        Route::post('/outlets', [OutletController::class, 'store'])->name('outlets.store');
        Route::put('/outlets/{outlet}', [OutletController::class, 'update'])->name('outlets.update');
        Route::delete('/outlets/{outlet}', [OutletController::class, 'destroy'])->name('outlets.destroy');

        // Bulk activate / deactivate / delete selected outlets (B7). Audited (B1).
        Route::post('/outlets/bulk', [OutletController::class, 'bulk'])->name('outlets.bulk');

        // Acknowledge an open alert (B11). Audited (B1 alert.acknowledged).
        Route::post('/alerts/{alert}/acknowledge', [AlertController::class, 'acknowledge'])->name('alerts.acknowledge');

        // Import (B10): upload → preview (no write) → apply (upsert-by-id, audited).
        Route::post('/outlets/import/preview', [OutletController::class, 'importPreview'])->name('outlets.import.preview');
        Route::post('/outlets/import/apply', [OutletController::class, 'importApply'])->name('outlets.import.apply');

        Route::post('/scraping/trigger', [ScrapingJobController::class, 'trigger'])->name('scraping.trigger');

        // Moderation actions publish RabbitMQ commands (Curator applies them).
        Route::post('/moderation/pages/{page}/publish', [EventModerationController::class, 'publishPage'])->name('moderation.pages.publish');
        Route::post('/moderation/pages/{page}/unpublish', [EventModerationController::class, 'unpublishPage'])->name('moderation.pages.unpublish');
        Route::post('/moderation/pages/{page}/drop', [EventModerationController::class, 'dropPage'])->name('moderation.pages.drop');
        Route::post('/moderation/events/{event}/resynthesize', [EventModerationController::class, 'resynthesizeEvent'])->name('moderation.events.resynthesize');
        Route::post('/moderation/events/{event}/recluster', [EventModerationController::class, 'reclusterEvent'])->name('moderation.events.recluster');
    });

    // ── Admin only: keys, settings writes, audit log, user management ────────
    // (B2 RBAC — ADR-0005).
    Route::middleware('role:admin')->group(function () {
        // Curator settings — the single backoffice.curator_settings row Curator
        // polls. See ADR-0004 (config from DB) + ADR-0003 (schema isolation).
        // The edit view + update are admin-only (a bad config reaches the live
        // pipeline), so the whole Settings section is gated.
        Route::get('/settings', [CuratorSettingController::class, 'edit'])->name('settings.edit');
        Route::put('/settings', [CuratorSettingController::class, 'update'])->name('settings.update');
        // B9: restore the canonical defaults from config/curator.php (audited).
        Route::post('/settings/reset', [CuratorSettingController::class, 'reset'])->name('settings.reset');
        // ADR-0004: trigger a corpus re-embed (publishes embeddings.reembed to
        // Curator). Used after switching the embedding provider/model.
        Route::post('/settings/reembed', [CuratorSettingController::class, 'reembed'])->name('settings.reembed');

        // Provider API keys — encrypted-at-rest vault for store/rotate/mask/test.
        // Curator does NOT read these (it loads real keys from env — ADR-0004).
        Route::get('/api-keys', [ApiKeyController::class, 'index'])->name('api-keys.index');
        // B8: read-only rotation / change history (filtered audit_logs view).
        Route::get('/api-keys/history', [ApiKeyController::class, 'history'])->name('api-keys.history');
        Route::post('/api-keys', [ApiKeyController::class, 'store'])->name('api-keys.store');
        Route::put('/api-keys/{apiKey}', [ApiKeyController::class, 'update'])->name('api-keys.update');
        Route::delete('/api-keys/{apiKey}', [ApiKeyController::class, 'destroy'])->name('api-keys.destroy');
        Route::post('/api-keys/{apiKey}/test', [ApiKeyController::class, 'test'])->name('api-keys.test');

        // Audit log — read-only viewer of backoffice.audit_logs (who did what to
        // which target, with before/after). Written best-effort by every
        // mutation via AuditLog::record(). See gap-analysis B1. Admin-only:
        // exposing who-did-what is itself sensitive.
        Route::get('/audit-log', [AuditLogController::class, 'index'])->name('audit-log.index');

        // Minimal user/role management (B2). Lists backoffice.users and lets an
        // admin change roles; guards against removing the last admin.
        Route::get('/users', [UserController::class, 'index'])->name('users.index');
        Route::put('/users/{user}/role', [UserController::class, 'updateRole'])->name('users.update-role');
    });
});

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

require __DIR__.'/auth.php';
