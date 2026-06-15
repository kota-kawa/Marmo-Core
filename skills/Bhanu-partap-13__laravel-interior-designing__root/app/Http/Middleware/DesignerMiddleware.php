<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use App\Models\User;
use Symfony\Component\HttpFoundation\Response;

class DesignerMiddleware
{
    public function handle(Request $request, Closure $next): Response
    {
        if (!Auth::check()) {
            return redirect()->route('auth.login');
        }

        $user = Auth::user();
        if (!$user instanceof User) {
            abort(403, 'Designer access only.');
        }

        if (!$user->isDesigner()) {
            abort(403, 'Designer access only.');
        }

        return $next($request);
    }
}
