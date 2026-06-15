<?php

namespace Database\Seeders;

use App\Models\User;
use App\Models\Category;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // 1. Seed Categories (Hanya kalau belum ada)
        $categories = [
            ['name' => 'Jaringan & WiFi', 'slug' => 'jaringan-wifi', 'description' => 'Kendala koneksi internet.'],
            ['name' => 'Hardware', 'slug' => 'hardware', 'description' => 'Masalah perangkat fisik.'],
            ['name' => 'Software', 'slug' => 'software', 'description' => 'Masalah aplikasi.'],
        ];

        foreach ($categories as $cat) {
            Category::updateOrCreate(['slug' => $cat['slug']], $cat);
        }

        // 2. Buat Admin Utama
        User::updateOrCreate(
            ['email' => 'admin@kampus.ac.id'],
            [
                'id' => (string) Str::uuid(),
                'name' => 'Admin Utama',
                'password' => Hash::make('password123'),
                'role' => 'admin',
            ]
        );

        // 3. Buat Akun Kepala IT (Untuk akses Executive Dashboard)
        User::updateOrCreate(
            ['email' => 'kepalait@kampus.ac.id'],
            [
                'id' => (string) Str::uuid(),
                'name' => 'Kepala IT',
                'password' => Hash::make('kepalait123'),
                'role' => 'kepala_it',
            ]
        );
        
        echo "DATABASE SEEDING SUKSES!\n";
    }
}
