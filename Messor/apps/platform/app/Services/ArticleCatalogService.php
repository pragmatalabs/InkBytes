<?php

namespace App\Services;

use App\Models\Article;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ArticleCatalogService
{
    public function listForInertia(Request $request): array
    {
        $search = $this->normalizeString($request->string('search')->value());
        $source = $this->normalizeString($request->string('source')->value());
        $language = $this->normalizeString($request->string('language')->value());
        $perPage = max(10, min(100, (int) $request->input('perPage', 25)));

        $query = Article::query()->with('source:id,name')
            ->orderByDesc('publish_date')
            ->orderByDesc('fetched_on')
            ->orderByDesc('id');

        if ($search !== null) {
            $this->applySearchFilter($query, $search);
        }

        if ($source !== null) {
            $query->where('article_source', $source);
        }

        if ($language !== null) {
            $query->where('language', $language);
        }

        $paginator = $query->paginate($perPage)->withQueryString();

        return [
            'articles' => $paginator->getCollection()
                ->map(fn (Article $article): array => [
                    'id' => $article->id,
                    'external_id' => $article->external_id,
                    'title' => $article->title ?: 'Untitled article',
                    'summary' => Str::limit(trim((string) ($article->summary ?: $article->text ?: '')), 220),
                    'article_source' => $article->article_source ?: ($article->source?->name ?? 'Unknown'),
                    'source_name' => $article->source?->name,
                    'article_url' => $article->article_url,
                    'language' => $article->language ?: 'n/a',
                    'publish_date' => $article->publish_date?->toIso8601String(),
                    'fetched_on' => $article->fetched_on?->toIso8601String(),
                    'authors' => is_array($article->authors) ? $article->authors : [],
                ])
                ->values()
                ->all(),
            'pagination' => [
                'page' => $paginator->currentPage(),
                'perPage' => $paginator->perPage(),
                'total' => $paginator->total(),
                'lastPage' => $paginator->lastPage(),
            ],
            'filters' => [
                'search' => $search,
                'source' => $source,
                'language' => $language,
                'perPage' => $perPage,
            ],
            'filterOptions' => [
                'sources' => Article::query()
                    ->whereNotNull('article_source')
                    ->where('article_source', '!=', '')
                    ->distinct()
                    ->orderBy('article_source')
                    ->pluck('article_source')
                    ->values()
                    ->all(),
                'languages' => Article::query()
                    ->whereNotNull('language')
                    ->where('language', '!=', '')
                    ->distinct()
                    ->orderBy('language')
                    ->pluck('language')
                    ->values()
                    ->all(),
            ],
        ];
    }

    private function applySearchFilter($query, string $search): void
    {
        $operator = DB::connection()->getDriverName() === 'pgsql' ? 'ilike' : 'like';
        $pattern = "%{$search}%";

        $query->where(function ($builder) use ($operator, $pattern): void {
            $builder->where('title', $operator, $pattern)
                ->orWhere('summary', $operator, $pattern)
                ->orWhere('article_url', $operator, $pattern)
                ->orWhere('article_source', $operator, $pattern);
        });
    }

    private function normalizeString(?string $value): ?string
    {
        if (!is_string($value)) {
            return null;
        }

        $trimmed = trim($value);
        return $trimmed === '' ? null : $trimmed;
    }
}
