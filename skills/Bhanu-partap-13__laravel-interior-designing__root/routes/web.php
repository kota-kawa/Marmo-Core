<?php

use App\Http\Controllers\Auth\LoginController;
use App\Http\Controllers\Auth\PasswordResetController;
use App\Http\Controllers\Auth\RegisterController;
use App\Http\Controllers\CategoryController;
use App\Http\Controllers\ClientDashboardController;
use App\Http\Controllers\ContactController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\Dashboard\InquiryController as DashboardInquiryController;
use App\Http\Controllers\Dashboard\ProjectController as DashboardProjectController;
use App\Http\Controllers\DesignerController;
use App\Http\Controllers\InquiryController;
use App\Http\Controllers\LocaleController;
use App\Http\Controllers\ProjectController;
use Illuminate\Support\Facades\Route;

Route::get('/', [\App\Http\Controllers\HomeController::class, 'index'])->name('home');
Route::view('/contact', 'home.contact')->name('contact');
Route::post('/contact', [ContactController::class, 'store'])->name('contact.store');

Route::get('/login', [LoginController::class, 'showForm'])->name('login');
Route::get('/register', [RegisterController::class, 'showForm'])->name('register');
Route::get('/forgot-password', [PasswordResetController::class, 'requestForm'])->name('password.request');
Route::post('/forgot-password', [PasswordResetController::class, 'email'])->name('password.email');
Route::get('/reset-password/{token}', [PasswordResetController::class, 'resetForm'])->name('password.reset');
Route::post('/reset-password', [PasswordResetController::class, 'update'])->name('password.update');

Route::get('/lang/{locale}', [LocaleController::class, 'update'])->name('locale.switch');

Route::prefix('designers')->name('designers.')->group(function () {
    Route::get('/', [DesignerController::class, 'index'])->name('index');
    Route::get('/{designer}', [DesignerController::class, 'show'])->name('show');
});

Route::prefix('projects')->name('projects.')->group(function () {
    Route::get('/', [ProjectController::class, 'index'])->name('index');
    Route::get('/{project}', [ProjectController::class, 'show'])->name('show');
});

Route::get('/categories/{category}', [CategoryController::class, 'show'])
    ->name('categories.show');

Route::prefix('auth')->name('auth.')->group(function () {
    Route::get('/login', [LoginController::class, 'showForm'])->name('login');
    Route::post('/login', [LoginController::class, 'login'])
        ->middleware('throttle:login')
        ->name('login.store');
    Route::post('/logout', [LoginController::class, 'logout'])->name('logout');
    Route::get('/register', [RegisterController::class, 'showForm'])->name('register');
    Route::post('/register', [RegisterController::class, 'register'])->name('register.store');
});

Route::post('/inquiries', [InquiryController::class, 'store'])
    ->middleware('throttle:inquiries')
    ->name('inquiries.store');

Route::middleware(['auth', 'designer'])->prefix('dashboard')->name('dashboard.')->group(function () {
    Route::get('/', [DashboardController::class, 'index'])->name('index');
    Route::get('/profile', [DesignerController::class, 'edit'])->name('profile.edit');
    Route::put('/profile', [DesignerController::class, 'update'])->name('profile.update');
    Route::resource('projects', DashboardProjectController::class)->except(['show']);
    Route::get('/inquiries', [DashboardInquiryController::class, 'index'])->name('inquiries.index');
    Route::patch('/inquiries/{inquiry}', [DashboardInquiryController::class, 'update'])->name('inquiries.update');
});

Route::middleware(['auth', 'client'])->prefix('client')->name('client.')->group(function () {
    Route::get('/dashboard', [ClientDashboardController::class, 'index'])->name('dashboard');
    Route::put('/profile', [ClientDashboardController::class, 'update'])->name('profile.update');
});
