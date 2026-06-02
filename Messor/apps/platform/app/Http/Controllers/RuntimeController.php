<?php

namespace App\Http\Controllers;

use App\Services\DockerRuntimeService;
use Illuminate\Http\JsonResponse;
use Inertia\Inertia;
use Inertia\Response;

class RuntimeController extends Controller
{
    public function __construct(
        private readonly DockerRuntimeService $dockerRuntimeService
    ) {
    }

    public function index(): Response
    {
        return Inertia::render('Runtime/Index', [
            'snapshot' => $this->dockerRuntimeService->snapshot(),
        ]);
    }

    public function snapshot(): JsonResponse
    {
        return response()->json($this->dockerRuntimeService->snapshot());
    }
}
