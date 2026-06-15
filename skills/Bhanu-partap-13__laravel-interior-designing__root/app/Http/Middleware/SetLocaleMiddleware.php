<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\App;
use Symfony\Component\HttpFoundation\Response;

class SetLocaleMiddleware
{
    public function handle(Request $request, Closure $next): Response
    {
        $supported = config('app.supported_locales', ['en']);
        $queryLocale = $request->query('lang');

        if ($request->hasSession()) {
            if ($queryLocale && in_array($queryLocale, $supported, true)) {
                $request->session()->put('locale', $queryLocale);
            }
        }

        $locale = $request->hasSession()
            ? $request->session()->get('locale', config('app.locale'))
            : config('app.locale');

        if (!in_array($locale, $supported, true)) {
            $locale = config('app.locale');
        }

        App::setLocale($locale);

        return $next($request);
    }
}
