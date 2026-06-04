<?php

namespace Tests\Feature;

use App\Http\Controllers\OutletController;
use Illuminate\Foundation\Testing\RefreshDatabase;
use ReflectionMethod;
use Tests\TestCase;

/**
 * B3 — Outlet health columns.
 *
 * The enriched Outlets index joins Curator's `public.articles` cross-schema
 * (ADR-0003, read-only) to attach article volume, events contributed and
 * last-scraped recency per outlet. There is intentionally NO success rate:
 * `public.articles` only holds successfully-scraped articles, so attempts /
 * failures (a true rate) live in Messor's run history — a future B4.
 *
 * SQLite caveat: the test DB is SQLite (:memory:) and has neither
 * `public.articles` nor `public.outlets`. We therefore exercise the defensive
 * fallback here — `outletStats()` must return an empty map (not throw) when the
 * Curator table is unreachable, so the page renders with null/0 stats. The
 * fully-populated payload (apnews article_count≈158, etc.) is verified against
 * Postgres via tinker in the B3 verification notes, the same approach prior
 * cross-schema phases used.
 */
class OutletHealthTest extends TestCase
{
    use RefreshDatabase;

    public function test_outlet_stats_degrade_to_empty_without_public_articles(): void
    {
        $method = new ReflectionMethod(OutletController::class, 'outletStats');
        $method->setAccessible(true);

        $stats = $method->invoke(new OutletController());

        $this->assertSame([], $stats);
    }
}
