<?php

namespace App\Http\Controllers;

use App\Services\ScrapeRunService;
use Inertia\Inertia;
use Inertia\Response;

class DashboardController extends Controller
{
    public function __construct(
        private readonly ScrapeRunService $scrapeRunService
    ) {
    }

    public function __invoke(): Response
    {
        return Inertia::render('Dashboard', [
            'metrics' => $this->scrapeRunService->dashboardMetrics(),
        ]);
    }
}
