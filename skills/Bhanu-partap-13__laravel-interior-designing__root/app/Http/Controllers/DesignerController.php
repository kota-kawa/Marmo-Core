<?php

namespace App\Http\Controllers;

use App\Http\Requests\UpdateDesignerRequest;
use App\Models\Designer;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class DesignerController extends Controller
{
    public function index(Request $request)
    {
        $specialties = Designer::query()
            ->whereNotNull('specialization')
            ->distinct()
            ->orderBy('specialization')
            ->pluck('specialization');

        $designers = Designer::with('user')
            ->withCount('projects')
            ->when($request->filled('specialty'), function ($query) use ($request) {
                $query->where('specialization', $request->specialty);
            })
            ->latest()
            ->paginate(9)
            ->withQueryString();

        return view('designers.index', compact('designers', 'specialties'));
    }

    public function show(string $designer)
    {
        $designer = Designer::with('user')
            ->where('slug', $designer)
            ->firstOrFail();

        $projects = $designer->projects()
            ->with('category')
            ->where('is_published', true)
            ->latest()
            ->get();

        return view('designers.show', compact('designer', 'projects'));
    }

    public function edit(Request $request)
    {
        $designer = $request->user()->designer;

        return view('dashboard.profile', compact('designer'));
    }

    public function update(UpdateDesignerRequest $request)
    {
        $designer = $request->user()->designer;

        if (!$designer) {
            abort(403, 'Designer profile missing.');
        }

        $data = $request->validated();

        if ($request->hasFile('profile_photo')) {
            if ($designer->profile_photo && Storage::disk('public')->exists($designer->profile_photo)) {
                Storage::disk('public')->delete($designer->profile_photo);
            }
            $data['profile_photo'] = $request->file('profile_photo')->store('profiles', 'public');
        }

        if (empty($designer->slug)) {
            $data['slug'] = $this->uniqueSlug($request->user()->name);
        }

        $designer->update($data);

        $redirect = $request->input('redirect_to');

        if ($redirect && Route::has($redirect)) {
            return redirect()->route($redirect)
                ->with('status', 'Profile updated.');
        }

        return back()->with('status', 'Profile updated.');
    }

    private function uniqueSlug(string $name): string
    {
        $base = Str::slug($name);
        $slug = $base;
        $counter = 1;

        while (Designer::where('slug', $slug)->exists()) {
            $slug = $base.'-'.$counter;
            $counter++;
        }

        return $slug;
    }
}
