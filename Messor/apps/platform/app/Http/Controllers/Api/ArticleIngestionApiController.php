<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\ArticleIngestionService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ArticleIngestionApiController extends Controller
{
    public function __construct(
        private readonly ArticleIngestionService $articleIngestionService
    ) {
    }

    public function storeBatch(Request $request): JsonResponse
    {
        $result = $this->articleIngestionService->ingestBatch($request->all());

        return response()->json([
            'data' => $result,
        ]);
    }
}
