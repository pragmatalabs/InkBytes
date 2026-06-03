<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * model_usage — one row per completed LLM call (tokens + cost).
 *
 * Backoffice-owned DDL (ADR-0001 / ADR-0003): this table lands in the
 * `backoffice` schema via the connection search_path. **Laravel owns the DDL.**
 * Curator only INSERTs data into it (schema-qualified `backoffice.model_usage`),
 * the same cross-schema data-write pattern it uses for `public.outlets` —
 * it never creates or alters this table.
 *
 * `event_id` is a nullable plain text column holding Curator's event id
 * (`public.events.id`, a TEXT key). It is intentionally NOT a foreign key:
 * cross-schema FKs are avoided (ADR-0003) and enrich calls happen before an
 * event exists, so the column is frequently NULL.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('model_usage', function (Blueprint $table) {
            $table->id();

            // Which skill made the call: "enrich" / "synthesize".
            $table->string('call_label', 64);
            // The model that served the call, e.g. "claude-haiku-4-5".
            $table->string('model', 120);

            $table->unsignedBigInteger('input_tokens')->default(0);
            $table->unsignedBigInteger('output_tokens')->default(0);
            // List-price cost for this single call, in USD.
            $table->decimal('cost_usd', 12, 6)->default(0);

            // Curator's event id (public.events.id, TEXT). Nullable, no cross-
            // schema FK (ADR-0003). NULL for enrich calls (pre-clustering).
            $table->text('event_id')->nullable();

            // Curator sets this to the call's completion time (timestamptz).
            $table->timestampTz('created_at')->useCurrent();

            $table->index('model');
            $table->index('created_at');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('model_usage');
    }
};
