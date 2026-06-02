<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\ScrapeRunService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ScrapeSessionApiController extends Controller
{
    public function __construct(
        private readonly ScrapeRunService $scrapeRunService
    ) {
    }

    public function index(Request $request): JsonResponse
    {
        return response()->json(
            $this->scrapeRunService->listSessionsForApi($request)
        );
    }

    public function store(Request $request): JsonResponse
    {
        $run = $this->scrapeRunService->ingestSessionPayload($request->all());

        return response()->json([
            'data' => $this->scrapeRunService->formatSessionRecord($run),
        ], 201);
    }

    public function status(): JsonResponse
    {
        return response()->json($this->scrapeRunService->currentStatus());
    }

    public function results(): JsonResponse
    {
        $payload = $this->scrapeRunService->latestResultsPayload();
        if ($payload === null) {
            return response()->json([
                'message' => 'No scraping sessions available.',
            ], 404);
        }

        return response()->json($payload);
    }

    public function recordView(string $sessionId): JsonResponse
    {
        return response()->json(
            $this->scrapeRunService->recordSessionView($sessionId)
        );
    }
}
