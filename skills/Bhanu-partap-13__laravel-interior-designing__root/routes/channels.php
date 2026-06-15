<?php

use Illuminate\Support\Facades\Broadcast;

Broadcast::channel('designer.{designerId}', function ($user, $designerId) {
    $designer = $user->designer;

    return $designer && (int) $designer->id === (int) $designerId;
});
