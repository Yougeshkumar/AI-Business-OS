/**
 * Shared API and event contracts.
 *
 * Sprint 0 ships only the common response envelope types. Module-specific
 * contracts (CRM, Finance, etc.) are added in later sprints alongside their
 * OpenAPI/AsyncAPI definitions.
 */

export interface ResponseMeta {
  request_id: string;
  trace_id: string;
  timestamp: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: string | null;
  trace_id: string;
  timestamp: string;
}

export interface HealthStatus {
  status: 'ok';
  service: string;
  version: string;
  environment: string;
}
