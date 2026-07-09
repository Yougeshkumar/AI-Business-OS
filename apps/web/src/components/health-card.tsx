'use client';

import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';

import { fetchHealth, type HealthStatus } from '@/lib/health';
import { cn } from '@/lib/utils';

/** Displays the live API health status, polling every 15 seconds. */
export function HealthCard(): ReactNode {
  const { data, isLoading, isError } = useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 15_000,
  });

  const dotClass = cn(
    'h-2.5 w-2.5 rounded-full',
    isError ? 'bg-red-500' : data ? 'bg-green-500' : 'bg-yellow-500',
  );

  return (
    <div className="w-full rounded-lg border border-border p-6">
      <div className="flex items-center gap-2">
        <span className={dotClass} aria-hidden />
        <span className="font-medium">API status</span>
      </div>
      <div className="mt-3 text-sm text-muted-foreground">
        {isLoading && <p>Checking…</p>}
        {isError && <p>API unreachable.</p>}
        {data && (
          <dl className="grid grid-cols-2 gap-1">
            <dt>Service</dt>
            <dd className="text-foreground">{data.service}</dd>
            <dt>Version</dt>
            <dd className="text-foreground">{data.version}</dd>
            <dt>Environment</dt>
            <dd className="text-foreground">{data.environment}</dd>
          </dl>
        )}
      </div>
    </div>
  );
}
