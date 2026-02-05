'use client';

import React, { ReactNode } from 'react';
import { NuqsAdapter } from 'nuqs/adapters/next/app';
import { ErrorBoundary } from './ErrorBoundary';

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Client-side providers wrapper component.
 * Wraps the app with ErrorBoundary and other client-side providers.
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      <NuqsAdapter>{children}</NuqsAdapter>
    </ErrorBoundary>
  );
}

export default Providers;
