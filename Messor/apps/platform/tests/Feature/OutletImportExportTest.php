<?php

namespace Tests\Feature;

use App\Models\AuditLog;
use App\Models\Outlet;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseMigrations;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/**
 * B10 — Outlet import/export.
 *
 * Export streams the full `public.outlets` catalogue in the Messor seed shape
 * (id/name/display_name/url/region/language/vertical/active/priority — NO
 * timestamps) so an exported file round-trips back through import and can serve
 * as / replace `apps/scraper/data/outlets/outlets.json`.
 *
 * Import is upload → validate → diff preview (no write) → apply (upsert-by-id,
 * audited B1, operator+ B2).
 *
 * SQLite caveat: the test DB is SQLite (:memory:) and has no `public` schema.
 * The Outlet model is bound to `public.outlets`, which Eloquent compiles to the
 * qualified "public"."outlets" (schema.table) — matching Postgres. We ATTACH an
 * in-memory database named `public` and create the table there so the apply path
 * runs against the REAL Eloquent model, exactly as it would hit Postgres. We use
 * DatabaseMigrations (not RefreshDatabase) because ATTACH cannot run inside the
 * per-test transaction RefreshDatabase wraps everything in.
 */
class OutletImportExportTest extends TestCase
{
    use DatabaseMigrations;

    /**
     * The seed shape (and the round-trip export shape): the exact fields in
     * apps/scraper/data/outlets/outlets.json, no timestamps.
     */
    private const SEED_FIELDS = [
        'id', 'name', 'display_name', 'url', 'region', 'language', 'vertical', 'active', 'priority',
    ];

    protected function setUp(): void
    {
        parent::setUp();

        // ATTACH an in-memory `public` schema + the outlets table (test-only
        // scaffolding mirroring the Curator-owned columns — no DDL/migration is
        // shipped). DatabaseMigrations leaves no open transaction here, so ATTACH
        // (which cannot run inside one) succeeds.
        DB::statement("ATTACH DATABASE ':memory:' AS public");
        DB::statement('CREATE TABLE public.outlets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            url TEXT NOT NULL,
            region TEXT NOT NULL,
            language TEXT NOT NULL,
            vertical TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            priority INTEGER NOT NULL DEFAULT 2,
            created_at DATETIME,
            updated_at DATETIME
        )');
    }

    private function seedOutlet(array $overrides = []): Outlet
    {
        return Outlet::query()->create(array_merge([
            'id' => 'bbc',
            'name' => 'bbc',
            'display_name' => 'BBC',
            'url' => 'https://www.bbc.com/',
            'region' => 'global',
            'language' => 'en',
            'vertical' => 'general',
            'active' => true,
            'priority' => 1,
        ], $overrides));
    }

    private function jsonUpload(array $payload): UploadedFile
    {
        $path = tempnam(sys_get_temp_dir(), 'outlets').'.json';
        file_put_contents($path, json_encode($payload));

        return new UploadedFile($path, 'outlets.json', 'application/json', null, true);
    }

    // ── Export ────────────────────────────────────────────────────────────────

    public function test_export_streams_json_in_round_trip_seed_shape(): void
    {
        $user = User::factory()->create();
        $this->seedOutlet(['id' => 'bbc', 'priority' => 1]);
        $this->seedOutlet([
            'id' => 'wired',
            'name' => 'wired',
            'display_name' => 'Wired',
            'url' => 'https://www.wired.com/',
            'vertical' => 'tech',
            'priority' => 2,
        ]);

        $response = $this->actingAs($user)->get('/outlets/export');

        $response->assertOk();
        $response->assertHeader('content-type', 'application/json');

        $rows = json_decode($response->streamedContent(), true);
        $this->assertCount(2, $rows);

        // Every row carries exactly the seed fields — no timestamps, no extras.
        foreach ($rows as $row) {
            $this->assertSame(self::SEED_FIELDS, array_keys($row));
        }

        // Types match the seed: active is a real bool, priority a real int.
        $this->assertIsBool($rows[0]['active']);
        $this->assertIsInt($rows[0]['priority']);
    }

    public function test_export_is_available_to_any_authenticated_role(): void
    {
        $viewer = User::factory()->viewer()->create();
        $this->seedOutlet();

        $this->actingAs($viewer)->get('/outlets/export')->assertOk();
    }

    // ── Import: validation + preview (no write) ────────────────────────────────

    public function test_import_preview_reports_create_update_error_without_writing(): void
    {
        $operator = User::factory()->operator()->create();
        // One existing outlet so the "changed" entry classifies as an update.
        $this->seedOutlet(['id' => 'bbc', 'display_name' => 'BBC']);

        $upload = $this->jsonUpload([
            // create
            [
                'id' => 'newoutlet',
                'name' => 'newoutlet',
                'display_name' => 'New Outlet',
                'url' => 'https://new.example.com/',
                'region' => 'global',
                'language' => 'en',
                'vertical' => 'tech',
                'active' => true,
                'priority' => 2,
            ],
            // update (bbc already exists; display_name changed)
            [
                'id' => 'bbc',
                'name' => 'bbc',
                'display_name' => 'BBC News',
                'url' => 'https://www.bbc.com/',
                'region' => 'global',
                'language' => 'en',
                'vertical' => 'general',
                'active' => true,
                'priority' => 1,
            ],
            // invalid (bad region enum + missing url)
            [
                'id' => 'badone',
                'name' => 'badone',
                'display_name' => 'Bad One',
                'region' => 'mars',
                'language' => 'en',
                'vertical' => 'general',
                'active' => true,
                'priority' => 9,
            ],
        ]);

        $response = $this->actingAs($operator)->post('/outlets/import/preview', [
            'file' => $upload,
        ]);

        $response->assertRedirect();
        $preview = session('importPreview');

        $this->assertSame(1, $preview['summary']['create']);
        $this->assertSame(1, $preview['summary']['update']);
        $this->assertSame(1, $preview['summary']['error']);

        // Nothing was written: bbc unchanged, no new rows.
        $this->assertSame(1, Outlet::query()->count());
        $this->assertSame('BBC', Outlet::query()->find('bbc')->display_name);
    }

    public function test_import_preview_rejects_malformed_file(): void
    {
        $operator = User::factory()->operator()->create();
        // A JSON object (not a list) is malformed for our import.
        $upload = $this->jsonUpload(['not' => 'a list']);

        $response = $this->actingAs($operator)->post('/outlets/import/preview', [
            'file' => $upload,
        ]);

        $response->assertRedirect();
        $this->assertNotNull(session('error'));
        $this->assertNull(session('importPreview'));
    }

    // ── Import: apply (upsert) + audit ──────────────────────────────────────────

    public function test_import_apply_upserts_and_audits(): void
    {
        $operator = User::factory()->operator()->create();
        $this->seedOutlet(['id' => 'bbc', 'display_name' => 'BBC', 'priority' => 1]);

        $rows = [
            [
                'id' => 'newoutlet',
                'name' => 'newoutlet',
                'display_name' => 'New Outlet',
                'url' => 'https://new.example.com/',
                'region' => 'global',
                'language' => 'en',
                'vertical' => 'tech',
                'active' => true,
                'priority' => 2,
            ],
            [
                'id' => 'bbc',
                'name' => 'bbc',
                'display_name' => 'BBC News',
                'url' => 'https://www.bbc.com/',
                'region' => 'global',
                'language' => 'en',
                'vertical' => 'general',
                'active' => false,
                'priority' => 1,
            ],
        ];

        $response = $this->actingAs($operator)->post('/outlets/import/apply', [
            'outlets' => $rows,
        ]);

        $response->assertRedirect(route('outlets.index'));

        // New row created.
        $new = Outlet::query()->find('newoutlet');
        $this->assertNotNull($new);
        $this->assertSame('New Outlet', $new->display_name);

        // Existing row updated (display_name + active changed).
        $bbc = Outlet::query()->find('bbc');
        $this->assertSame('BBC News', $bbc->display_name);
        $this->assertFalse((bool) $bbc->active);

        // Audit: per-row created/updated + a summary row.
        $this->assertSame(1, AuditLog::query()->where('action', 'outlet.created')->where('target_id', 'newoutlet')->count());
        $this->assertSame(1, AuditLog::query()->where('action', 'outlet.updated')->where('target_id', 'bbc')->count());

        $summary = AuditLog::query()->where('action', 'outlet.imported')->first();
        $this->assertNotNull($summary);
        $this->assertSame(['created' => 1, 'updated' => 1], $summary->after);
    }

    public function test_import_apply_aborts_when_a_row_is_invalid(): void
    {
        $operator = User::factory()->operator()->create();

        $response = $this->actingAs($operator)->post('/outlets/import/apply', [
            'outlets' => [
                ['id' => 'bad', 'name' => 'bad', 'display_name' => 'Bad', 'region' => 'mars', 'language' => 'en', 'vertical' => 'general', 'active' => true, 'priority' => 9],
            ],
        ]);

        $response->assertRedirect();
        $this->assertNotNull(session('error'));
        $this->assertSame(0, Outlet::query()->count());
    }

    // ── RBAC: import is operator+ ───────────────────────────────────────────────

    public function test_viewer_is_forbidden_from_import(): void
    {
        $viewer = User::factory()->viewer()->create();

        $this->actingAs($viewer)->post('/outlets/import/preview', [])->assertForbidden();
        $this->actingAs($viewer)->post('/outlets/import/apply', [])->assertForbidden();
    }
}
