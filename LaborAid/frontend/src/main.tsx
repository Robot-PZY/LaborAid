import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { ToastProvider } from './lib/toast';
import { GlobalLoadingProvider } from './lib/loading';
import NetworkStatus from './lib/network-status';
import { KeyboardShortcutsProvider } from './lib/keyboard';
import { SkipToContent } from './lib/accessibility';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// ── Global Error Boundary ──────────────────────────────────────────────

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class GlobalErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Global error boundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-background p-8" role="alert" aria-live="assertive">
          <div className="max-w-md text-center space-y-4">
            <div className="flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
                <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
            <h1 className="text-xl font-bold text-foreground">页面出了问题</h1>
            <p className="text-sm text-muted-foreground">
              应用程序发生了意外错误。请尝试刷新页面或返回首页。
            </p>
            {this.state.error && (
              <pre className="mt-2 max-h-32 overflow-auto rounded-lg bg-muted p-3 text-left text-xs text-muted-foreground">
                {this.state.error.message}
              </pre>
            )}
            <div className="flex gap-3 justify-center pt-2">
              <button
                onClick={() => window.location.reload()}
                className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
              >
                刷新页面
              </button>
              <button
                onClick={this.handleReset}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// ── Root render ────────────────────────────────────────────────────────

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GlobalErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <GlobalLoadingProvider>
            <KeyboardShortcutsProvider>
              <ToastProvider>
                <SkipToContent />
                <NetworkStatus />
                <App />
              </ToastProvider>
            </KeyboardShortcutsProvider>
          </GlobalLoadingProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </GlobalErrorBoundary>
  </React.StrictMode>,
);
