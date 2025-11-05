'use client';

import { ClientMetricsProvider } from '@/lib/ClientMetricsProvider';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ClientMetricsProvider>
      {children}
    </ClientMetricsProvider>
  );
}