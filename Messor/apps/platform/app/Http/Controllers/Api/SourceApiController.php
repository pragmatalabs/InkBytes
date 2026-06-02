<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\SourceCatalogService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class SourceApiController extends Controller
{
    public function __construct(
        private readonly SourceCatalogService $sourceCatalogService
    ) {
    }

    public function index(Request $request): JsonResponse
    {
        $onlyActive = null;

        $activeFilter = $request->input('filters.active');
        if ($activeFilter !== null) {
            $parsed = filter_var($activeFilter, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
            $onlyActive = $parsed ?? true;
        }

        return response()->json([
            'data' => $this->sourceCatalogService->listForApi($onlyActive),
        ]);
    }
}
