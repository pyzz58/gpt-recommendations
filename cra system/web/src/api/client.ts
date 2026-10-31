import type { components } from "./generated";

export type CapabilityResponse =
  components["schemas"]["CapabilityResponse"];
export type ScopeResponse = components["schemas"]["ScopeResponse"];
export type SessionResponse = components["schemas"]["SessionView"];
export type DocumentView = components["schemas"]["DocumentView"];
export type DocumentVersionView = components["schemas"]["VersionView"];
export type SourceAnchorView = components["schemas"]["AnchorView"];
export type ParseCoverageView = components["schemas"]["CoverageView"];
export type JobView = components["schemas"]["JobView"];
export type UploadResponse = components["schemas"]["UploadResponse"];

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

function csrfToken(): string {
  const entry = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("cra_csrf="));
  return entry ? decodeURIComponent(entry.slice("cra_csrf=".length)) : "";
}

export function getDocuments(
  studyId: string,
  siteId: string
): Promise<DocumentView[]> {
  return request<DocumentView[]>(
    `/api/v1/studies/${studyId}/documents?site_id=${encodeURIComponent(siteId)}`
  );
}

export function getDocumentVersions(
  documentId: string
): Promise<DocumentVersionView[]> {
  return request<DocumentVersionView[]>(
    `/api/v1/documents/${documentId}/versions`
  );
}

export function getVersionAnchors(
  versionId: string
): Promise<SourceAnchorView[]> {
  return request<SourceAnchorView[]>(
    `/api/v1/document-versions/${versionId}/anchors`
  );
}

export function getVersionCoverage(
  versionId: string
): Promise<ParseCoverageView[]> {
  return request<ParseCoverageView[]>(
    `/api/v1/document-versions/${versionId}/coverage`
  );
}

export function getJob(jobId: string): Promise<JobView> {
  return request<JobView>(`/api/v1/jobs/${jobId}`);
}

export function retryJob(jobId: string): Promise<{ job_id: string; status: string }> {
  return request(`/api/v1/jobs/${jobId}/retry`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken() }
  });
}

export function documentContentUrl(versionId: string): string {
  return `/api/v1/document-versions/${versionId}/content`;
}

export function uploadDocument(
  studyId: string,
  siteId: string,
  values: {
    title: string;
    documentType: string;
    purpose: string;
    versionLabel: string;
    publishedOn: string;
    userStartsOn: string;
    file: File;
    idempotencyKey: string;
  }
): Promise<UploadResponse> {
  const body = new FormData();
  body.set("title", values.title);
  body.set("document_type", values.documentType);
  body.set("purpose", values.purpose);
  body.set("version_label", values.versionLabel);
  body.set("expected_revision", "0");
  body.set("site_id", siteId);
  if (values.publishedOn) {
    body.set("published_on", values.publishedOn);
  }
  if (values.userStartsOn) {
    body.set("user_starts_on", values.userStartsOn);
  }
  body.set("file", values.file);
  return request<UploadResponse>(`/api/v1/studies/${studyId}/documents`, {
    method: "POST",
    body,
    headers: {
      "Idempotency-Key": values.idempotencyKey,
      "X-CSRF-Token": csrfToken()
    }
  });
}
