<?php

namespace App\Services;

use App\Models\Source;
use Illuminate\Support\Collection;

class SourceCatalogService
{
    public function listForInertia(): Collection
    {
        return Source::query()
            ->orderBy('name')
            ->get()
            ->map(fn (Source $source): array => [
                'name' => $source->name,
                'region' => $source->region ?? 'Global',
                'status' => $source->status,
                'url' => $source->base_url,
            ])
            ->values();
    }

    public function listForApi(?bool $onlyActive = null): array
    {
        $query = Source::query()->orderBy('name');

        if ($onlyActive !== null) {
            if ($onlyActive) {
                $query->where('status', 'active');
            } else {
                $query->where('status', '!=', 'active');
            }
        }

        return $query->get()
            ->map(fn (Source $source): array => [
                'id' => $source->id,
                'documentId' => $source->slug,
                'name' => $source->name,
                'url' => $source->base_url,
                'active' => $source->status === 'active',
                'status' => $source->status,
                'description' => $source->region ?? '',
                'slug' => $source->slug,
                'createdAt' => $source->created_at?->toIso8601String(),
                'updatedAt' => $source->updated_at?->toIso8601String(),
                'publishedAt' => $source->updated_at?->toIso8601String(),
            ])
            ->values()
            ->all();
    }
}
