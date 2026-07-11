import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { QueryProvider } from '@/components/query-provider';

import './globals.css';

export const metadata: Metadata = {
  title: 'AI Business Operating System',
  description: 'Unified AI-native business operations platform',
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}): ReactNode {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
