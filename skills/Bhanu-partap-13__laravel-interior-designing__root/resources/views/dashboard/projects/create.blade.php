@extends('layouts.app')

@section('title', __('app.dashboard.projects.create_title'))

@section('content')
<section class="page-hero">
    <div class="container narrow">
        <p class="eyebrow">{{ __('app.dashboard.projects.eyebrow') }}</p>
        <h1>{{ __('app.dashboard.projects.create_heading') }}</h1>
        <p class="lead">{{ __('app.dashboard.projects.create_lead') }}</p>
        <form class="form-card" method="post" action="{{ route('dashboard.projects.store') }}" enctype="multipart/form-data">
            @csrf
            @include('dashboard.projects._form')
            <button class="btn btn-primary" type="submit">{{ __('app.dashboard.projects.create_submit') }}</button>
        </form>
    </div>
</section>
@endsection
