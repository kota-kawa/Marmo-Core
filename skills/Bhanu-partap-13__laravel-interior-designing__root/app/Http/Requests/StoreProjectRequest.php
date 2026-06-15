<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

class StoreProjectRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'title' => ['required', 'string', 'max:160'],
            'category_id' => ['required', 'exists:categories,id'],
            'subcategory_id' => ['nullable', 'exists:subcategories,id'],
            'description' => ['nullable', 'string', 'max:2000'],
            'company_name' => ['nullable', 'string', 'max:160'],
            'budget_range' => ['nullable', 'string', 'max:60'],
            'duration_days' => ['nullable', 'integer', 'min:1'],
            'style_tags' => ['nullable', 'string', 'max:250'],
            'materials' => ['nullable', 'string', 'in:Wood,Tile,Marble,Laminate,Glass,Concrete,Composite,Other'],
            'scope' => ['nullable', 'string', 'max:1000'],
            'payment_status' => ['nullable', 'string', 'in:paid,free'],
            'amount_paid' => ['nullable', 'numeric', 'min:0'],
            'before_image' => ['nullable', 'image', 'max:4096'],
            'after_image' => ['nullable', 'image', 'max:4096'],
            'video' => ['nullable', 'file', 'mimes:mp4,webm,mov,avi,mkv', 'max:5120'],
            'invoice_proof' => ['nullable', 'file', 'mimes:pdf,jpg,jpeg,png,webp', 'max:4096'],
            'media' => ['nullable', 'array'],
            'media.*' => ['file', 'mimes:jpg,jpeg,png,webp,mp4,webm,mov', 'max:8192'],
            'is_published' => ['nullable', 'boolean'],
        ];
    }
}
