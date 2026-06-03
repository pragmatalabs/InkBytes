<?php

namespace App\Http\Controllers;

use App\Models\Outlet;
use Illuminate\Support\Facades\DB;
use Inertia\Inertia;
use Inertia\Response;

class DashboardController extends Controller
{
    public function __invoke(): Response
    {
        return Inertia::render('Dashboard', [
            'metrics' => [
                'total_outlets' => Outlet::query()->count(),
                'active_outlets' => Outlet::query()->where('active', true)->count(),
                'high_priority_outlets' => Outlet::query()->where('priority', 1)->count(),
                'regions' => Outlet::query()
                    ->selectRaw('region, count(*) as count')
                    ->groupBy('region')
                    ->orderByDesc('count')
                    ->get()
                    ->map(fn ($row): array => [
                        'region' => $row->region,
                        'count' => (int) $row->count,
                    ])
                    ->values(),
                'pipeline' => $this->pipelineMetrics(),
            ],
        ]);
    }

    /**
     * Live pipeline state from Curator's `public.*` tables + the
     * `backoffice.model_usage` cost sink. Cross-schema reads are allowed
     * (ADR-0003); the Backoffice never writes these. Defensive: if Curator's
     * schema is absent the dashboard still renders.
     *
     * @return array<string, mixed>
     */
    private function pipelineMetrics(): array
    {
        try {
            return [
                'available' => true,
                'articles' => (int) DB::scalar('SELECT count(*) FROM public.articles'),
                'enriched' => (int) DB::scalar('SELECT count(*) FROM public.articles WHERE enriched_at IS NOT NULL'),
                'events' => (int) DB::scalar('SELECT count(*) FROM public.events'),
                'pages' => (int) DB::scalar('SELECT count(*) FROM public.pages'),
                'pages_published' => (int) DB::scalar('SELECT count(*) FROM public.pages WHERE published_at IS NOT NULL'),
                'spend_usd' => (float) DB::scalar('SELECT COALESCE(SUM(cost_usd), 0) FROM backoffice.model_usage'),
                'last_harvest' => DB::scalar('SELECT MAX(scraped_at) FROM public.articles'),
            ];
        } catch (\Throwable $e) {
            return ['available' => false];
        }
    }
}
