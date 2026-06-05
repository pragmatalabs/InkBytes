<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Outlet;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * Read-only outlet catalogue endpoint, backed by the shared `public.outlets`
 * table (Curator owns the DDL — see ADR-0003). Kept for legacy clients that
 * pull the outlet list over HTTP.
 */
class SourceApiController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $query = Outlet::query()->orderBy('display_name');

        $activeFilter = $request->input('filters.active');
        if ($activeFilter !== null) {
            $parsed = filter_var($activeFilter, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
            $query->where('active', $parsed ?? true);
        }

        $data = $query->get()
            ->map(fn (Outlet $outlet): array => [
                // Note: 'id' is intentionally omitted — it's a string slug in
                // our schema but OutletsSource.id expects int (Pydantic v1).
                // The string slug is carried by 'slug' and 'documentId' instead,
                // which is what Messor's _outlet_identifiers() matches against.
                'documentId' => $outlet->id,
                'name' => $outlet->display_name,
                'url' => $outlet->url,
                'active' => (bool) $outlet->active,
                'region' => $outlet->region,
                'language' => $outlet->language,
                'vertical' => $outlet->vertical,
                'priority' => (int) $outlet->priority,
                'slug' => $outlet->id,
                'createdAt' => $outlet->created_at?->toIso8601String(),
                'updatedAt' => $outlet->updated_at?->toIso8601String(),
            ])
            ->values()
            ->all();

        return response()->json(['data' => $data]);
    }
}
