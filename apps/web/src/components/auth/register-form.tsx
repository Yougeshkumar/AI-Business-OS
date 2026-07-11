'use client';

import { useForm } from 'react-hook-form';
import type { ReactNode } from 'react';

import { Button } from '@/components/ui/button';
import { useRegister } from '@/hooks/use-auth';
import type { RegisterPayload } from '@/types/auth';

/** Controlled registration form backed by React Hook Form + TanStack Query. */
export function RegisterForm(): ReactNode {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterPayload>();
  const registerMutation = useRegister();

  const onSubmit = (values: RegisterPayload): void => {
    registerMutation.mutate(values);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="organization_name" className="text-sm font-medium">
          Organization name
        </label>
        <input
          id="organization_name"
          type="text"
          className="rounded-md border border-border px-3 py-2"
          {...register('organization_name', {
            required: 'Organization name is required',
            minLength: { value: 2, message: 'At least 2 characters' },
          })}
        />
        {errors.organization_name && (
          <span className="text-sm text-red-500">
            {errors.organization_name.message}
          </span>
        )}
      </div>

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
          autoComplete="new-password"
          className="rounded-md border border-border px-3 py-2"
          {...register('password', {
            required: 'Password is required',
            minLength: { value: 12, message: 'At least 12 characters' },
          })}
        />
        {errors.password && (
          <span className="text-sm text-red-500">
            {errors.password.message}
          </span>
        )}
      </div>

      {registerMutation.isError && (
        <p className="text-sm text-red-500">
          Registration failed. Please try again.
        </p>
      )}

      <Button type="submit" disabled={registerMutation.isPending}>
        {registerMutation.isPending ? 'Creating…' : 'Create account'}
      </Button>
    </form>
  );
}
