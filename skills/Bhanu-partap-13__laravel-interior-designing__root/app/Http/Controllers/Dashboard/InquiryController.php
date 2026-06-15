<?php

namespace App\Http\Controllers\Dashboard;

use App\Http\Controllers\Controller;
use App\Models\Inquiry;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class InquiryController extends Controller
{
    public function index(Request $request)
    {
        $designer = $request->user()->designer;

        $inquiries = $designer
            ? Inquiry::with('project')
                ->whereHas('project', function ($query) use ($designer) {
                    $query->where('designer_id', $designer->id);
                })
                ->latest()
                ->paginate(10)
                ->withQueryString()
            : collect();

        return view('dashboard.inquiries.index', compact('inquiries', 'designer'));
    }

    public function update(Inquiry $inquiry, Request $request): RedirectResponse
    {
        $designer = $request->user()->designer;

        if (!$designer || $inquiry->project->designer_id !== $designer->id) {
            abort(403, 'Not authorized to update this inquiry.');
        }

        $validated = $request->validate([
            'status' => ['required', 'in:pending,replied,closed'],
        ]);

        $inquiry->update(['status' => $validated['status']]);

        return back()->with('status', 'Inquiry updated.');
    }
}
