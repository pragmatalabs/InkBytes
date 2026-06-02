<?php

namespace App\Http\Controllers;

use App\Services\SourceCatalogService;
use Inertia\Inertia;
use Inertia\Response;

class SourceController extends Controller
{
    public function __construct(
        private readonly SourceCatalogService $sourceCatalogService
    ) {
    }

    public function index(): Response
    {
        return Inertia::render('Sources/Index', [
            'sources' => $this->sourceCatalogService->listForInertia(),
        ]);
    }
}
