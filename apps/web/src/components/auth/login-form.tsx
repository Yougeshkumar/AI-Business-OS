'use client';

import { useForm } from 'react-hook-form';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { useLogin } from '@/hooks/use-auth';
import type { LoginPayload } from '@/types/auth';

/** Controlled login form backed by React Hook Form + TanStack Query. */
export function LoginForm(): ReactNode {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginPayload>();
  const login = useLogin();

  const onSubmit = (values: LoginPayload): void => {
    login.mutate(values);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          className="rounded-md border border-border px-3 py-2"
          {...register('email', { required: 'Email is required' })}
        />
        {errors.email && (
          <span className="text-sm text-red-500">{errors.email.message}</span>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          className="rounded-md border border-border px-3 py-2"
          {...register('password', { required: 'Password is required' })}
        />
        {errors.password && (
          <span className="text-sm text-red-500">
            {errors.password.message}
          </span>
        )}
      </div>

      {login.isError && (
        <p className="text-sm text-red-500">
          Login failed. Check your credentials and try again.
        </p>
      )}

      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? 'Signing in…' : 'Sign in'}
      </Button>
    </form>
  );
}
