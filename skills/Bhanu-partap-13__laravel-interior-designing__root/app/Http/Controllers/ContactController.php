<?php

namespace App\Http\Controllers;

use App\Http\Requests\ContactRequest;
use App\Mail\ContactMail;
use App\Models\ContactMessage;
use Illuminate\Support\Facades\Mail;

class ContactController extends Controller
{
    public function store(ContactRequest $request)
    {
        $contactMessage = ContactMessage::create($request->validated());

        $recipient = config('mail.from.address');

        if ($recipient) {
            Mail::to($recipient)->send(new ContactMail($contactMessage));
        }

        return back()->with('status', __('app.contact.form.success'));
    }
}
