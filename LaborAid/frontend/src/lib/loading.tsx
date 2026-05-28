import { useState, useCallback, useContext, createContext, type ReactNode } from 'react';

/** Global loading indicator context for showing a spinner in the top bar during API calls */

interface LoadingContextValue {
  isLoading: boolean;
  startLoading: () => void;
  stopLoading: () => void;
}

const LoadingContext = createContext<LoadingContextValue>({
  isLoading: false,
  startLoading: () => {},
  stopLoading: () => {},
});

export function useGlobalLoading(): LoadingContextValue {
  return useContext(LoadingContext);
}

export function GlobalLoadingProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState(0);

  const startLoading = useCallback(() => setCount((c) => c + 1), []);
  const stopLoading = useCallback(() => setCount((c) => Math.max(0, c - 1)), []);

  return (
    <LoadingContext.Provider value={{ isLoading: count > 0, startLoading, stopLoading }}>
      {children}
    </LoadingContext.Provider>
  );
}
