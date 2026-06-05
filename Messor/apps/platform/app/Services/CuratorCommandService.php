<?php

namespace App\Services;

use Illuminate\Http\Client\PendingRequest;
use Illuminate\Support\Facades\Http;
use RuntimeException;

/**
 * Publishes Backoffice → Curator moderation commands over RabbitMQ (Phase 2.3).
 *
 * Curator owns all writes to public.events / public.pages (ADR-0003); the
 * Backoffice never mutates those tables directly. Instead it publishes a JSON
 * command and Curator's consumer performs the write / skill re-run.
 *
 * Transport: the RabbitMQ **management HTTP API**, called with Guzzle via the
 * Laravel HTTP client. We deliberately avoid an AMQP composer package
 * (php-amqplib): Laravel already ships Guzzle, the only thing we need is
 * fire-one-message-and-forget, and the management API's
 * `POST /api/exchanges/{vhost}/{exchange}/publish` does exactly that with HTTP
 * basic auth. See docs/lessons-learned.md for the rationale.
 *
 * Commands (routing key → payload):
 *   page.publish        {"id": "<page id>"}
 *   page.unpublish      {"id": "<page id>"}
 *   page.drop           {"id": "<page id>"}
 *   event.resynthesize  {"id": "<event id>"}
 *   event.recluster     {"id": "<event id>"}
 *   embeddings.reembed  {"id": "all"|"missing"}   (ADR-0004; corpus re-embed)
 */
class CuratorCommandService
{
    public const COMMANDS = [
        'page.publish',
        'page.unpublish',
        'page.drop',
        'event.resynthesize',
        'event.recluster',
        'embeddings.reembed',
    ];

    public function publishPage(string $pageId): bool
    {
        return $this->publish('page.publish', $pageId);
    }

    public function unpublishPage(string $pageId): bool
    {
        return $this->publish('page.unpublish', $pageId);
    }

    public function dropPage(string $pageId): bool
    {
        return $this->publish('page.drop', $pageId);
    }

    public function resynthesizeEvent(string $eventId): bool
    {
        return $this->publish('event.resynthesize', $eventId);
    }

    public function reclusterEvent(string $eventId): bool
    {
        return $this->publish('event.recluster', $eventId);
    }

    /**
     * Trigger a corpus re-embed (ADR-0004). $scope is "all" (overwrite every
     * article's vector with the current embedder) or "missing" (only NULLs).
     */
    public function reembedCorpus(string $scope = 'all'): bool
    {
        return $this->publish('embeddings.reembed', $scope);
    }

    /**
     * Publish one command to the Curator commands exchange.
     *
     * @param  string  $command  one of self::COMMANDS — used as the routing key
     * @param  string  $targetId  the page id / event id the command acts on
     * @return bool  true when RabbitMQ reports the message was routed
     *
     * @throws RuntimeException on an unknown command or an unroutable message
     */
    public function publish(string $command, string $targetId): bool
    {
        if (! in_array($command, self::COMMANDS, true)) {
            throw new RuntimeException("Unknown Curator command: {$command}");
        }

        $cfg = config('services.curator.rabbitmq');
        $vhost = rawurlencode($cfg['vhost'] ?? '/');
        $exchange = $cfg['commands_exchange'];
        $base = rtrim($cfg['management_url'], '/')
            ."/api/exchanges/{$vhost}/".rawurlencode($exchange);

        // Idempotently ensure the durable topic exchange exists. Curator's
        // consumer also declares it on startup; declaring it here means an
        // admin can issue commands even if Curator hasn't booted yet (the
        // message then waits for the queue to be bound, but at least the
        // exchange is present and the call doesn't 404).
        $this->client($cfg)->put($base, [
            'type' => 'topic',
            'durable' => true,
            'auto_delete' => false,
        ]);

        $response = $this->client($cfg)->post($base.'/publish', [
            'properties' => ['delivery_mode' => 2, 'content_type' => 'application/json'],
            'routing_key' => $command,
            'payload' => json_encode(['id' => $targetId], JSON_THROW_ON_ERROR),
            'payload_encoding' => 'string',
        ]);

        if (! $response->successful()) {
            throw new RuntimeException(
                "RabbitMQ publish failed (HTTP {$response->status()}) for {$command}."
            );
        }

        // The management API returns {"routed": true|false}. A false here means
        // the exchange exists but no queue is bound — surface it so the admin
        // knows Curator's consumer isn't listening.
        $routed = (bool) ($response->json('routed') ?? false);

        if (! $routed) {
            throw new RuntimeException(
                "Command {$command} was published but not routed — is Curator's "
                .'commands consumer running?'
            );
        }

        return true;
    }

    /**
     * Build the authenticated, short-timeout HTTP client for the mgmt API.
     */
    private function client(array $cfg): PendingRequest
    {
        return Http::withBasicAuth($cfg['user'], $cfg['password'])
            ->timeout(8)
            ->acceptJson()
            ->asJson();
    }
}
