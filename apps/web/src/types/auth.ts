/** Authentication domain types shared across the web app. */

export interface AuthUser {
  id: string;
  organization_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  status: string;
}

export interface AuthOrganization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResult {
  tokens: TokenPair;
  user: AuthUser;
  organization: AuthOrganization;
}

export interface RegisterPayload {
  email: string;
  password: string;
  organization_name: string;
  first_name?: string;
  last_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
