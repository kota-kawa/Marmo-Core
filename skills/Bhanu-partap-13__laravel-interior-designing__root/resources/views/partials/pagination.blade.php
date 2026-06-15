@if ($paginator->hasPages())
    <nav class="pagination" role="navigation">
        <div class="page-group">
            @if ($paginator->onFirstPage())
                <span class="page disabled">{{ __('app.pagination.prev') }}</span>
            @else
                <a class="page" href="{{ $paginator->previousPageUrl() }}" rel="prev">{{ __('app.pagination.prev') }}</a>
            @endif

            @foreach ($elements as $element)
                @if (is_string($element))
                    <span class="page disabled">{{ $element }}</span>
                @endif

                @if (is_array($element))
                    @foreach ($element as $page => $url)
                        @if ($page == $paginator->currentPage())
                            <span class="page active">{{ $page }}</span>
                        @else
                            <a class="page" href="{{ $url }}">{{ $page }}</a>
                        @endif
                    @endforeach
                @endif
            @endforeach

            @if ($paginator->hasMorePages())
                <a class="page" href="{{ $paginator->nextPageUrl() }}" rel="next">{{ __('app.pagination.next') }}</a>
            @else
                <span class="page disabled">{{ __('app.pagination.next') }}</span>
            @endif
        </div>
    </nav>
@endif
