import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-8 max-w-md text-center">
            <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900 mb-2">Something went wrong</h2>
            <p className="text-sm text-slate-500 mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}


// Route-aware wrapper that resets error boundary on navigation
import { useLocation } from 'react-router-dom';

export function RouteErrorBoundary({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  return (
    <ErrorBoundary key={location.pathname}>
      {children}
    </ErrorBoundary>
  );
}
