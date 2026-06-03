<?php

namespace App\Http\Controllers;

use App\Models\ApiKey;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
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
    private const PROVIDERS = ['anthropic', 'openai'];

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

        ApiKey::query()->create($data);

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

        $apiKey->fill($data)->save();

        return redirect()
            ->route('api-keys.index')
            ->with('success', "{$apiKey->provider} key updated.");
    }

    public function destroy(ApiKey $apiKey): RedirectResponse
    {
        $provider = $apiKey->provider;
        $apiKey->delete();

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
