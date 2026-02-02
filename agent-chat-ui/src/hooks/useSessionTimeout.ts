import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";
import { TIMING } from "@/lib/constants";

interface UseSessionTimeoutOptions {
  onExpire: () => void;
  timeout?: number;
}

export function useSessionTimeout({
  onExpire,
  timeout = TIMING.SESSION_TIMEOUT,
}: UseSessionTimeoutOptions) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onExpireRef = useRef(onExpire);

  // Keep callback ref up to date without causing timer resets
  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const resetTimer = useCallback(() => {
    clearTimer();
    timerRef.current = setTimeout(() => {
      toast.info("세션이 만료되어 새 대화가 시작됩니다", {
        duration: 5000,
      });
      onExpireRef.current();
    }, timeout);
  }, [clearTimer, timeout]);

  // Start timer on mount, clear on unmount
  useEffect(() => {
    resetTimer();
    return clearTimer;
  }, [resetTimer, clearTimer]);

  return { resetTimer, clearTimer };
}
