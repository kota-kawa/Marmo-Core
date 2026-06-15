@extends('layouts.app')

@section('title', __('app.dashboard.projects.edit_title'))

@section('content')
<section class="page-hero">
    <div class="container narrow">
        <p class="eyebrow">{{ __('app.dashboard.projects.eyebrow') }}</p>
        <h1>{{ __('app.dashboard.projects.edit_heading') }}</h1>
        <p class="lead">{{ __('app.dashboard.projects.edit_lead') }}</p>
        <form class="form-card" method="post" action="{{ route('dashboard.projects.update', $project) }}" enctype="multipart/form-data">
            @csrf
            @method('put')
            @include('dashboard.projects._form')
            <button class="btn btn-primary" type="submit">{{ __('app.dashboard.projects.edit_submit') }}</button>
        </form>
    </div>
</section>
@endsection
