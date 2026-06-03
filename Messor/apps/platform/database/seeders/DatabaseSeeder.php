<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        User::query()->updateOrCreate([
            'email' => 'test@example.com',
        ], [
            'name' => 'Test User',
            'email_verified_at' => now(),
            'password' => Hash::make('password'),
        ]);

        // Outlets are seeded by Curator into public.outlets (seed-if-empty);
        // the Backoffice does not seed them. See ADR-0003.
    }
}
