import type { components } from "./generated";

export type CapabilityResponse =
  components["schemas"]["CapabilityResponse"];
export type ScopeResponse = components["schemas"]["ScopeResponse"];
export type SessionResponse = components["schemas"]["SessionView"];

type ErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
    retryable?: boolean;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;

  constructor(status: number, code: string, message: string, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...init?.headers
    }
  });
  if (!response.ok) {
    let body: ErrorEnvelope = {};
    try {
      body = (await response.json()) as ErrorEnvelope;
    } catch {
      // The status remains useful if an upstream proxy returned a non-JSON page.
    }
    throw new ApiError(
      response.status,
      body.error?.code ?? "api_error",
      body.error?.message ?? "服务暂时不可用",
      body.error?.retryable ?? response.status >= 500
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getCapabilities(): Promise<CapabilityResponse> {
  return request<CapabilityResponse>("/capabilities");
}

export function getScopes(): Promise<ScopeResponse> {
  return request<ScopeResponse>("/api/v1/me/scopes");
}

export function loginSynthetic(): Promise<SessionResponse> {
  return request<SessionResponse>("/api/v1/auth/synthetic/session", {
    method: "POST"
  });
}

export function logout(): Promise<void> {
  return request<void>("/api/v1/auth/logout", { method: "POST" });
}

export function oidcLoginUrl(): string {
  return "/api/v1/auth/oidc/login";
}
