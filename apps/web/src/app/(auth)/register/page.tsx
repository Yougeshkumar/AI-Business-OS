import Link from 'next/link';
import type { ReactNode } from 'react';

import { RegisterForm } from '@/components/auth/register-form';

export default function RegisterPage(): ReactNode {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-8">
      <div>
        <h1 className="text-2xl font-bold">Create your organization</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Set up a new workspace and admin account.
        </p>
      </div>
      <RegisterForm />
      <p className="text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link href="/login" className="font-medium underline">
          Sign in
        </Link>
      </p>
    </main>
  );
}
