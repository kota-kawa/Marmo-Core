<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Category extends Model
{
    use HasFactory;

    protected $fillable = [
        'name',
        'slug',
        'icon',
        'description',
    ];

    public function projects()
    {
        return $this->hasMany(Project::class);
    }

    public function subcategories()
    {
        return $this->hasMany(Subcategory::class);
    }
}
