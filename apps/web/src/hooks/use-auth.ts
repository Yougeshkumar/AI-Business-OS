'use client';

import { useMutation, type UseMutationResult } from '@tanstack/react-query';

import { loginRequest, registerRequest } from '@/lib/auth-api';
import { useAuthStore } from '@/stores/auth-store';
import type {
  AuthResult,
  LoginPayload,
  RegisterPayload,
} from '@/types/auth';

/** Mutation hook for registering a new organization + admin user. */
export function useRegister(): UseMutationResult<
  AuthResult,
  Error,
  RegisterPayload
> {
  const setAuth = useAuthStore((state) => state.setAuth);
  return useMutation({
    mutationFn: registerRequest,
    onSuccess: (result: AuthResult): void => {
      setAuth(result);
    },
  });
}

/** Mutation hook for logging in an existing user. */
export function useLogin(): UseMutationResult<AuthResult, Error, LoginPayload> {
  const setAuth = useAuthStore((state) => state.setAuth);
  return useMutation({
    mutationFn: loginRequest,
    onSuccess: (result: AuthResult): void => {
      setAuth(result);
    },
  });
}
