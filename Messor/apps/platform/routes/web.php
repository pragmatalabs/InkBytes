<?php

use App\Http\Controllers\DashboardController;
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
});

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

require __DIR__.'/auth.php';
