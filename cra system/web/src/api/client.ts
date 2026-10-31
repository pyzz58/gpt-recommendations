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
export type RuleListItemView = components["schemas"]["RuleListItemView"];
export type RuleVersionSummaryView =
  components["schemas"]["RuleVersionSummaryView"];
export type RuleRelationView = components["schemas"]["RuleRelationView"];
export type RuleVersionDetailView =
  components["schemas"]["RuleVersionDetailView"];
export type RuleNodeView = components["schemas"]["RuleNode-Output"];
export type RuleConditionView = components["schemas"]["RuleCondition-Output"];
export type RuleSourceRefView = components["schemas"]["RuleSourceRef"];
export type NodeEvaluationView = components["schemas"]["NodeEvaluation"];
export type ExtractionResponse =
  components["schemas"]["ExtractionResponse"];
export type ApplicabilityResponse =
  components["schemas"]["ApplicabilityResponse"];
export type ActivationResponse =
  components["schemas"]["ActivationResponse"];
export type SubjectView = components["schemas"]["SubjectView"];
export type ClinicalFactView =
  components["schemas"]["ClinicalFactView"];
export type EvaluateVisitRequirementsResponse =
  components["schemas"]["EvaluateVisitRequirementsResponse"];
export type CoverageBreakpointView =
  components["schemas"]["CoverageBreakpointView"];
export type CheckDecisionView =
  components["schemas"]["CheckDecisionView"];
export type ImportFactsResponse =
  components["schemas"]["ImportFactsResponse"];

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

export function getRules(
  studyId: string,
  siteId: string
): Promise<RuleListItemView[]> {
  return request<RuleListItemView[]>(
    `/api/v1/studies/${studyId}/rules?site_id=${encodeURIComponent(siteId)}`
  );
}

export function getRuleVersion(
  ruleVersionId: string
): Promise<RuleVersionDetailView> {
  return request<RuleVersionDetailView>(
    `/api/v1/rule-versions/${ruleVersionId}`
  );
}

export function getRuleVersions(
  ruleId: string
): Promise<RuleVersionSummaryView[]> {
  return request<RuleVersionSummaryView[]>(
    `/api/v1/rules/${ruleId}/versions`
  );
}

export function extractRuleCandidates(
  documentVersionId: string,
  idempotencyKey: string
): Promise<ExtractionResponse> {
  return request<ExtractionResponse>(
    `/api/v1/document-versions/${documentVersionId}/rule-candidates`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: 0,
        idempotency_key: idempotencyKey
      })
    }
  );
}

export function confirmRule(
  ruleId: string,
  values: {
    expectedRevision: number;
    baseVersionId: string;
    reason: string;
    operations: Record<string, unknown>[];
  }
): Promise<{
  rule_id: string;
  rule_version_id: string;
  revision: number;
  replayed: boolean;
}> {
  return request(`/api/v1/rules/${ruleId}/confirmation`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: values.expectedRevision,
      idempotency_key: crypto.randomUUID(),
      base_version_id: values.baseVersionId,
      reason: values.reason,
      operations: values.operations
    })
  });
}

export function createVersionActivation(values: {
  documentVersionId: string;
  startsOn: string;
  endsBefore: string;
  reason: string;
}): Promise<ActivationResponse> {
  return request<ActivationResponse>("/api/v1/version-activations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: 0,
      idempotency_key: crypto.randomUUID(),
      document_version_id: values.documentVersionId,
      starts_on: values.startsOn,
      ends_before: values.endsBefore || null,
      reason: values.reason
    })
  });
}

export function getApplicableRules(values: {
  studyId: string;
  siteId: string;
  eventDate: string;
  facts: Record<string, unknown>;
}): Promise<ApplicabilityResponse> {
  return request<ApplicabilityResponse>("/api/v1/rules/applicable", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      study_id: values.studyId,
      site_id: values.siteId,
      event_date: values.eventDate,
      jurisdiction: "synthetic",
      facts: values.facts
    })
  });
}

export function getSubjects(
  studyId: string,
  siteId: string
): Promise<SubjectView[]> {
  return request<SubjectView[]>(
    `/api/v1/studies/${studyId}/subjects?site_id=${encodeURIComponent(siteId)}`
  );
}

export function createSubject(values: {
  studyId: string;
  siteId: string;
  externalId: string;
  namespace: string;
}): Promise<{ id: string; revision: number }> {
  return request(`/api/v1/studies/${values.studyId}/subjects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: 0,
      idempotency_key: crypto.randomUUID(),
      site_id: values.siteId,
      external_id: values.externalId,
      identity_namespace: values.namespace,
      deidentified_label: values.externalId
    })
  });
}

export type SubjectFactInput = {
  subject_external_id: string;
  fact_key: string;
  value_raw: string;
  value_type?: string;
  observed_on?: string | null;
  observed_at?: string | null;
  precision?: string;
  unit?: string | null;
  repeat_instance?: string | null;
  visit_key?: string | null;
  source_kind?: string;
  source_ref: {
    source_type: string;
    source_id: string;
    locator?: string | null;
    quote?: string | null;
  };
};

export function importSubjectFacts(values: {
  studyId: string;
  siteId: string;
  namespace: string;
  sourceKind: string;
  rows: SubjectFactInput[];
}): Promise<ImportFactsResponse> {
  return request<ImportFactsResponse>(
    `/api/v1/studies/${values.studyId}/facts/import`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: 0,
        idempotency_key: crypto.randomUUID(),
        site_id: values.siteId,
        identity_namespace: values.namespace,
        source_kind: values.sourceKind,
        rows: values.rows
      })
    }
  );
}

export function importSubjectFile(values: {
  studyId: string;
  siteId: string;
  namespace: string;
  sourceKind: string;
  file: File;
}): Promise<ImportFactsResponse> {
  const body = new FormData();
  body.set("site_id", values.siteId);
  body.set("identity_namespace", values.namespace);
  body.set("source_kind", values.sourceKind);
  body.set("file", values.file);
  return request<ImportFactsResponse>(
    `/api/v1/studies/${values.studyId}/facts/import-file`,
    {
      method: "POST",
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "X-CSRF-Token": csrfToken()
      },
      body
    }
  );
}

export function getSubjectTimeline(
  subjectId: string
): Promise<ClinicalFactView[]> {
  return request<ClinicalFactView[]>(
    `/api/v1/subjects/${subjectId}/timeline`
  );
}

export function confirmSubjectFact(
  factId: string,
  expectedRevision: number
): Promise<ClinicalFactView> {
  return request<ClinicalFactView>(`/api/v1/facts/${factId}/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: expectedRevision,
      idempotency_key: crypto.randomUUID(),
      note: "CRA在工作台确认患者事实"
    })
  });
}

export function evaluateSubjectVisitRequirements(
  subjectId: string,
  eventDate: string
): Promise<EvaluateVisitRequirementsResponse> {
  return request<EvaluateVisitRequirementsResponse>(
    `/api/v1/subjects/${subjectId}/visit-requirements`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        event_date: eventDate,
        jurisdiction: "synthetic"
      })
    }
  );
}

export function getSubjectCoverage(
  subjectId: string
): Promise<CoverageBreakpointView[]> {
  return request<CoverageBreakpointView[]>(
    `/api/v1/subjects/${subjectId}/coverage`
  );
}

export function saveSubjectCoverage(
  subjectId: string,
  values: {
    expectedRevision: number;
    category: string;
    scopeKey: string;
    status: string;
    checkedThrough: string;
    normalScopeNote: string;
    unverifiedScope: string[];
  }
): Promise<CoverageBreakpointView> {
  return request<CoverageBreakpointView>(
    `/api/v1/subjects/${subjectId}/coverage`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: values.expectedRevision,
        idempotency_key: crypto.randomUUID(),
        category: values.category,
        scope_key: values.scopeKey,
        status: values.status,
        checked_through: values.checkedThrough || null,
        normal_scope_note: values.normalScopeNote || null,
        unverified_scope: values.unverifiedScope
      })
    }
  );
}

export function getCheckDecisions(
  subjectId: string
): Promise<CheckDecisionView[]> {
  return request<CheckDecisionView[]>(
    `/api/v1/subjects/${subjectId}/check-decisions`
  );
}

export function createCheckDecision(
  subjectId: string,
  values: {
    category: string;
    checkType: string;
    reason: string;
    scopeStart: string;
    scopeEnd: string;
    missingKeys: string[];
    affectedPaths: string[];
    canContinue: string[];
    ruleVersionId: string | null;
  }
): Promise<CheckDecisionView> {
  return request<CheckDecisionView>(
    `/api/v1/subjects/${subjectId}/check-decisions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: 0,
        idempotency_key: crypto.randomUUID(),
        category: values.category,
        check_type: values.checkType,
        reason: values.reason,
        scope_start: values.scopeStart || null,
        scope_end: values.scopeEnd || null,
        missing_keys: values.missingKeys,
        affected_paths: values.affectedPaths,
        can_continue: values.canContinue,
        rule_version_id: values.ruleVersionId
      })
    }
  );
}

export function resumeCheckDecision(
  subjectId: string,
  decisionId: string,
  expectedRevision: number
): Promise<CheckDecisionView> {
  return request<CheckDecisionView>(
    `/api/v1/subjects/${subjectId}/check-decisions/${decisionId}/resume`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: expectedRevision,
        idempotency_key: crypto.randomUUID(),
        reason: "CRA恢复核查该局部路径"
      })
    }
  );
}
