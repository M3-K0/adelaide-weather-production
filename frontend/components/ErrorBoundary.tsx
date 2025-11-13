/**
 * ErrorBoundary Component
 * 
 * React error boundary that catches JavaScript errors anywhere in the child
 * component tree and displays a fallback UI with helpful error information.
 */

'use client';

import React, { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCw, Bug, ExternalLink } from 'lucide-react';

interface ErrorBoundaryProps {
  /** Child components */
  children: ReactNode;
  /** Custom fallback component */
  fallback?: ReactNode;
  /** Optional error callback */
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  /** Show technical details */
  showDetails?: boolean;
  /** Component name for debugging */
  componentName?: string;
  /** Custom className */
  className?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // In production, you might want to send errors to an error reporting service
    // Example: reportError(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      // Show custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className={`
          bg-red-950/20 border border-red-700 rounded-lg p-6 text-center
          ${this.props.className || ''}
        `}>
          {/* Error Icon */}
          <div className="flex justify-center mb-4">
            <AlertCircle size={32} className="text-red-400" />
          </div>

          {/* Error Title */}
          <h2 className="text-lg font-semibold text-red-300 mb-2">
            Something went wrong
          </h2>

          {/* Error Description */}
          <p className="text-red-200 text-sm mb-4">
            {this.props.componentName 
              ? `An error occurred in the ${this.props.componentName} component.`
              : 'An unexpected error occurred while rendering this component.'
            }
          </p>

          {/* Error Details (Development only) */}
          {this.props.showDetails && this.state.error && (
            <details className="mb-4 text-left">
              <summary className="text-xs text-red-400 cursor-pointer hover:text-red-300 mb-2">
                <Bug size={12} className="inline mr-1" />
                Technical Details
              </summary>
              <div className="bg-red-950/30 border border-red-800 rounded p-3 text-xs font-mono">
                <div className="mb-2">
                  <strong className="text-red-300">Error:</strong>
                  <div className="text-red-200 mt-1">{this.state.error.message}</div>
                </div>
                {this.state.error.stack && (
                  <div className="mb-2">
                    <strong className="text-red-300">Stack:</strong>
                    <pre className="text-red-200 mt-1 whitespace-pre-wrap text-xs overflow-x-auto">
                      {this.state.error.stack}
                    </pre>
                  </div>
                )}
                {this.state.errorInfo?.componentStack && (
                  <div>
                    <strong className="text-red-300">Component Stack:</strong>
                    <pre className="text-red-200 mt-1 whitespace-pre-wrap text-xs overflow-x-auto">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </div>
            </details>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={this.handleRetry}
              className="
                inline-flex items-center gap-2 px-4 py-2 text-sm
                bg-red-600 hover:bg-red-700 text-white
                border border-red-500 hover:border-red-400 rounded-lg
                transition-colors focus:outline-none focus:ring-2 focus:ring-red-500
              "
            >
              <RefreshCw size={14} />
              Try Again
            </button>

            <button
              onClick={() => window.location.reload()}
              className="
                inline-flex items-center gap-2 px-4 py-2 text-sm
                bg-transparent hover:bg-red-900/30 text-red-300 hover:text-red-200
                border border-red-600 hover:border-red-500 rounded-lg
                transition-colors focus:outline-none focus:ring-2 focus:ring-red-500
              "
            >
              <ExternalLink size={14} />
              Reload Page
            </button>
          </div>

          {/* Support Information */}
          <div className="mt-6 pt-4 border-t border-red-800">
            <p className="text-xs text-red-400">
              If this error persists, please contact support with the error details above.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component to wrap components with error boundary
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const WrappedComponent: React.FC<P> = (props) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
}

export default ErrorBoundary;