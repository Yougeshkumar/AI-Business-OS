import Link from 'next/link';
import type { ReactNode } from 'react';

import { LoginForm } from '@/components/auth/login-form';

export default function LoginPage(): ReactNode {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-8">
      <div>
        <h1 className="text-2xl font-bold">Sign in</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Welcome back to the AI Business Operating System.
        </p>
      </div>
      <LoginForm />
      <p className="text-sm text-muted-foreground">
        No account?{' '}
        <Link href="/register" className="font-medium underline">
          Create one
        </Link>
      </p>
    </main>
  );
}
