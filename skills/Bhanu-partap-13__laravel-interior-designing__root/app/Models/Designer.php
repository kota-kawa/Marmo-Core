<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Designer extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'slug',
        'bio',
        'specialization',
        'city',
        'phone',
        'profile_photo',
        'portfolio_url',
        'education',
        'certifications',
        'years_experience',
        'is_verified',
    ];

    protected $casts = [
        'is_verified' => 'boolean',
        'years_experience' => 'integer',
    ];

    public function requiredProfileFields(): array
    {
        return [
            'phone',
            'years_experience',
            'education',
            'certifications',
            'profile_photo',
        ];
    }

    public function profileCompletionFields(): array
    {
        return [
            'bio',
            'specialization',
            'city',
            'phone',
            'portfolio_url',
            'profile_photo',
            'years_experience',
            'education',
            'certifications',
        ];
    }

    public function isProfileComplete(): bool
    {
        foreach ($this->requiredProfileFields() as $field) {
            if (empty($this->{$field})) {
                return false;
            }
        }

        return true;
    }

    public function profileCompletionScore(): int
    {
        $fields = $this->profileCompletionFields();
        $filled = 0;

        foreach ($fields as $field) {
            if (!empty($this->{$field})) {
                $filled++;
            }
        }

        return $fields ? (int) round(($filled / count($fields)) * 100) : 0;
    }

    public function user()
    {
        return $this->belongsTo(User::class);
    }

    public function projects()
    {
        return $this->hasMany(Project::class);
    }
}
