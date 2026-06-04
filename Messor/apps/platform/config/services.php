<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    /*
    | Curator moderation commands (Phase 2.3).
    |
    | The Backoffice publishes JSON commands (page.publish / page.unpublish /
    | page.drop / event.resynthesize / event.recluster) to a RabbitMQ topic
    | exchange that Curator consumes. We publish via the RabbitMQ *management
    | HTTP API* (Guzzle, no AMQP composer package) — see CuratorCommandService
    | and docs/lessons-learned.md.
    */
    'curator' => [
        // Curator FastAPI base — health + pipeline status probe (B6).
        'url' => env('CURATOR_URL', 'http://localhost:8060'),
        'rabbitmq' => [
            // Management HTTP API base (note: port 15672, not the AMQP 5672).
            'management_url' => env('RABBITMQ_MANAGEMENT_URL', 'http://localhost:15672'),
            'user' => env('RABBITMQ_USER', 'messor'),
            'password' => env('RABBITMQ_PASSWORD', 'messor'),
            'vhost' => env('RABBITMQ_VHOST', '/'),
            'commands_exchange' => env('CURATOR_COMMANDS_EXCHANGE', 'curator.commands'),
        ],
    ],

    /*
    | Messor harvester FastAPI base — reachability probe for the unified health
    | dashboard (B6). Messor exposes no /health, so the controller probes a cheap
    | read endpoint (GET /api/scrapesessions?page=1&limit=1).
    */
    'messor' => [
        'url' => env('MESSOR_URL', 'http://localhost:8050'),
    ],

];
