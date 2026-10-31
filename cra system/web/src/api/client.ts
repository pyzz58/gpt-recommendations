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
export type IssueView = components["schemas"]["IssueView"];
export type ActionView = components["schemas"]["ActionView"];
export type QueryLinkView = components["schemas"]["QueryLinkView"];
export type CarryoverResponse =
  components["schemas"]["CarryoverResponse"];
export type WorkbenchView = components["schemas"]["WorkbenchView"];
export type EDCPreviewView = components["schemas"]["EDCPreviewView"];
export type EDCSnapshotView = components["schemas"]["EDCSnapshotView"];
export type EDCSnapshotSummaryView =
  components["schemas"]["EDCSnapshotSummaryView"];
export type EDCMappingProfileView =
  components["schemas"]["EDCMappingProfileView"];
export type EDCSnapshotLookupView =
  components["schemas"]["EDCSnapshotLookupView"];
export type LabReportView = components["schemas"]["LabReportView"];
export type LabObservationView =
  components["schemas"]["LabObservationView"];
export type LabComparisonView =
  components["schemas"]["LabComparisonView"];
export type LabComparisonFieldView =
  components["schemas"]["LabComparisonFieldView"];
export type LabIssueLinkView =
  components["schemas"]["LabIssueLinkView"];
export type SafetyAssessmentView =
  components["schemas"]["SafetyAssessmentView"];
export type SafetyAssessmentSummaryView =
  components["schemas"]["SafetyAssessmentSummaryView"];
export type SafetyDimensionView =
  components["schemas"]["SafetyDimensionView"];
export type SafetyQuestionView =
  components["schemas"]["SafetyQuestionView"];
export type TimelySafetyAlertView =
  components["schemas"]["TimelySafetyAlertView"];

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

export function getSafetyAssessments(
  studyId: string,
  siteId: string,
  subjectId: string
): Promise<SafetyAssessmentSummaryView[]> {
  const query = new URLSearchParams({
    site_id: siteId,
    subject_id: subjectId
  });
  return request<SafetyAssessmentSummaryView[]>(
    `/api/v1/studies/${studyId}/safety-assessments?${query.toString()}`
  );
}

export function getSafetyAssessment(
  assessmentId: string
): Promise<SafetyAssessmentView> {
  return request<SafetyAssessmentView>(
    `/api/v1/safety-assessments/${assessmentId}`
  );
}

export function createSafetyAssessment(values: {
  studyId: string;
  siteId: string;
  subjectId: string;
  eventType: string;
  eventDate: string;
  requestedDimensions: string[];
  note: string;
}): Promise<SafetyAssessmentView> {
  return request<SafetyAssessmentView>("/api/v1/safety-assessments", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: 0,
      idempotency_key: crypto.randomUUID(),
      study_id: values.studyId,
      site_id: values.siteId,
      subject_id: values.subjectId,
      event_type: values.eventType,
      event_date: values.eventDate,
      requested_dimensions: values.requestedDimensions,
      lab_comparison_id: null,
      note: values.note || null
    })
  });
}

export function recordSafetyCraReview(
  assessmentId: string,
  values: {
    decision: string;
    dimensions: string[];
    note: string;
  }
): Promise<SafetyAssessmentView> {
  return request<SafetyAssessmentView>(
    `/api/v1/safety-assessments/${assessmentId}/cra-review`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        decision: values.decision,
        dimensions: values.dimensions,
        note: values.note || null
      })
    }
  );
}

export function recordMedicalSafetyResponse(
  assessmentId: string,
  values: {
    respondentRole: string;
    respondentName: string;
    responseText: string;
    dimensionResponses: Record<string, string>;
    sourceNote: string;
  }
): Promise<SafetyAssessmentView> {
  return request<SafetyAssessmentView>(
    `/api/v1/safety-assessments/${assessmentId}/medical-response`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        respondent_role: values.respondentRole,
        respondent_name: values.respondentName || null,
        response_text: values.responseText,
        dimension_responses: values.dimensionResponses,
        source_note: values.sourceNote || null
      })
    }
  );
}

export function linkSafetyAssessmentIssue(
  assessmentId: string,
  values: {
    dimensions: string[];
    requirement: string;
  }
): Promise<IssueView> {
  return request<IssueView>(
    `/api/v1/safety-assessments/${assessmentId}/issues`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        dimensions: values.dimensions,
        action_kind: "medical_clarification",
        requirement: values.requirement || null
      })
    }
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

export function getIssues(
  studyId: string,
  siteId: string,
  remainingOnly = false
): Promise<IssueView[]> {
  const params = new URLSearchParams({
    site_id: siteId,
    remaining_only: String(remainingOnly)
  });
  return request<IssueView[]>(
    `/api/v1/studies/${studyId}/issues?${params.toString()}`
  );
}

export function createIssue(
  studyId: string,
  values: {
    siteId: string;
    issueNumber?: string;
    finding: string;
    location?: string;
    recommendation?: string;
    knownProgress?: string;
    actions: {
      kind: string;
      requirement?: string;
      actionKey?: string;
    }[];
  }
): Promise<IssueView> {
  return request<IssueView>(`/api/v1/studies/${studyId}/issues`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: 0,
      idempotency_key: crypto.randomUUID(),
      site_id: values.siteId,
      issue_number: values.issueNumber || null,
      original_finding: values.finding,
      location: values.location || null,
      recommendation: values.recommendation || null,
      recommendation_sources: [],
      known_progress: values.knownProgress || null,
      source_kind: "manual",
      source_refs: [
        {
          source_type: "record",
          source_id: `synthetic-manual:${crypto.randomUUID()}`,
          locator: "CRA工作台人工记录"
        }
      ],
      actions: values.actions.map((action, index) => ({
        action_key: action.actionKey || `A${index + 1}`,
        kind: action.kind,
        requirement: action.requirement || null,
        deadline_source_refs: []
      }))
    })
  });
}

export function confirmCorrectedActions(values: {
  actions: { id: string; revision: number }[];
  note?: string;
}): Promise<{ actions: ActionView[]; replayed: boolean }> {
  return request("/api/v1/actions/confirm-corrected", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      idempotency_key: crypto.randomUUID(),
      actions: values.actions.map((action) => ({
        action_id: action.id,
        expected_revision: action.revision
      })),
      optional_note: values.note || null
    })
  });
}

export function confirmPdReported(
  action: { id: string; revision: number },
  values: { statement: string; note?: string }
): Promise<ActionView> {
  return request<ActionView>(
    `/api/v1/actions/${action.id}/confirm-reported`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: action.revision,
        idempotency_key: crypto.randomUUID(),
        user_statement: values.statement,
        optional_note: values.note || null
      })
    }
  );
}

export function reopenIssueAction(
  action: { id: string; revision: number },
  reason: string
): Promise<ActionView> {
  return request<ActionView>(`/api/v1/actions/${action.id}/reopen`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: action.revision,
      idempotency_key: crypto.randomUUID(),
      reason
    })
  });
}

export function createQueryLink(
  issue: { id: string; revision: number },
  values: {
    state: "draft" | "formal";
    externalSystem: string;
    externalNumber: string;
    openedOn: string;
    dueOn: string;
    deadlineSource: string;
  }
): Promise<QueryLinkView> {
  return request<QueryLinkView>(
    `/api/v1/issues/${issue.id}/query-links`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: issue.revision,
        idempotency_key: crypto.randomUUID(),
        query_state: values.state,
        external_system: values.externalSystem || null,
        external_query_number: values.externalNumber || null,
        opened_on: values.openedOn || null,
        due_on: values.dueOn || null,
        deadline_source: values.deadlineSource || null,
        deadline_source_refs: []
      })
    }
  );
}

export function createMonitoringVisit(values: {
  studyId: string;
  siteId: string;
  title: string;
  scopeNote: string;
  stage?: string;
}): Promise<WorkbenchView> {
  return request<WorkbenchView>(
    `/api/v1/studies/${values.studyId}/monitoring-visits`,
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
        stage: values.stage || "carryover_review",
        title: values.title,
        scope_note: values.scopeNote || null
      })
    }
  );
}

export function getMonitoringWorkbench(
  visitId: string
): Promise<WorkbenchView> {
  return request<WorkbenchView>(
    `/api/v1/monitoring-visits/${visitId}/workbench`
  );
}

export function selectPrevisitIssues(
  visit: { id: string; revision: number },
  issueIds: string[]
): Promise<WorkbenchView> {
  return request<WorkbenchView>(
    `/api/v1/monitoring-visits/${visit.id}/previsit-selection`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: visit.revision,
        idempotency_key: crypto.randomUUID(),
        issue_ids: issueIds
      })
    }
  );
}

export function updateMonitoringScope(
  visit: { id: string; revision: number },
  values: { scopeNote: string; status: string }
): Promise<WorkbenchView> {
  return request<WorkbenchView>(
    `/api/v1/monitoring-visits/${visit.id}/scope`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: visit.revision,
        idempotency_key: crypto.randomUUID(),
        scope_note: values.scopeNote || null,
        status: values.status
      })
    }
  );
}

export function previewCarryoverDocument(values: {
  versionId: string;
  siteId: string;
}): Promise<CarryoverResponse> {
  return request<CarryoverResponse>(
    `/api/v1/document-versions/${values.versionId}/carryover-imports/preview`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: 0,
        idempotency_key: crypto.randomUUID(),
        site_id: values.siteId
      })
    }
  );
}

export function previewCarryoverText(values: {
  studyId: string;
  siteId: string;
  label: string;
  text: string;
}): Promise<CarryoverResponse> {
  return request<CarryoverResponse>(
    `/api/v1/studies/${values.studyId}/carryover-imports/preview-text`,
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
        source_label: values.label,
        text: values.text
      })
    }
  );
}

export function confirmCarryoverImport(
  preview: CarryoverResponse,
  corrections: Record<string, unknown>[]
): Promise<CarryoverResponse> {
  return request<CarryoverResponse>(
    `/api/v1/carryover-imports/${preview.import_record.id}/confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: preview.import_record.revision,
        idempotency_key: crypto.randomUUID(),
        corrections
      })
    }
  );
}

export function getEdcMappings(
  studyId: string,
  siteId: string,
  headerSignature?: string
): Promise<EDCMappingProfileView[]> {
  const params = new URLSearchParams({ site_id: siteId });
  if (headerSignature) {
    params.set("header_signature", headerSignature);
  }
  return request<EDCMappingProfileView[]>(
    `/api/v1/studies/${studyId}/edc-import-mappings?${params.toString()}`
  );
}

export function previewEdcImport(values: {
  studyId: string;
  siteId: string;
  title: string;
  file: File;
  exportScope: Record<string, unknown>;
  exportStartedAt: string;
  exportCompletedAt: string;
  includedSheets: string[];
  mappingProfileId?: string;
  identityNamespace?: string;
}): Promise<EDCPreviewView> {
  const body = new FormData();
  body.set("site_id", values.siteId);
  body.set("title", values.title);
  body.set("file", values.file);
  body.set("export_scope_json", JSON.stringify(values.exportScope));
  body.set("included_sheets_json", JSON.stringify(values.includedSheets));
  body.set("identity_namespace", values.identityNamespace || "edc");
  if (values.exportStartedAt) {
    body.set("export_started_at", values.exportStartedAt);
  }
  if (values.exportCompletedAt) {
    body.set("export_completed_at", values.exportCompletedAt);
  }
  if (values.mappingProfileId) {
    body.set("mapping_profile_id", values.mappingProfileId);
  }
  return request<EDCPreviewView>(
    `/api/v1/studies/${values.studyId}/edc-imports/preview`,
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

export function getEdcPreview(
  previewId: string
): Promise<EDCPreviewView> {
  return request<EDCPreviewView>(`/api/v1/edc-imports/${previewId}`);
}

export function confirmEdcImport(values: {
  preview: EDCPreviewView;
  mapping: Record<string, unknown>;
  exportScope: Record<string, unknown>;
  identityNamespace: string;
  saveMappingName: string;
}): Promise<EDCSnapshotView> {
  return request<EDCSnapshotView>(
    `/api/v1/edc-imports/${values.preview.id}/confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: values.preview.revision,
        idempotency_key: crypto.randomUUID(),
        mapping: values.mapping,
        export_scope: values.exportScope,
        identity_namespace: values.identityNamespace,
        save_mapping_name: values.saveMappingName || null
      })
    }
  );
}

export function getEdcSnapshot(
  snapshotId: string
): Promise<EDCSnapshotView> {
  return request<EDCSnapshotView>(
    `/api/v1/edc-snapshots/${snapshotId}`
  );
}

export function getEdcSnapshots(
  studyId: string,
  siteId: string
): Promise<EDCSnapshotSummaryView[]> {
  return request<EDCSnapshotSummaryView[]>(
    `/api/v1/studies/${studyId}/edc-snapshots?site_id=${encodeURIComponent(siteId)}`
  );
}

export function lookupEdcSnapshot(
  snapshotId: string,
  values: {
    subjectExternalId: string;
    analyte: string;
    collectedOn?: string;
    instanceType?: string;
  }
): Promise<EDCSnapshotLookupView> {
  return request<EDCSnapshotLookupView>(
    `/api/v1/edc-snapshots/${snapshotId}/lookup`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject_external_id: values.subjectExternalId,
        analyte: values.analyte,
        collected_on: values.collectedOn || null,
        instance_type: values.instanceType || null
      })
    }
  );
}

export function getLabReports(
  studyId: string,
  siteId: string
): Promise<LabReportView[]> {
  return request<LabReportView[]>(
    `/api/v1/studies/${studyId}/lab-reports?site_id=${encodeURIComponent(siteId)}`
  );
}

export function createLabReport(values: {
  studyId: string;
  siteId: string;
  title: string;
  versionLabel: string;
  file: File;
}): Promise<LabReportView> {
  const body = new FormData();
  body.set("site_id", values.siteId);
  body.set("title", values.title);
  body.set("version_label", values.versionLabel);
  body.set("file", values.file);
  return request<LabReportView>(
    `/api/v1/studies/${values.studyId}/lab-reports`,
    {
      method: "POST",
      body,
      headers: {
        "Idempotency-Key": crypto.randomUUID(),
        "X-CSRF-Token": csrfToken()
      }
    }
  );
}

export function getLabReport(reportId: string): Promise<LabReportView> {
  return request<LabReportView>(`/api/v1/lab-reports/${reportId}`);
}

export function reviewLabObservation(
  report: LabReportView,
  observationId: string,
  values: {
    action: "confirm" | "correct" | "skip";
    correctedFields?: Record<string, unknown>;
    note?: string;
  }
): Promise<LabReportView> {
  return request<LabReportView>(
    `/api/v1/lab-reports/${report.id}/observations/${observationId}/decision`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: report.revision,
        idempotency_key: crypto.randomUUID(),
        action: values.action,
        corrected_fields: values.correctedFields ?? {},
        note: values.note || null
      })
    }
  );
}

export function batchConfirmLabObservations(
  report: LabReportView,
  observationIds: string[]
): Promise<LabReportView> {
  return request<LabReportView>(
    `/api/v1/lab-reports/${report.id}/observations/batch-confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: report.revision,
        idempotency_key: crypto.randomUUID(),
        observation_ids: observationIds,
        note: "批量确认已通过结构、来源和实例校验的候选"
      })
    }
  );
}

export function addManualLabObservation(
  report: LabReportView,
  values: {
    subjectExternalId: string;
    visitKey: string;
    analyte: string;
    specimen: string;
    collectedOn: string;
    collectedAt: string;
    instanceType: string;
    reportRevision: string;
    valueRaw: string;
    unitRaw: string;
    lowerLimit: string;
    upperLimit: string;
    sourceNote: string;
  }
): Promise<LabReportView> {
  return request<LabReportView>(
    `/api/v1/lab-reports/${report.id}/observations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        expected_revision: report.revision,
        idempotency_key: crypto.randomUUID(),
        subject_external_id: values.subjectExternalId,
        visit_key: values.visitKey || null,
        analyte_raw: values.analyte,
        specimen: values.specimen || null,
        collected_on: values.collectedOn,
        collected_at: values.collectedAt
          ? new Date(values.collectedAt).toISOString()
          : null,
        instance_type_raw: values.instanceType,
        report_revision: values.reportRevision || null,
        value_raw: values.valueRaw,
        unit_raw: values.unitRaw || null,
        lower_limit_raw: values.lowerLimit || null,
        upper_limit_raw: values.upperLimit || null,
        source_note: values.sourceNote
      })
    }
  );
}

export function createLabComparison(values: {
  reportId: string;
  edcSnapshotId: string;
}): Promise<LabComparisonView> {
  return request<LabComparisonView>("/api/v1/lab-comparisons", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken()
    },
    body: JSON.stringify({
      expected_revision: 0,
      idempotency_key: crypto.randomUUID(),
      report_id: values.reportId,
      edc_snapshot_id: values.edcSnapshotId
    })
  });
}

export function getLabComparison(
  comparisonId: string
): Promise<LabComparisonView> {
  return request<LabComparisonView>(
    `/api/v1/lab-comparisons/${comparisonId}`
  );
}

export function linkLabComparisonIssues(
  comparisonId: string,
  fieldIds: string[]
): Promise<LabIssueLinkView> {
  return request<LabIssueLinkView>(
    `/api/v1/lab-comparisons/${comparisonId}/issues`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken()
      },
      body: JSON.stringify({
        idempotency_key: crypto.randomUUID(),
        field_ids: fieldIds
      })
    }
  );
}
