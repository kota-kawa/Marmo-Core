<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class ClientProfile extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'profile_photo',
        'design_type',
        'budget_range',
        'location',
        'timeline',
        'property_size',
        'style_preference',
        'notes',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
