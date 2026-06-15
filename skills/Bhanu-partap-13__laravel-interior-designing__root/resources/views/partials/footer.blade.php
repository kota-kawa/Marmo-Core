<footer class="site-footer">
    <div class="container footer-grid">
        <div class="footer-brand">
            <img class="footer-logo" src="{{ asset('logoo.svg') }}" alt="{{ __('app.footer.brand_title') }}">
            <h4>{{ __('app.footer.brand_title') }}</h4>
            <p>{{ __('app.footer.brand_text') }}</p>
        </div>
        <div class="footer-col">
            <p class="footer-title">{{ __('app.footer.explore') }}</p>
            <a href="{{ route('designers.index') }}">{{ __('app.nav.designers') }}</a>
            <a href="{{ route('projects.index') }}">{{ __('app.nav.projects') }}</a>
            <a href="{{ route('categories.show', 'living-room') }}">{{ __('app.nav.categories') }}</a>
        </div>
        <div class="footer-col">
            <p class="footer-title">{{ __('app.footer.account') }}</p>
            <a href="{{ route('auth.login') }}">{{ __('app.nav.login') }}</a>
            <a href="{{ route('auth.register') }}">{{ __('app.nav.register') }}</a>
        </div>
        <div class="footer-col">
            <p class="footer-title">{{ __('app.footer.contact') }}</p>
            <p>parveshyadav136@gmail.com</p>
            <p>9040011331</p>
            <p>Bhubaneshwar, Odisha</p>
        </div>
    </div>
    <div class="container footer-bottom">
        <p>{{ __('app.footer.rights') }}</p>
        <p>{{ __('app.footer.built') }}</p>
    </div>
</footer>
