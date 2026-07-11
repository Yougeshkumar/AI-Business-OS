import type { ReactNode } from 'react';

import { HealthCard } from '@/components/health-card';
import { Button } from '@/components/ui/button';

export default function HomePage(): ReactNode {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold">AI Business Operating System</h1>
        <p className="mt-2 text-muted-foreground">
          Sprint 0 — Foundation is running.
        </p>
      </div>
      <HealthCard />
      <Button variant="outline">Get started</Button>
    </main>
  );
}
