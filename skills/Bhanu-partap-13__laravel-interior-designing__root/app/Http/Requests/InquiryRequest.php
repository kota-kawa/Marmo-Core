<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class InquiryRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        $rules = [
            'project_id' => ['required', 'exists:projects,id'],
            'message' => ['required', 'string', 'min:3', 'max:2000'],
            'visitor_name' => ['nullable', 'string', 'max:120'],
            'visitor_email' => ['nullable', 'email', 'max:160'],
        ];

        return $rules;
    }
}
