<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

/**
 * ApiKey — a provider API key managed by the Backoffice (store/rotate/mask/test).
 *
 * Backoffice-owned (ADR-0001 / ADR-0003); lives in the `backoffice` schema.
 *
 * Security (ADR-0004 + handoff §1):
 *  - `value` uses Laravel's `encrypted` cast → ciphertext at rest.
 *  - Never serialise `value` directly to the client; expose only `masked()`.
 *  - Curator does NOT read this table; it loads real keys from env.
 */
class ApiKey extends Model
{
    protected $table = 'api_keys';

    protected $fillable = [
        'provider',
        'label',
        'value',
        'active',
    ];

    protected $casts = [
        // AES-256 via APP_KEY; transparently decrypts on read in PHP only.
        'value' => 'encrypted',
        'active' => 'boolean',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * Hide the raw (decrypted) value from any array/JSON serialisation so it
     * can never leak through an accidental `->toArray()` / `->toJson()`.
     */
    protected $hidden = [
        'value',
    ];

    /**
     * A masked form safe to send to the UI: last 4 chars only.
     */
    public function masked(): string
    {
        $raw = (string) $this->value;
        $len = strlen($raw);

        if ($len === 0) {
            return '';
        }

        $tail = substr($raw, -4);

        return str_repeat('•', max(4, $len - 4)).$tail;
    }
}
