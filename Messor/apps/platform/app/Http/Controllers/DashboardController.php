<?php

namespace App\Http\Controllers;

use App\Models\Outlet;
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
            ],
        ]);
    }
}
