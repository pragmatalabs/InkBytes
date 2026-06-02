<?php

namespace App\Services;

use App\Models\Article;
use App\Models\ScrapeRun;
use App\Models\Source;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ArticleIngestionService
{
    public function ingestBatch(array $payload): array
    {
        $data = $payload['data'] ?? $payload;
        if (!is_array($data)) {
            return $this->emptyResult();
        }

        $articles = $data['articles'] ?? [];
        if (!is_array($articles)) {
            return $this->emptyResult();
        }

        $runCode = $this->normalizeString($data['run_code'] ?? $data['results_staging_file_name'] ?? null);
        $scrapeRun = $runCode !== null
            ? ScrapeRun::query()->where('run_code', $runCode)->first()
            : null;

        $now = now();
        $rows = [];
        $invalid = 0;

        foreach ($articles as $article) {
            if (!is_array($article)) {
                $invalid++;
                continue;
            }

            $externalId = $this->resolveExternalId($article);
            if ($externalId === null) {
                $invalid++;
                continue;
            }

            $articleSource = $this->normalizeString($article['article_source'] ?? $article['source_url'] ?? null);
            $source = $this->resolveSource($articleSource, $scrapeRun);

            $rows[] = [
                'external_id' => $externalId,
                'uid' => $this->normalizeString($article['uid'] ?? null),
                'source_id' => $source?->id,
                'scrape_run_id' => $scrapeRun?->id,
                'article_url' => $this->normalizeString($article['article_url'] ?? null),
                'article_source' => $articleSource,
                'title' => $this->normalizeString($article['title'] ?? null),
                'text' => $this->normalizeString($article['text'] ?? null),
                'summary' => $this->normalizeString($article['summary'] ?? null),
                'authors' => $this->toJson($this->ensureArray($article['authors'] ?? null)),
                'keywords' => $this->toJson($this->ensureArray($article['keywords'] ?? null)),
                'topics' => $this->toJson($this->ensureArray($article['topics'] ?? null)),
                'meta_categories' => $this->toJson($this->ensureArray($article['meta_categories'] ?? null)),
                'entities' => $this->toJson($this->normalizeEntities($article['entities'] ?? null)),
                'language' => $this->normalizeString($article['language'] ?? null),
                'publish_date' => $this->parseDate($article['publish_date'] ?? null),
                'fetched_on' => $this->parseDate($article['fetched_on'] ?? null),
                'last_updated_at' => $this->parseDate($article['last_updated'] ?? null),
                'metadata' => $this->toJson($this->ensureAssociativeArray($article['metadata'] ?? null)),
                'created_at' => $now,
                'updated_at' => $now,
            ];
        }

        if ($rows === []) {
            return [
                'received' => count($articles),
                'inserted' => 0,
                'skipped' => count($articles),
                'invalid' => $invalid,
            ];
        }

        $inserted = 0;

        DB::transaction(function () use (&$inserted, $rows): void {
            foreach (array_chunk($rows, 250) as $chunk) {
                $inserted += DB::table((new Article())->getTable())->insertOrIgnore($chunk);
            }
        });

        $received = count($articles);
        $skipped = max(0, $received - $inserted);

        return [
            'received' => $received,
            'inserted' => $inserted,
            'skipped' => $skipped,
            'invalid' => $invalid,
        ];
    }

    private function emptyResult(): array
    {
        return [
            'received' => 0,
            'inserted' => 0,
            'skipped' => 0,
            'invalid' => 0,
        ];
    }

    private function resolveExternalId(array $article): ?string
    {
        $id = $this->normalizeString($article['id'] ?? null);
        if ($id !== null) {
            return $id;
        }

        $uid = $this->normalizeString($article['uid'] ?? null);
        if ($uid !== null) {
            return $uid;
        }

        $articleUrl = $this->normalizeString($article['article_url'] ?? null);
        if ($articleUrl === null) {
            return null;
        }

        // Match scraper identity fallback when hash id is missing in payload.
        return sha1($articleUrl);
    }

    private function resolveSource(?string $articleSource, ?ScrapeRun $scrapeRun): ?Source
    {
        if ($scrapeRun?->source !== null) {
            return $scrapeRun->source;
        }

        if ($articleSource === null) {
            return null;
        }

        return Source::query()
            ->where('slug', Str::slug($articleSource))
            ->orWhereRaw('LOWER(name) = ?', [Str::lower($articleSource)])
            ->first();
    }

    private function parseDate(mixed $value): ?Carbon
    {
        if (!is_string($value) || trim($value) === '' || strtolower($value) === 'none' || strtolower($value) === 'null') {
            return null;
        }

        try {
            return Carbon::parse($value);
        } catch (\Throwable) {
            return null;
        }
    }

    private function normalizeString(mixed $value): ?string
    {
        if (!is_string($value)) {
            return null;
        }

        $trimmed = trim($value);
        return $trimmed === '' ? null : $trimmed;
    }

    private function ensureArray(mixed $value): array
    {
        if (is_array($value)) {
            return array_values($value);
        }

        if (is_string($value) && trim($value) !== '') {
            return [trim($value)];
        }

        return [];
    }

    private function ensureAssociativeArray(mixed $value): ?array
    {
        if (!is_array($value)) {
            return null;
        }

        return $value;
    }

    private function normalizeEntities(mixed $value): array
    {
        if (is_array($value)) {
            return $value;
        }

        return [];
    }

    private function toJson(mixed $value): ?string
    {
        if ($value === null) {
            return null;
        }

        try {
            return json_encode($value, JSON_THROW_ON_ERROR);
        } catch (\Throwable) {
            return null;
        }
    }
}
