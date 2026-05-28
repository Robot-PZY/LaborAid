import { useEffect, useRef, useCallback } from 'react';

/**
 * Accessibility utilities:
 * - Screen reader announcements
 * - Focus management for modals
 * - Skip-to-content link
 */

/** Announce a message to screen readers using a live region */
export function announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite') {
  const el = document.createElement('div');
  el.setAttribute('role', 'status');
  el.setAttribute('aria-live', priority);
  el.setAttribute('aria-atomic', 'true');
  el.className = 'sr-only';
  el.textContent = message;
  document.body.appendChild(el);
  // Remove after the announcement is read
  setTimeout(() => {
    document.body.removeChild(el);
  }, 1000);
}

/** Hook for managing focus in modal dialogs */
export function useFocusTrap(isOpen: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      // Save the previously focused element
      previousFocusRef.current = document.activeElement as HTMLElement;

      // Focus the first focusable element inside the container
      requestAnimationFrame(() => {
        if (!containerRef.current) return;
        const focusable = containerRef.current.querySelector<HTMLElement>(
          'input, textarea, select, button, [tabindex]:not([tabindex="-1"])'
        );
        focusable?.focus();
      });
    } else {
      // Restore focus to the previously focused element
      previousFocusRef.current?.focus();
      previousFocusRef.current = null;
    }
  }, [isOpen]);

  // Handle Tab key to trap focus within the modal
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !containerRef.current) return;

    const focusableElements = containerRef.current.querySelectorAll<HTMLElement>(
      'input, textarea, select, button, [tabindex]:not([tabindex="-1"])'
    );
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable?.focus();
      }
    } else {
      if (document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable?.focus();
      }
    }
  }, []);

  return { containerRef, handleKeyDown };
}

/** SkipToContent link component for keyboard users */
export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[300] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-ring"
    >
      跳转到主要内容
    </a>
  );
}
