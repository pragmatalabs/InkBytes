<?php

use App\Http\Controllers\Api\ArticleIngestionApiController;
use App\Http\Controllers\Api\ScrapeSessionApiController;
use App\Http\Controllers\Api\SourceApiController;
use Illuminate\Support\Facades\Route;

Route::get('/news-outlets', [SourceApiController::class, 'index']);

Route::get('/scrapesessions', [ScrapeSessionApiController::class, 'index']);
Route::post('/scrapesessions', [ScrapeSessionApiController::class, 'store']);
Route::get('/scrapesessions/status', [ScrapeSessionApiController::class, 'status']);
Route::post('/articles/batch', [ArticleIngestionApiController::class, 'storeBatch']);

Route::get('/scrape/status', [ScrapeSessionApiController::class, 'status']);
Route::get('/scrape/results', [ScrapeSessionApiController::class, 'results']);
Route::post('/scrape/session/{sessionId}/view', [ScrapeSessionApiController::class, 'recordView']);
