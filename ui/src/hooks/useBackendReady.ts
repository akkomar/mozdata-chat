import { useState, useEffect, useCallback, useRef } from "react";

const POLL_INTERVAL_MS = 1000;
const MAX_ATTEMPTS = 60; // 60 seconds total timeout

interface UseBackendReadyOptions {
  enabled: boolean;
}

interface UseBackendReadyResult {
  isReady: boolean;
  isLoading: boolean;
  error: string | null;
  attemptCount: number;
  retry: () => void;
}

export function useBackendReady({
  enabled,
}: UseBackendReadyOptions): UseBackendReadyResult {
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attemptCount, setAttemptCount] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const response = await fetch("/api/health");
      if (response.ok) {
        if (mountedRef.current) {
          setIsReady(true);
          setIsLoading(false);
          setError(null);
          stopPolling();
        }
        return true;
      }
    } catch {
      // Health check failed, continue polling
    }
    return false;
  }, [stopPolling]);

  const startPolling = useCallback(() => {
    setIsLoading(true);
    setError(null);
    setAttemptCount(0);
    setIsReady(false);

    // Check immediately
    checkHealth();

    let attempts = 1;
    intervalRef.current = setInterval(async () => {
      if (!mountedRef.current) {
        stopPolling();
        return;
      }

      attempts++;
      setAttemptCount(attempts);

      if (attempts > MAX_ATTEMPTS) {
        stopPolling();
        if (mountedRef.current) {
          setIsLoading(false);
          setError("Backend service is taking too long to respond. Please try again.");
        }
        return;
      }

      await checkHealth();
    }, POLL_INTERVAL_MS);
  }, [checkHealth, stopPolling]);

  const retry = useCallback(() => {
    stopPolling();
    startPolling();
  }, [stopPolling, startPolling]);

  useEffect(() => {
    mountedRef.current = true;

    if (enabled && !isReady) {
      startPolling();
    }

    return () => {
      mountedRef.current = false;
      stopPolling();
    };
  }, [enabled, isReady, startPolling, stopPolling]);

  return {
    isReady,
    isLoading,
    error,
    attemptCount,
    retry,
  };
}
