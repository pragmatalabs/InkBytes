<?php

namespace App\Http\Controllers;

use App\Services\ScrapeRunService;
use Inertia\Inertia;
use Inertia\Response;

class ScrapeRunController extends Controller
{
    public function __construct(
        private readonly ScrapeRunService $scrapeRunService
    ) {
    }

    public function index(): Response
    {
        return Inertia::render('Runs/Index', [
            'runs' => $this->scrapeRunService->listForInertia(),
        ]);
    }
}
