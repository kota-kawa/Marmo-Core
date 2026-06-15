/**
 * ErrorBoundary - Industrial Brutalist
 */

import { Component, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center p-8" style={{ background: '#09090B' }}>
                    <div className="max-w-md w-full">
                        <div className="card">
                            <div className="px-4 py-3 border-b border-zinc-700 flex items-center gap-3">
                                <AlertCircle className="w-4 h-4 text-accent" />
                                <span className="label">SYSTEM ERROR</span>
                            </div>
                            <div className="card-content text-center py-8">
                                <h2 className="font-display text-xl font-bold text-zinc-50 mb-3">
                                    Something broke
                                </h2>
                                <p className="text-zinc-500 text-sm mb-6">
                                    {this.state.error?.message || 'An unexpected error occurred'}
                                </p>
                                <div className="flex gap-3 justify-center">
                                    <button
                                        onClick={() => this.setState({ hasError: false })}
                                        className="btn btn-primary"
                                    >
                                        <RefreshCw className="w-4 h-4" />
                                        Retry
                                    </button>
                                    <button
                                        onClick={() => window.location.reload()}
                                        className="btn btn-secondary"
                                    >
                                        Reload Page
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
