<?php

namespace App\Http\Controllers;

use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class LocaleController extends Controller
{
    public function update(string $locale, Request $request): RedirectResponse
    {
        $supported = config('app.supported_locales', ['en']);

        if (in_array($locale, $supported, true)) {
            $request->session()->put('locale', $locale);
        }

        return redirect()->back();
    }
}
