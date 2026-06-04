<?php

namespace Tests\Feature;

use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

/**
 * B2 — minimal user/role management (admin-only). Role changes are audited and
 * the last admin can never be demoted (zero-admin lockout guard).
 */
class UserManagementTest extends TestCase
{
    use RefreshDatabase;

    public function test_admin_sees_users_index(): void
    {
        $admin = User::factory()->admin()->create();
        User::factory()->viewer()->create();

        $this->actingAs($admin)->get('/users')->assertOk();
    }

    public function test_admin_can_change_a_role_and_it_is_audited(): void
    {
        $admin = User::factory()->admin()->create();
        $target = User::factory()->viewer()->create();

        $this->actingAs($admin)
            ->put(route('users.update-role', $target->id), ['role' => 'operator'])
            ->assertRedirect(route('users.index'))
            ->assertSessionHas('success');

        $this->assertSame(User::ROLE_OPERATOR, $target->refresh()->role);

        $log = AuditLog::query()->where('action', 'user.role_changed')->firstOrFail();
        $this->assertSame('user', $log->target_type);
        $this->assertSame((string) $target->id, $log->target_id);
        $this->assertSame('viewer', $log->before['role']);
        $this->assertSame('operator', $log->after['role']);
        $this->assertSame($admin->email, $log->actor_email);
    }

    public function test_cannot_demote_the_last_admin(): void
    {
        // Only one admin exists.
        $admin = User::factory()->admin()->create();
        User::factory()->viewer()->create();

        $this->actingAs($admin)
            ->put(route('users.update-role', $admin->id), ['role' => 'viewer'])
            ->assertRedirect(route('users.index'))
            ->assertSessionHas('error');

        $this->assertSame(User::ROLE_ADMIN, $admin->refresh()->role);
        $this->assertDatabaseMissing('audit_logs', ['action' => 'user.role_changed']);
    }

    public function test_can_demote_an_admin_when_another_admin_exists(): void
    {
        $admin = User::factory()->admin()->create();
        $secondAdmin = User::factory()->admin()->create();

        $this->actingAs($admin)
            ->put(route('users.update-role', $secondAdmin->id), ['role' => 'operator'])
            ->assertRedirect(route('users.index'))
            ->assertSessionHas('success');

        $this->assertSame(User::ROLE_OPERATOR, $secondAdmin->refresh()->role);
    }

    public function test_invalid_role_is_rejected(): void
    {
        $admin = User::factory()->admin()->create();
        $target = User::factory()->viewer()->create();

        $this->actingAs($admin)
            ->put(route('users.update-role', $target->id), ['role' => 'superuser'])
            ->assertSessionHasErrors('role');

        $this->assertSame(User::ROLE_VIEWER, $target->refresh()->role);
    }

    public function test_non_admin_cannot_access_user_management(): void
    {
        $operator = User::factory()->operator()->create();
        $target = User::factory()->viewer()->create();

        $this->actingAs($operator)->get('/users')->assertForbidden();
        $this->actingAs($operator)
            ->put(route('users.update-role', $target->id), ['role' => 'admin'])
            ->assertForbidden();
    }
}
