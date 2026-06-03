<?php

namespace Tests\Feature;

use App\Models\ApiKey;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

class ApiKeysTest extends TestCase
{
    use RefreshDatabase;

    public function test_index_is_displayed(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/api-keys')->assertOk();
    }

    public function test_key_is_stored_encrypted_and_never_returned_raw(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->post('/api-keys', [
            'provider' => 'openai',
            'label' => 'prod',
            'value' => 'sk-super-secret-1234',
            'active' => true,
        ])->assertRedirect(route('api-keys.index'));

        $key = ApiKey::first();
        $this->assertNotNull($key);

        // Decrypts transparently in PHP via the cast.
        $this->assertSame('sk-super-secret-1234', $key->value);

        // ...but the raw column holds ciphertext, not the plaintext.
        $raw = DB::table('api_keys')->where('id', $key->id)->value('value');
        $this->assertNotSame('sk-super-secret-1234', $raw);
        $this->assertStringNotContainsString('sk-super-secret-1234', $raw);

        // Masked form shows only the last 4, and serialization hides the value.
        $this->assertStringEndsWith('1234', $key->masked());
        $this->assertArrayNotHasKey('value', $key->toArray());
    }

    public function test_rotate_keeps_existing_secret_when_value_blank(): void
    {
        $user = User::factory()->create();
        $key = ApiKey::create([
            'provider' => 'anthropic',
            'label' => 'old',
            'value' => 'sk-original-9999',
            'active' => true,
        ]);

        $this->actingAs($user)->put("/api-keys/{$key->id}", [
            'label' => 'renamed',
            'value' => '', // blank => keep existing secret
            'active' => false,
        ])->assertRedirect(route('api-keys.index'));

        $key->refresh();
        $this->assertSame('renamed', $key->label);
        $this->assertFalse($key->active);
        $this->assertSame('sk-original-9999', $key->value);
    }

    public function test_key_can_be_deleted(): void
    {
        $user = User::factory()->create();
        $key = ApiKey::create([
            'provider' => 'openai',
            'value' => 'sk-delete-me-0000',
            'active' => true,
        ]);

        $this->actingAs($user)
            ->delete("/api-keys/{$key->id}")
            ->assertRedirect(route('api-keys.index'));

        $this->assertNull(ApiKey::find($key->id));
    }
}
