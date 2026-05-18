import { useEffect, useRef } from 'react';
import { apiBaseUrl } from './api';

export interface JobEventPayload<TJob = unknown> {
  type: 'created' | 'updated';
  job_id: string;
  job: TJob;
}

interface UseJobEventsOptions {
  onConnectionChange?: (connected: boolean) => void;
}

export function useJobEvents<TJob = unknown>(
  onEvent: (payload: JobEventPayload<TJob>) => void,
  options?: UseJobEventsOptions,
) {
  const handlerRef = useRef(onEvent);
  const optionsRef = useRef(options);

  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  useEffect(() => {
    const eventsUrl = `${apiBaseUrl}/jobs/events`;
    let source: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let retryDelay = 1000;

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
      source.addEventListener('ready', () => {
        retryDelay = 1000;
        optionsRef.current?.onConnectionChange?.(true);
      });

      source.onerror = () => {
        optionsRef.current?.onConnectionChange?.(false);
        source?.close();
        source = null;
        retryTimeout = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 30000);
      };
    };

    connect();

    return () => {
      optionsRef.current?.onConnectionChange?.(false);
      if (retryTimeout) clearTimeout(retryTimeout);
      source?.close();
    };
  }, []);
}
