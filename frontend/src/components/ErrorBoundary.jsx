import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { AlertTriangle } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Filter out ResizeObserver errors
    if (
      error.message &&
      (error.message.includes('ResizeObserver loop') ||
       error.message.includes('ResizeObserver loop limit exceeded') ||
       error.message.includes('ResizeObserver loop completed with undelivered notifications'))
    ) {
      console.log('ResizeObserver error caught and suppressed');
      this.setState({ hasError: false, error: null, errorInfo: null });
      return;
    }

    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <Card className="max-w-md w-full border-red-200">
            <CardHeader className="bg-red-50">
              <CardTitle className="flex items-center text-red-700">
                <AlertTriangle className="w-5 h-5 mr-2" />
                Something went wrong
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <p className="text-sm text-gray-600 mb-4">
                We encountered an unexpected error. Please try refreshing the page.
              </p>
              {this.state.error && (
                <details className="mb-4">
                  <summary className="text-sm font-medium cursor-pointer text-gray-700">
                    Error details
                  </summary>
                  <pre className="mt-2 text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                    {this.state.error.toString()}
                  </pre>
                </details>
              )}
              <Button onClick={this.handleReset} className="w-full">
                Refresh Page
              </Button>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
