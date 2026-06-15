<?php

use Illuminate\Support\Facades\Route;

Route::get('/', \App\Livewire\IssueSubmission::class)->name('home');

Route::get('dashboard', function () {
    $role = auth()->user()->role;
    if (in_array($role, ['admin', 'staff'])) {
        return redirect()->route('staff.dashboard');
    }
    if (in_array($role, ['kepala_it', 'dekan'])) {
        return redirect()->route('executive.dashboard');
    }
    return view('dashboard'); // fallback for dosen or unexpected
})->middleware(['auth', 'verified'])->name('dashboard');

Route::get('/staff/dashboard', \App\Livewire\StaffDashboard::class)
    ->middleware(['auth', 'role:admin,staff'])
    ->name('staff.dashboard');

Route::get('/executive/dashboard', \App\Livewire\ExecutiveDashboard::class)
    ->middleware(['auth', 'role:kepala_it,dekan'])
    ->name('executive.dashboard');

Route::get('/executive/staff-work', \App\Livewire\ExecutiveStaffWork::class)
    ->middleware(['auth', 'role:kepala_it,dekan'])
    ->name('executive.staff-work');

require __DIR__.'/auth.php';
