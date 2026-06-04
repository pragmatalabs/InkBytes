<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

/*
| B11 — Alerting. The evaluator probes the B3/B4/B5/B6 signal sources and
| upserts open alerts (deduped by dedup_key). Every 5 minutes.
|
| DEPLOY NOTE: this only fires if a scheduler is running —
| `php artisan schedule:work` (dev) or a system cron invoking
| `php artisan schedule:run` every minute (prod). Without it no alerts are
| raised. withoutOverlapping() guards against a slow run stacking up.
*/
Schedule::command('alerts:evaluate')
    ->everyFiveMinutes()
    ->withoutOverlapping();
