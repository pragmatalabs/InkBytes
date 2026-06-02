<?php

namespace App\Http\Controllers;

use App\Services\ArticleCatalogService;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

class ArticleController extends Controller
{
    public function __construct(
        private readonly ArticleCatalogService $articleCatalogService
    ) {
    }

    public function index(Request $request): Response
    {
        return Inertia::render('Articles/Index', $this->articleCatalogService->listForInertia($request));
    }
}
