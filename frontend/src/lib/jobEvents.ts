import { useEffect, useRef } from 'react';
import { apiBaseUrl } from './api';

export interface JobEventPayload<TJob = unknown> {
  type: 'created' | 'updated';
  job_id: string;
  job: TJob;
}

export function useJobEvents<TJob = unknown>(onEvent: (payload: JobEventPayload<TJob>) => void) {
  const handlerRef = useRef(onEvent);

  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    const eventsUrl = `${apiBaseUrl}/jobs/events`;
    let source: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let retryDelay = 1000; // Start at 1s, back off on errors

    const connect = () => {
      source = new EventSource(eventsUrl);

      const handler = (event: MessageEvent) => {
        try {
          const payload = JSON.parse(event.data) as JobEventPayload<TJob>;
          handlerRef.current(payload);
        } catch (error) {
          console.error('Failed to parse job event payload', error);
        }
      };

      source.addEventListener('created', handler);
      source.addEventListener('updated', handler);
      source.addEventListener('heartbeat', () => {});
      source.addEventListener('ready', () => { retryDelay = 1000; }); // Reset on success

      source.onerror = () => {
        source?.close();
        source = null;
        // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
        retryTimeout = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 30000);
      };
    };

    connect();

    return () => {
      if (retryTimeout) clearTimeout(retryTimeout);
      source?.close();
    };
  }, []);
}
