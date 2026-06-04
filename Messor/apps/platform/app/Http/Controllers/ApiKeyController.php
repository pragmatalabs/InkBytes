<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Concerns\PaginatesQueries;
use App\Models\ApiKey;
use App\Models\AuditLog;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

/**
 * Store / rotate / mask / test provider API keys (Backoffice-owned, ADR-0003).
 *
 * Security (ADR-0004 + handoff §1):
 *  - `value` is encrypted at rest (model `encrypted` cast).
 *  - The raw key is NEVER returned to the client or logged — only `masked()`.
 *  - Curator does NOT read this table; it loads real keys from env. This vault
 *    is for human key management (store, rotate, test) only.
 */
class ApiKeyController extends Controller
{
    use PaginatesQueries;

    private const PROVIDERS = ['anthropic', 'openai'];

    /** The apikey.* audit actions B1 records — the history view's filter set. */
    private const HISTORY_ACTIONS = [
        'apikey.created',
        'apikey.updated',
        'apikey.deactivated',
        'apikey.deleted',
    ];

    public function index(): Response
    {
        return Inertia::render('ApiKeys/Index', [
            'keys' => ApiKey::query()
                ->orderBy('provider')
                ->orderByDesc('created_at')
                ->get()
                ->map(fn (ApiKey $key): array => $this->present($key))
                ->values(),
            'providers' => self::PROVIDERS,
            // UI honesty (B8 §3): last-used / spend-per-key are N/A by design —
            // Curator uses env keys (ADR-0004), so nothing stamps a "used at" or
            // ties spend to a DB key. Surface that, don't show empty columns.
            'tracking' => [
                'last_used' => false,
                'spend_per_key' => false,
                'note' => 'Not tracked — Curator uses env keys (ADR-0004).',
            ],
        ]);
    }

    /**
     * Read-only rotation / change history for API keys (B8 §2): a filtered view
     * of backoffice.audit_logs where target_type='apikey'. B1 already records
     * create / update / delete / deactivate with ONLY non-secret metadata
     * (provider / label / masked last-4 / active), so no key material is ever
     * present in these rows. Server-paginated (B7 trait) + filterable by action.
     */
    public function history(Request $request): Response
    {
        $sortable = ['created_at', 'action'];
        [$sort, $dir] = $this->resolveSort($request, $sortable, 'created_at', 'desc');
        $perPage = $this->resolvePerPage($request);

        $query = AuditLog::query()->where('target_type', 'apikey');

        $action = trim((string) $request->query('action', ''));
        if ($action !== '' && in_array($action, self::HISTORY_ACTIONS, true)) {
            $query->where('action', $action);
        }

        // Stable tiebreaker so equal timestamps order deterministically.
        $logs = $this->paginateList($request, $query, ['action', 'actor_name', 'actor_email'], $sort, $dir, $perPage)
            ->through(fn (AuditLog $log): array => $this->presentHistory($log));

        return Inertia::render('ApiKeys/History', [
            'logs' => $logs,
            'state' => $this->listState($request, $sort, $dir, $perPage),
            'action' => $action,
            'actions' => self::HISTORY_ACTIONS,
        ]);
    }

    public function store(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'provider' => ['required', Rule::in(self::PROVIDERS)],
            'label' => ['nullable', 'string', 'max:120'],
            'value' => ['required', 'string', 'min:8', 'max:500'],
            'active' => ['required', 'boolean'],
        ]);

        // One-active-per-provider (B8 §1): if this key comes in active, demote
        // the currently-active key of the same provider first, in one
        // transaction. Deactivate-then-activate so we never trip the partial
        // unique index `(provider) WHERE active`.
        $key = DB::transaction(function () use ($data): ApiKey {
            if ($data['active']) {
                $this->deactivateActiveFor($data['provider']);
            }

            return ApiKey::query()->create($data);
        });

        // CRITICAL: never audit the raw/encrypted secret — only safe metadata.
        AuditLog::record('apikey.created', 'apikey', (string) $key->id, null, $this->auditSnapshot($key));

        return redirect()
            ->route('api-keys.index')
            ->with('success', "{$data['provider']} key stored (encrypted).");
    }

    /**
     * Rotate = replace the secret value (and optionally label/active) in place.
     */
    public function update(Request $request, ApiKey $apiKey): RedirectResponse
    {
        $data = $request->validate([
            'label' => ['nullable', 'string', 'max:120'],
            // Optional on rotate: empty means "keep the existing secret".
            'value' => ['nullable', 'string', 'min:8', 'max:500'],
            'active' => ['required', 'boolean'],
        ]);

        if (empty($data['value'])) {
            unset($data['value']);
        }

        $before = $this->auditSnapshot($apiKey);

        // One-active-per-provider (B8 §1): if this update activates the key,
        // demote the previously-active key of the same provider first, in one
        // transaction. Deactivate-then-activate so we never trip the partial
        // unique index. A no-op when this key was already the active one (it's
        // excluded from the demotion) or when active=false.
        DB::transaction(function () use ($apiKey, $data): void {
            if (! empty($data['active'])) {
                $this->deactivateActiveFor($apiKey->provider, $apiKey->id);
            }

            $apiKey->fill($data)->save();
        });

        // CRITICAL: never audit the raw/encrypted secret — only safe metadata.
        AuditLog::record('apikey.updated', 'apikey', (string) $apiKey->id, $before, $this->auditSnapshot($apiKey->refresh()));

        return redirect()
            ->route('api-keys.index')
            ->with('success', "{$apiKey->provider} key updated.");
    }

    public function destroy(ApiKey $apiKey): RedirectResponse
    {
        $provider = $apiKey->provider;
        $before = $this->auditSnapshot($apiKey);
        $id = (string) $apiKey->id;
        $apiKey->delete();

        // CRITICAL: never audit the raw/encrypted secret — only safe metadata.
        AuditLog::record('apikey.deleted', 'apikey', $id, $before, null);

        return redirect()
            ->route('api-keys.index')
            ->with('success', "{$provider} key deleted.");
    }

    /**
     * Validate a stored key against its provider with a lightweight call.
     * Degrades gracefully when offline. Never echoes the raw key.
     */
    public function test(ApiKey $apiKey): JsonResponse
    {
        $raw = (string) $apiKey->value;

        try {
            [$ok, $message] = match ($apiKey->provider) {
                'anthropic' => $this->testAnthropic($raw),
                'openai' => $this->testOpenai($raw),
                default => [false, 'Unknown provider.'],
            };
        } catch (Throwable $e) {
            // Network/offline or unexpected error — degrade gracefully, no key in the message.
            return response()->json([
                'ok' => false,
                'reachable' => false,
                'message' => 'Could not reach the provider (offline?): '.$e->getMessage(),
            ]);
        }

        return response()->json([
            'ok' => $ok,
            'reachable' => true,
            'message' => $message,
        ]);
    }

    /**
     * @return array{0: bool, 1: string}
     */
    private function testAnthropic(string $key): array
    {
        $resp = Http::timeout(8)
            ->withHeaders([
                'x-api-key' => $key,
                'anthropic-version' => '2023-06-01',
            ])
            ->get('https://api.anthropic.com/v1/models');

        if ($resp->successful()) {
            return [true, 'Key is valid (Anthropic accepted it).'];
        }
        if ($resp->status() === 401) {
            return [false, 'Key rejected (401 Unauthorized).'];
        }

        return [false, "Provider returned HTTP {$resp->status()}."];
    }

    /**
     * @return array{0: bool, 1: string}
     */
    private function testOpenai(string $key): array
    {
        $resp = Http::timeout(8)
            ->withToken($key)
            ->get('https://api.openai.com/v1/models');

        if ($resp->successful()) {
            return [true, 'Key is valid (OpenAI accepted it).'];
        }
        if ($resp->status() === 401) {
            return [false, 'Key rejected (401 Unauthorized).'];
        }

        return [false, "Provider returned HTTP {$resp->status()}."];
    }

    /**
     * Demote the currently-active key of a provider so the new/updated key can
     * become the sole active one. Each demoted key is audited as
     * `apikey.deactivated` (superseded), secret-free. Optionally excludes a key
     * id (the one being activated) so we don't deactivate then re-activate it.
     *
     * Must run inside the caller's transaction.
     */
    private function deactivateActiveFor(string $provider, ?int $exceptId = null): void
    {
        $superseded = ApiKey::query()
            ->where('provider', $provider)
            ->where('active', true)
            ->when($exceptId !== null, fn ($q) => $q->where('id', '!=', $exceptId))
            ->get();

        foreach ($superseded as $old) {
            $before = $this->auditSnapshot($old);
            $old->forceFill(['active' => false])->save();

            // CRITICAL: never audit the raw/encrypted secret — only safe metadata.
            AuditLog::record('apikey.deactivated', 'apikey', (string) $old->id, $before, $this->auditSnapshot($old->refresh()));
        }
    }

    /**
     * History-row projection of an audit log. The B1 before/after snapshots are
     * already secret-free (provider / label / masked last-4 / active) — there is
     * no raw or encrypted key material anywhere in audit_logs.
     *
     * @return array<string, mixed>
     */
    private function presentHistory(AuditLog $log): array
    {
        return [
            'id' => $log->id,
            'actor_name' => $log->actor_name,
            'actor_email' => $log->actor_email,
            'action' => $log->action,
            'target_id' => $log->target_id,
            'before' => $log->before,
            'after' => $log->after,
            'created_at' => $log->created_at?->toIso8601String(),
        ];
    }

    /**
     * Audit-safe snapshot of a key. Contains ONLY non-secret metadata —
     * provider, label, masked last-4 and active flag. The raw/encrypted
     * `value` is NEVER included so no key material ever lands in audit_logs.
     *
     * @return array<string, mixed>
     */
    private function auditSnapshot(ApiKey $key): array
    {
        return [
            'provider' => $key->provider,
            'label' => $key->label,
            'masked' => $key->masked(),
            'active' => (bool) $key->active,
        ];
    }

    /**
     * Client-safe projection — masked value only, never the raw secret.
     *
     * @return array<string, mixed>
     */
    private function present(ApiKey $key): array
    {
        return [
            'id' => $key->id,
            'provider' => $key->provider,
            'label' => $key->label,
            'masked' => $key->masked(),
            'active' => (bool) $key->active,
            'created_at' => $key->created_at?->toIso8601String(),
            'updated_at' => $key->updated_at?->toIso8601String(),
        ];
    }
}
