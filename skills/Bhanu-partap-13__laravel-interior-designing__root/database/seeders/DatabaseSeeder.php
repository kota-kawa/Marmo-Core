<?php

namespace Database\Seeders;

use App\Models\Category;
use App\Models\Designer;
use App\Models\Project;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $categories = [
            [
                'name' => 'Living Room',
                'slug' => 'living-room',
                'description' => 'Gathering spaces designed for calm routines and layered light.',
            ],
            [
                'name' => 'Bedroom',
                'slug' => 'bedroom',
                'description' => 'Private retreats with soft palettes and tailored storage.',
            ],
            [
                'name' => 'Kitchen',
                'slug' => 'kitchen',
                'description' => 'Chef-friendly layouts, natural materials, and warm textures.',
            ],
            [
                'name' => 'Bathroom',
                'slug' => 'bathroom',
                'description' => 'Spa-inspired wet rooms and serene vanity designs.',
            ],
            [
                'name' => 'Home Office',
                'slug' => 'office',
                'description' => 'Focused workspaces with acoustic control and flexible zones.',
            ],
            [
                'name' => 'Dining Room',
                'slug' => 'dining-room',
                'description' => 'Elegant dining spaces crafted for memorable meals.',
            ],
            [
                'name' => 'Kids Room',
                'slug' => 'kids-room',
                'description' => 'Playful, safe, and imaginative spaces for children.',
            ],
            [
                'name' => 'Outdoor',
                'slug' => 'outdoor',
                'description' => 'Balconies, patios, and garden spaces brought to life.',
            ],
            [
                'name' => 'Commercial',
                'slug' => 'commercial',
                'description' => 'Office, retail, and hospitality interiors at scale.',
            ],
            [
                'name' => 'Luxury',
                'slug' => 'luxury',
                'description' => 'Premium bespoke interiors with exceptional craftsmanship.',
            ],
        ];

        foreach ($categories as $category) {
            Category::firstOrCreate(['slug' => $category['slug']], $category);
        }

        $primaryUser = User::factory()->create([
            'name' => 'Ariadne Studio',
            'email' => 'designer@example.com',
            'password' => Hash::make('password'),
            'role' => 'designer',
        ]);

        $secondaryUser = User::factory()->create([
            'name' => 'Lumen Atelier',
            'email' => 'lumen@example.com',
            'password' => Hash::make('password'),
            'role' => 'designer',
        ]);

        $primaryDesigner = Designer::create([
            'user_id' => $primaryUser->id,
            'slug' => Str::slug($primaryUser->name),
            'bio' => 'Residential interiors shaped by natural light and crafted materials.',
            'specialization' => 'Residential',
            'city' => 'Kyoto, JP',
            'phone' => '+81 90 1234 5678',
            'portfolio_url' => 'https://interiorcanvas.test/ariadne',
            'years_experience' => 9,
            'is_verified' => true,
        ]);

        $secondaryDesigner = Designer::create([
            'user_id' => $secondaryUser->id,
            'slug' => Str::slug($secondaryUser->name),
            'bio' => 'Minimal studios focused on calm material palettes and light flow.',
            'specialization' => 'Minimal',
            'city' => 'Copenhagen, DK',
            'phone' => '+45 12 34 56 78',
            'portfolio_url' => 'https://interiorcanvas.test/lumen',
            'years_experience' => 12,
            'is_verified' => true,
        ]);

    }
}
