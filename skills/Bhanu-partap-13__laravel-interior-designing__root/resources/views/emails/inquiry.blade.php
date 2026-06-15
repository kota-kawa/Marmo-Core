<!doctype html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <title>{{ __('app.emails.inquiry.title') }}</title>
</head>
<body>
    <h2>{{ __('app.emails.inquiry.heading') }}</h2>
    <p><strong>{{ __('app.emails.inquiry.project') }}:</strong> {{ $inquiry->project->title ?? __('app.projects.index.project_fallback') }}</p>
    @if($inquiry->visitor_name || $inquiry->visitor_email)
        <p><strong>{{ __('app.emails.inquiry.from') }}:</strong>
            @if($inquiry->visitor_name){{ $inquiry->visitor_name }}@endif
            @if($inquiry->visitor_email) ({{ $inquiry->visitor_email }})@endif
        </p>
    @endif
    <p><strong>{{ __('app.emails.inquiry.message') }}:</strong></p>
    <p>{{ $inquiry->message }}</p>
</body>
</html>
