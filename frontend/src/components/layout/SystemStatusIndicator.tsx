/**
 * SystemStatusIndicator: Displays real-time high-level health and readiness status.
 * Gracefully handles errors without crashing the application shell.
 */

import React, { useEffect, useState } from 'react';
import { systemService } from '../../services/system';
import { useAIPreferences } from '../../hooks/useAIPreferences';

export type SystemStatus = 'checking' | 'ready' | 'degraded' | 'offline';

export const SystemStatusIndicator: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus>('checking');
  const { t } = useAIPreferences();

  useEffect(() => {
    let isMounted = true;

    const checkStatus = async () => {
      try {
        const [health, readiness] = await Promise.allSettled([
          systemService.getHealth(),
          systemService.getReadiness(),
        ]);

        if (!isMounted) return;

        const isHealthOk =
          health.status === 'fulfilled' && health.value?.status === 'healthy';
        const isReadyOk =
          readiness.status === 'fulfilled' && readiness.value?.status === 'ready';

        if (isHealthOk && isReadyOk) {
          setStatus('ready');
        } else if (isHealthOk || isReadyOk) {
          setStatus('degraded');
        } else {
          setStatus('offline');
        }
      } catch {
        if (!isMounted) return;
        setStatus('offline');
      }
    };

    checkStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  const getStatusText = (): string => {
    switch (status) {
      case 'ready':
        return t('status.ready');
      case 'degraded':
        return t('status.degraded');
      case 'offline':
        return t('status.offline');
      case 'checking':
      default:
        return t('status.checking');
    }
  };

  const statusLabel = getStatusText();

  return (
    <div
      className="system-status-badge"
      title={`${t('status.systemHealth')}: ${statusLabel}`}
      data-testid="system-status-badge"
    >
      <span className={`status-dot ${status}`} data-testid={`status-dot-${status}`} />
      <span>{statusLabel}</span>
    </div>
  );
};
