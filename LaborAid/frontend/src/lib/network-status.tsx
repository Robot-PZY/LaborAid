import { useState, useEffect, useCallback } from 'react';
import { WifiOff, Wifi, RefreshCw } from 'lucide-react';

/** Network status banner - shows when the browser goes offline, with retry and reconnection detection */

export default function NetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [justReconnected, setJustReconnected] = useState(false);
  const [wasOffline, setWasOffline] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      if (wasOffline) {
        setJustReconnected(true);
        // Auto-dismiss the reconnection banner after 3 seconds
        setTimeout(() => setJustReconnected(false), 3000);
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
      setWasOffline(true);
      setJustReconnected(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [wasOffline]);

  const handleRetry = useCallback(() => {
    // Attempt to fetch a lightweight endpoint to check connectivity
    // If the browser detects connectivity, the 'online' event will fire
    if (navigator.onLine) {
      setIsOnline(true);
      setJustReconnected(true);
      setTimeout(() => setJustReconnected(false), 3000);
    } else {
      // Try to trigger a network check by creating a temporary image request
      const img = new Image();
      img.onload = () => {
        setIsOnline(true);
        setJustReconnected(true);
        setTimeout(() => setJustReconnected(false), 3000);
      };
      img.onerror = () => {
        // Still offline - the browser will fire the online event when reconnected
      };
      img.src = `${window.location.origin}/favicon.png?_=${Date.now()}`;
    }
  }, []);

  // Reconnection success banner
  if (isOnline && justReconnected) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="fixed top-0 left-0 right-0 z-[200] flex items-center justify-center gap-2 bg-green-600 px-4 py-2 text-sm font-medium text-white animate-in slide-in-from-top-full duration-300"
      >
        <Wifi className="h-4 w-4 shrink-0" />
        网络已恢复连接
      </div>
    );
  }

  // Offline banner
  if (!isOnline) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        className="fixed top-0 left-0 right-0 z-[200] flex items-center justify-center gap-3 bg-red-600 px-4 py-2 text-sm font-medium text-white animate-in slide-in-from-top-full duration-300"
      >
        <WifiOff className="h-4 w-4 shrink-0" />
        <span>网络已断开，部分功能可能不可用</span>
        <button
          onClick={handleRetry}
          className="ml-2 inline-flex items-center gap-1 rounded-md bg-white/20 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
          aria-label="重试连接"
        >
          <RefreshCw className="h-3 w-3" />
          重试
        </button>
      </div>
    );
  }

  // Reset wasOffline when online and no banners showing
  if (wasOffline && !justReconnected) {
    setWasOffline(false);
  }

  return null;
}
