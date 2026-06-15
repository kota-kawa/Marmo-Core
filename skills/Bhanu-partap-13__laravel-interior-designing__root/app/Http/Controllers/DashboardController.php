<?php

namespace App\Http\Controllers;

use App\Models\Inquiry;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function index(Request $request)
    {
        $designer = $request->user()->designer;
        $projects = $designer
            ? $designer->projects()->with('category')->latest()->get()
            : collect();

        $publishedCount = $designer
            ? $designer->projects()->where('is_published', true)->count()
            : 0;
        $draftCount = $designer
            ? $designer->projects()->where('is_published', false)->count()
            : 0;
        $inquiryCount = $designer
            ? Inquiry::whereHas('project', function ($query) use ($designer) {
                $query->where('designer_id', $designer->id);
            })->count()
            : 0;

        $profileScore = 0;
        if ($designer) {
            $profileScore = $designer->profileCompletionScore();
        }

        $metrics = [
            'published' => $publishedCount,
            'drafts' => $draftCount,
            'inquiries' => $inquiryCount,
            'profile' => $profileScore,
        ];

        return view('dashboard.index', compact('metrics', 'designer', 'projects'));
    }
}
