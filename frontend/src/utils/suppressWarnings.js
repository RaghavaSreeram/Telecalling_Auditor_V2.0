// Suppress and fix ResizeObserver issues
// Implements proper debouncing and requestAnimationFrame to prevent loops

const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

const suppressResizeObserverWarnings = () => {
  // Patch ResizeObserver to use requestAnimationFrame
  if (typeof ResizeObserver !== 'undefined') {
    const OriginalResizeObserver = window.ResizeObserver;
    
    window.ResizeObserver = class PatchedResizeObserver extends OriginalResizeObserver {
      constructor(callback) {
        const wrappedCallback = debounce((entries, observer) => {
          window.requestAnimationFrame(() => {
            try {
              callback(entries, observer);
            } catch (e) {
              // Suppress ResizeObserver errors
              if (!e.message.includes('ResizeObserver')) {
                throw e;
              }
            }
          });
        }, 16); // ~60fps
        
        super(wrappedCallback);
      }
    };
  }

  // Suppress console errors
  const originalConsoleError = console.error;
  console.error = (...args) => {
    const firstArg = args[0];
    if (typeof firstArg === 'string') {
      if (
        firstArg.includes('ResizeObserver loop') ||
        firstArg.includes('ResizeObserver loop limit exceeded') ||
        firstArg.includes('ResizeObserver loop completed with undelivered notifications')
      ) {
        return; // Suppress these specific errors
      }
    }
    originalConsoleError(...args);
  };

  // Suppress error events
  window.addEventListener('error', (e) => {
    if (
      e.message &&
      (e.message.includes('ResizeObserver loop') ||
       e.message === 'ResizeObserver loop limit exceeded' ||
       e.message === 'ResizeObserver loop completed with undelivered notifications')
    ) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return false;
    }
  }, true);

  // Also handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (e) => {
    if (
      e.reason &&
      e.reason.message &&
      e.reason.message.includes('ResizeObserver')
    ) {
      e.preventDefault();
      return false;
    }
  });
};

export default suppressResizeObserverWarnings;
