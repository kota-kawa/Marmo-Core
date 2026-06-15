<?php

namespace App\Http\Middleware;

use App\Models\User;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

class ClientMiddleware
{
    public function handle(Request $request, Closure $next): Response
    {
        if (!Auth::check()) {
            return redirect()->route('auth.login');
        }

        $user = Auth::user();
        if (!$user instanceof User) {
            abort(403, 'Client access only.');
        }

        if (!$user->isClient()) {
            abort(403, 'Client access only.');
        }

        return $next($request);
    }
}
