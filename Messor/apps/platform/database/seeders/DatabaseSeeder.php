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
        // Dev admin so the Backoffice is usable immediately after `php artisan db:seed`.
        // Override in real environments; never ship these credentials to production.
        User::query()->updateOrCreate([
            'email' => 'admin@inkbytes.test',
        ], [
            'name' => 'Admin',
            'email_verified_at' => now(),
            'password' => Hash::make('password123'),
        ]);

        // Outlets are seeded by Curator into public.outlets (seed-if-empty);
        // the Backoffice does not seed them. See ADR-0003.
    }
}
