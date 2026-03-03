"use client";

import { useEffect, useState, useCallback } from "react";
import { useAppContext } from "@/context/AppContext";

export function useSSE(onStateChange: () => void) {
  const { config } = useAppContext();
  const [status, setStatus] = useState<"connected" | "disconnected" | "error">("disconnected");

  const connect = useCallback(() => {
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    const url = `${config.apiBaseUrl}/api/events`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      setStatus("connected");
      console.log("SSE connected");
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "state_change") {
          onStateChange();
        }
      } catch (e) {
        console.error("Failed to parse SSE event", e);
      }
    };

    eventSource.onerror = (e) => {
      setStatus("error");
      console.error("SSE error", e);
      eventSource.close();
      // Retry connection after 5 seconds
      retryTimer = setTimeout(() => {
        connect();
      }, 5000);
    };

    return {
      close: () => {
        if (retryTimer) {
          clearTimeout(retryTimer);
        }
        eventSource.close();
      },
    };
  }, [config.apiBaseUrl, onStateChange]);

  useEffect(() => {
    const es = connect();
    return () => {
      es.close();
    };
  }, [connect]);

  return { status };
}
