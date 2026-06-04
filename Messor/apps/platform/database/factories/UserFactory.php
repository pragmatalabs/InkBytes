<?php

namespace Database\Factories;

use App\Models\User;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

/**
 * @extends Factory<User>
 */
class UserFactory extends Factory
{
    /**
     * The current password being used by the factory.
     */
    protected static ?string $password;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'name' => fake()->name(),
            'email' => fake()->unique()->safeEmail(),
            // Default to admin so existing feature suites (which exercise
            // mutations) keep passing. Use the role states below to test the
            // RBAC gate explicitly. See ADR-0005.
            'role' => User::ROLE_ADMIN,
            'email_verified_at' => now(),
            'password' => static::$password ??= Hash::make('password'),
            'remember_token' => Str::random(10),
        ];
    }

    /** Admin — full access. */
    public function admin(): static
    {
        return $this->state(fn (array $attributes) => ['role' => User::ROLE_ADMIN]);
    }

    /** Operator — outlet/scraping/moderation mutations; no keys/settings/users. */
    public function operator(): static
    {
        return $this->state(fn (array $attributes) => ['role' => User::ROLE_OPERATOR]);
    }

    /** Viewer — read-only. */
    public function viewer(): static
    {
        return $this->state(fn (array $attributes) => ['role' => User::ROLE_VIEWER]);
    }

    /**
     * Indicate that the model's email address should be unverified.
     */
    public function unverified(): static
    {
        return $this->state(fn (array $attributes) => [
            'email_verified_at' => null,
        ]);
    }
}
