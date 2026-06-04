<?php

use App\Http\Controllers\ApiKeyController;
use App\Http\Controllers\AuditLogController;
use App\Http\Controllers\CuratorSettingController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\EventModerationController;
use App\Http\Controllers\ModelUsageController;
use App\Http\Controllers\OutletController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\RuntimeController;
use App\Http\Controllers\ScrapingJobController;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

Route::get('/', function () {
    return Inertia::render('Home', [
        'canLogin' => Route::has('login'),
        'canRegister' => Route::has('register'),
    ]);
})->name('home');

Route::middleware(['auth', 'verified'])->group(function () {
    Route::get('/dashboard', DashboardController::class)->name('dashboard');

    // Outlets CRUD — bound to the shared public.outlets catalogue (Curator owns
    // the DDL, the Backoffice owns the row operations). See ADR-0003.
    Route::get('/outlets', [OutletController::class, 'index'])->name('outlets.index');
    Route::post('/outlets', [OutletController::class, 'store'])->name('outlets.store');
    Route::put('/outlets/{outlet}', [OutletController::class, 'update'])->name('outlets.update');
    Route::delete('/outlets/{outlet}', [OutletController::class, 'destroy'])->name('outlets.destroy');

    Route::get('/scraping', [ScrapingJobController::class, 'index'])->name('scraping.index');
    Route::post('/scraping/trigger', [ScrapingJobController::class, 'trigger'])->name('scraping.trigger');
    Route::get('/scraping/status', [ScrapingJobController::class, 'status'])->name('scraping.status');
    Route::get('/scraping/{id}/stream', [ScrapingJobController::class, 'stream'])->name('scraping.stream');
    Route::get('/runtime', [RuntimeController::class, 'index'])->name('runtime.index');
    Route::get('/runtime/snapshot', [RuntimeController::class, 'snapshot'])->name('runtime.snapshot');

    // Curator settings — the single backoffice.curator_settings row Curator polls.
    // See ADR-0004 (config from DB) + ADR-0003 (schema isolation).
    Route::get('/settings', [CuratorSettingController::class, 'edit'])->name('settings.edit');
    Route::put('/settings', [CuratorSettingController::class, 'update'])->name('settings.update');

    // Events / Pages moderation (Phase 2.3) — read-only review of Curator's
    // public.events/public.pages + publish/unpublish/drop and re-synthesize/
    // re-cluster actions that publish RabbitMQ commands (Curator applies them).
    Route::get('/moderation', [EventModerationController::class, 'index'])->name('moderation.index');
    Route::post('/moderation/pages/{page}/publish', [EventModerationController::class, 'publishPage'])->name('moderation.pages.publish');
    Route::post('/moderation/pages/{page}/unpublish', [EventModerationController::class, 'unpublishPage'])->name('moderation.pages.unpublish');
    Route::post('/moderation/pages/{page}/drop', [EventModerationController::class, 'dropPage'])->name('moderation.pages.drop');
    Route::post('/moderation/events/{event}/resynthesize', [EventModerationController::class, 'resynthesizeEvent'])->name('moderation.events.resynthesize');
    Route::post('/moderation/events/{event}/recluster', [EventModerationController::class, 'reclusterEvent'])->name('moderation.events.recluster');

    // Model usage / cost dashboard — read-only aggregates over
    // backoffice.model_usage (Curator writes rows; Phase 2.2 / ADR-0003).
    Route::get('/model-usage', [ModelUsageController::class, 'index'])->name('model-usage.index');

    // Provider API keys — encrypted-at-rest vault for store/rotate/mask/test.
    // Curator does NOT read these (it loads real keys from env — ADR-0004).
    Route::get('/api-keys', [ApiKeyController::class, 'index'])->name('api-keys.index');
    Route::post('/api-keys', [ApiKeyController::class, 'store'])->name('api-keys.store');
    Route::put('/api-keys/{apiKey}', [ApiKeyController::class, 'update'])->name('api-keys.update');
    Route::delete('/api-keys/{apiKey}', [ApiKeyController::class, 'destroy'])->name('api-keys.destroy');
    Route::post('/api-keys/{apiKey}/test', [ApiKeyController::class, 'test'])->name('api-keys.test');

    // Audit log — read-only viewer of backoffice.audit_logs (who did what to
    // which target, with before/after). Written best-effort by every mutation
    // via AuditLog::record(). See gap-analysis B1.
    Route::get('/audit-log', [AuditLogController::class, 'index'])->name('audit-log.index');
});

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

require __DIR__.'/auth.php';
