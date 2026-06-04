<?php

use App\Http\Controllers\ApiKeyController;
use App\Http\Controllers\AuditLogController;
use App\Http\Controllers\CuratorSettingController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\EventModerationController;
use App\Http\Controllers\HealthController;
use App\Http\Controllers\ModelUsageController;
use App\Http\Controllers\OutletController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\RuntimeController;
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

    // Scraping index/status/stream are read-only ops views; trigger is operator+.
    Route::get('/scraping', [ScrapingJobController::class, 'index'])->name('scraping.index');
    Route::get('/scraping/status', [ScrapingJobController::class, 'status'])->name('scraping.status');
    Route::get('/scraping/{id}/stream', [ScrapingJobController::class, 'stream'])->name('scraping.stream');

    Route::get('/runtime', [RuntimeController::class, 'index'])->name('runtime.index');
    Route::get('/runtime/snapshot', [RuntimeController::class, 'snapshot'])->name('runtime.snapshot');

    // Unified health dashboard (B6) — read-only observability across Postgres /
    // Curator / Messor / RabbitMQ. All authenticated roles; no role gate.
    Route::get('/health', [HealthController::class, 'index'])->name('health.index');

    // Moderation list is read-only review; the action POSTs below are operator+.
    Route::get('/moderation', [EventModerationController::class, 'index'])->name('moderation.index');

    // Model usage / cost dashboard — read-only aggregates over
    // backoffice.model_usage (Curator writes rows; Phase 2.2 / ADR-0003).
    Route::get('/model-usage', [ModelUsageController::class, 'index'])->name('model-usage.index');

    // ── Operator + admin: outlet / scraping / moderation MUTATIONS ───────────
    // (B2 RBAC — ADR-0005). Server middleware is the real gate; UI hiding is
    // cosmetic.
    Route::middleware('role:operator')->group(function () {
        // Outlets CRUD — bound to the shared public.outlets catalogue (Curator
        // owns the DDL, the Backoffice owns the row operations). See ADR-0003.
        Route::post('/outlets', [OutletController::class, 'store'])->name('outlets.store');
        Route::put('/outlets/{outlet}', [OutletController::class, 'update'])->name('outlets.update');
        Route::delete('/outlets/{outlet}', [OutletController::class, 'destroy'])->name('outlets.destroy');

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

        // Provider API keys — encrypted-at-rest vault for store/rotate/mask/test.
        // Curator does NOT read these (it loads real keys from env — ADR-0004).
        Route::get('/api-keys', [ApiKeyController::class, 'index'])->name('api-keys.index');
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
