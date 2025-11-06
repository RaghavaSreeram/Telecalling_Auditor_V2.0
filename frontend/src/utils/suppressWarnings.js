// Suppress benign ResizeObserver warnings
// These are non-critical browser warnings that don't affect functionality
const suppressResizeObserverWarnings = () => {
  const resizeObserverLoopErrRe = /^[^(ResizeObserver loop limit exceeded)]/;
  const resizeObserverLoopErrRe2 = /^[^(ResizeObserver loop completed with undelivered notifications)]/;
  
  const originalConsoleError = console.error;
  console.error = (...args) => {
    const firstArg = args[0];
    if (typeof firstArg === 'string') {
      if (
        firstArg.includes('ResizeObserver') ||
        !resizeObserverLoopErrRe.test(firstArg) ||
        !resizeObserverLoopErrRe2.test(firstArg)
      ) {
        return;
      }
    }
    originalConsoleError(...args);
  };

  // Also suppress the error event
  window.addEventListener('error', (e) => {
    if (
      e.message === 'ResizeObserver loop limit exceeded' ||
      e.message === 'ResizeObserver loop completed with undelivered notifications'
    ) {
      e.stopImmediatePropagation();
    }
  });
};

export default suppressResizeObserverWarnings;
