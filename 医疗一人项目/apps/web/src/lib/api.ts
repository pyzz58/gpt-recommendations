export type DependencyStatus = {
  status: string;
  detail: string;
};

export type ProviderCapability = {
  provider_id: string;
  mode: "mock" | "live";
  status: string;
  detail: string;
};

export type CapabilityReport = {
  mode: "mock" | "live";
  label: string;
  implementation_scope: string;
  providers: ProviderCapability[];
  dependencies: Record<string, DependencyStatus>;
  external_actions: DependencyStatus;
  limitations: string[];
};

export type HealthReport = {
  status: "ok" | "not_ready";
  mode: "mock" | "live";
  checks: Record<string, DependencyStatus>;
};

export type MockSmokeResponse = {
  mode: "mock";
  provider_id: string;
  output: string;
  disclaimer: string;
};

export type SessionView = {
  session_id: string;
  user_id: string;
  workspace_id: string;
  display_name: string;
  expires_at: string | null;
};

export type ProjectSnapshot = {
  id: string;
  workspace_id: string;
  name: string;
  scope: string;
  stage: string;
  status: string;
  revision: number;
  created_at: string;
  updated_at: string;
  policy_bundle_id?: string | null;
};

export type ProjectListItem = {
  project: ProjectSnapshot;
  open_tasks: number;
  documents: number;
  opportunities: number;
};

export type OpportunitySummary = {
  id: string;
  title: string;
  track: string;
  status: string;
  current_version: number;
  revision: number;
};

export type ProjectEvent = {
  event_id: string;
  project_seq: number;
  project_id: string;
  type: string;
  object_type: string;
  object_id: string;
  object_revision: number;
  actor_user_id: string | null;
  payload: Record<string, unknown>;
  correlation_id: string;
  occurred_at: string;
};

export type ProjectOverview = {
  project: ProjectSnapshot;
  counts: {
    tasks: number;
    open_tasks: number;
    documents: number;
    opportunities: number;
    active_agents: number;
  };
  current_direction: OpportunitySummary | null;
  current_selection_decision_id: string | null;
  opportunities: OpportunitySummary[];
  action_required: {
    kind: string;
    object_id: string;
    title: string;
    detail: string;
    state: string;
  }[];
  recent_events: ProjectEvent[];
};

export type PolicyBundleView = {
  id: string;
  workspace_id: string;
  version_label: string;
  content_sha256: string;
  theory_version: string;
  theory_sha256: string;
  component_sha256: Record<string, string>;
  state: "published" | "retired";
  created_at: string;
};

export type PolicyImpactView = {
  id: string;
  project_id: string;
  from_bundle_id: string | null;
  to_bundle_id: string;
  changed_components: string[];
  affected_requirements: string[];
  affected_task_ids: string[];
  status: "recorded" | "applied";
  created_at: string;
};

export type PolicyMigrationView = {
  id: string;
  project_id: string;
  kind: "config" | "database";
  from_bundle_id: string | null;
  to_bundle_id: string;
  expected_project_revision: number;
  schema_revision: string | null;
  state:
    | "dry_run_passed"
    | "dry_run_failed"
    | "applying"
    | "succeeded"
    | "failed"
    | "rolled_back";
  report: Record<string, unknown>;
  backup_ref: string | null;
  error_code: string | null;
  created_at: string;
  finished_at: string | null;
};

export type ProjectPolicyView = {
  project_id: string;
  project_revision: number;
  active_bundle: PolicyBundleView | null;
  project_bundle: PolicyBundleView | null;
  impacts: PolicyImpactView[];
  migrations: PolicyMigrationView[];
  limitations: string[];
};

export type TaskView = {
  id: string;
  task_type: string;
  purpose: string;
  assignee_role: string;
  goal: string;
  state: string;
  mode: string;
  revision: number;
  input_version: string;
  input_refs: string[];
  input_validity: "current" | "stale" | "under_review";
  input_snapshot_sha256: string | null;
  policy_bundle_id: string | null;
  input_invalidated_at: string | null;
  input_invalidated_reason: string | null;
  deliverable_schema: string;
  acceptance_policy: string;
  dependencies: string[];
  created_at: string;
  updated_at: string;
};

export type AgentRunSummary = {
  id: string;
  state: string;
  mode: string;
  provider_id: string;
  model_id: string;
  policy_bundle_id: string | null;
  created_at: string;
  ended_at: string | null;
};

export type AgentScene = {
  role_id: string;
  name: string;
  version: number;
  reports_to: string[];
  responsibilities: string[];
  deliverable_types: string[];
  scene_state: string;
  instance_state: string;
  latest_task_id: string | null;
  latest_task_goal: string | null;
  latest_task_state: string | null;
  latest_run: AgentRunSummary | null;
  updated_at: string | null;
};

export type MechanismStep = {
  statement: string;
  status: "fact" | "inference" | "hypothesis";
  evidence_refs: string[];
};

export type ProbabilityEstimate = {
  event: string;
  conditions: string;
  horizon: string;
  success_criterion: string;
  method: "empirical" | "validated_model" | "subjective_scenario" | "unknown";
  basis_refs: string[];
  population_or_base_rate: string | null;
  lower: number | null;
  upper: number | null;
  calibration_status: string;
  limitations: string[];
  unknown_reason: string | null;
};

export type CostEstimate = {
  currency: string;
  scope: string;
  stage: string;
  line_items: {
    item: string;
    quantity: number | null;
    unit: string;
    unit_cost_lower: number | null;
    unit_cost_upper: number | null;
    source_type: string;
    source_ref: string | null;
  }[];
  price_date: string | null;
  expiry: string | null;
  tax_shipping_assumption: string | null;
  excluded_work: string[];
  contingency_basis: string | null;
  total_range: [number | null, number | null];
  unknown_items: string[];
};

export type OpportunityCard = {
  title: string;
  track: "pet_repurposing" | "ivd" | "device";
  proposed_use: string;
  target_population_or_scene: string;
  need_evidence_refs: string[];
  mechanism_steps: MechanismStep[];
  current_alternatives: string[];
  proposed_advantage: string;
  comparison_metrics: string[];
  gaps: Record<string, string[]>;
  next_validation: {
    objective: string;
    success_criteria: string[];
    stop_criteria: string[];
    possible_outcomes: string[];
  };
  probabilities: ProbabilityEstimate[];
  costs: CostEstimate[];
  change_trigger: string;
  professional_opinions: Record<string, string>;
  review_findings: string[];
  evidence_cutoff: string;
  limitations: string[];
};

export type OpportunityView = {
  id: string;
  project_id: string;
  title: string;
  status: string;
  current_version: number;
  revision: number;
  card: OpportunityCard;
};

export type SelectionView = {
  decision_id: string;
  opportunity_id: string;
  opportunity_version: number;
  status: string;
};

export type PlanStatus =
  | "draft"
  | "active"
  | "paused"
  | "stopped"
  | "completed";

export type ReviewDecision =
  | "accepted"
  | "changes_requested"
  | "disputed";

export type ReviewFinding = {
  code: string;
  severity: "critical" | "major" | "minor";
  message: string;
  evidence_refs: string[];
};

export type PlanNodeView = {
  node_id: string;
  task_id: string;
  node_key: string;
  order_index: number;
  task_type: string;
  goal: string;
  assignee_role: string;
  task_state: string;
  task_revision: number;
  dependencies: string[];
  reviewer_roles: string[];
};

export type PlanReviewSummary = {
  review_id: string;
  task_id: string;
  reviewer_role: string;
  decision: ReviewDecision;
  review_round: number;
  summary: string;
  findings: ReviewFinding[];
  created_at: string;
};

export type PlanView = {
  id: string;
  project_id: string;
  plan_version: number;
  status: PlanStatus;
  revision: number;
  title: string;
  objective: string;
  source_decision_id: string;
  workflow_track: "pet_repurposing" | "ivd" | "device" | null;
  workflow_id: string | null;
  workflow_version: number | null;
  workflow_sha256: string | null;
  stage_id: string | null;
  pause_reason: string | null;
  max_rework_rounds: number;
  nodes: PlanNodeView[];
  reviews: PlanReviewSummary[];
  created_at: string;
  updated_at: string;
  activated_at: string | null;
  paused_at: string | null;
  stopped_at: string | null;
};

export type PlanNodeSpecInput = {
  key: string;
  task_type: string;
  purpose: string;
  assignee_role: string;
  role_version: string;
  input_version: string;
  input_refs: string[];
  goal: string;
  deliverable_schema: string;
  acceptance_policy: string;
  mode?: "mock";
  max_attempts?: number;
  depends_on?: string[];
};

export type PlanSpecInput = {
  title: string;
  objective: string;
  nodes: PlanNodeSpecInput[];
  max_rework_rounds?: number;
};

export type PlanDispatchView = {
  plan_id: string;
  plan_revision: number;
  dispatched: {
    task_id: string;
    node_key: string;
    assignee_role: string;
    task_state: string;
    task_revision: number;
  }[];
};

export type PlanExecutionView = {
  plan_id: string;
  executed: {
    task_id: string;
    role_id: string;
    task_state: string;
    run_id: string;
    run_state: string;
  }[];
};

export type TaskReviewView = {
  review_id: string;
  plan_id: string;
  task_id: string;
  decision: ReviewDecision;
  review_round: number;
  task_state: string;
  task_revision: number;
  unlocked_task_ids: string[];
  plan_status: PlanStatus;
};

export type WorkflowCriterion = {
  id: string;
  kind: "evidence" | "professional_judgment" | "decision" | "review";
  description: string;
  required: boolean;
  requires_refs: boolean;
};

export type WorkflowPlanNode = {
  key: string;
  task_type: string;
  purpose: string;
  assignee_role: string;
  goal: string;
  input_refs: string[];
  deliverable_schema: string;
  acceptance_policy: string;
  depends_on: string[];
};

export type ExternalPrecondition = {
  id: string;
  description: string;
  provider_type: string;
  evidence_type: string;
  required: boolean;
  cannot_self_confirm: true;
};

export type WorkflowStage = {
  stage_id: string;
  sequence: number;
  title: string;
  purpose: string;
  required_roles: string[];
  criteria: WorkflowCriterion[];
  required_inputs: string[];
  required_outputs: string[];
  review_policy: string;
  failure_routes: Record<string, string>;
  external_preconditions: ExternalPrecondition[];
  theory_refs: string[];
  plan_nodes: WorkflowPlanNode[];
};

export type WorkflowDefinition = {
  schema_version: 1;
  workflow_id: string;
  version: number;
  track: "pet_repurposing" | "ivd" | "device";
  title: string;
  purpose: string;
  applicability: string[];
  non_goals: string[];
  stages: WorkflowStage[];
};

export type WorkflowDescriptor = {
  definition: WorkflowDefinition;
  sha256: string;
};

export type CriterionResult = {
  criterion_id: string;
  status: "met" | "unmet" | "unknown";
  rationale: string;
  evidence_refs: string[];
};

export type StageAssessmentView = {
  id: string;
  project_id: string;
  workflow_track: "pet_repurposing" | "ivd" | "device";
  workflow_id: string;
  workflow_version: number;
  workflow_sha256: string;
  stage_id: string;
  assessment_version: number;
  status: "needs_evidence" | "needs_revision" | "blocked" | "ready_for_review";
  recommendation:
    | "continue_to_review"
    | "gather_evidence"
    | "revise"
    | "wait_external"
    | "stop";
  criterion_results: CriterionResult[];
  external_preconditions: {
    id: string;
    description: string;
    provider_type: string;
    evidence_type: string;
    status: string;
    cannot_self_confirm: boolean;
  }[];
  evidence_refs: string[];
  rationale: string;
  decision: "accepted" | "changes_requested" | "blocked" | null;
  reviewer_role: string | null;
  created_at: string;
};

export type DatasetVersionView = {
  id: string;
  dataset_id: string;
  version_number: number;
  kind: "raw" | "derived";
  state: "ready" | "partial" | "rejected";
  source_document_version_id: string | null;
  parent_version_id: string | null;
  manifest: Record<string, unknown>;
  transformation: Record<string, unknown> | null;
  rows_sha256: string;
  row_count: number;
  columns: string[];
  quality_findings: Record<string, unknown>[];
  preview: Record<string, unknown>[];
  created_at: string;
};

export type DatasetView = {
  id: string;
  project_id: string;
  title: string;
  revision: number;
  current_version: DatasetVersionView;
  versions: DatasetVersionView[];
  created_at: string;
  updated_at: string;
};

export type StatisticalPlanSpecInput = {
  question: string;
  endpoint_column: string;
  method:
    | "descriptive_continuous"
    | "two_group_mean_difference"
    | "proportion_wilson";
  group_column: string | null;
  analysis_set: string;
  missing_policy: "exclude_endpoint_missing" | "fail_if_missing";
  unit: string | null;
  alpha: number;
  expected_groups: string[];
  limitations: string[];
  exploratory: boolean;
};

export type StatisticalPlanView = {
  id: string;
  project_id: string;
  dataset_version_id: string;
  plan_version: number;
  question: string;
  endpoint_column: string;
  method: StatisticalPlanSpecInput["method"];
  group_column: string | null;
  analysis_set: string;
  missing_policy: string;
  unit: string | null;
  alpha: number;
  expected_groups: string[];
  limitations: string[];
  exploratory: boolean;
  created_at: string;
};

export type AnalysisReviewView = {
  id: string;
  analysis_id: string;
  decision: ReviewDecision;
  reviewer_role: string;
  summary: string;
  findings: ReviewFinding[];
  result_sha256: string;
  created_at: string;
};

export type AnalysisRunView = {
  id: string;
  project_id: string;
  dataset_version_id: string;
  plan_id: string;
  analysis_version: number;
  code_version: string;
  code_sha256: string;
  environment: Record<string, unknown>;
  random_seed: number;
  state: "succeeded" | "failed";
  result: Record<string, unknown>;
  chart_spec: Record<string, unknown>;
  input_sha256: string;
  output_sha256: string;
  error_code: string | null;
  created_at: string;
  latest_review: AnalysisReviewView | null;
};

export type ArtifactExportFormat = "docx" | "pptx" | "xlsx" | "pdf";

export type ArtifactExportRuntime = {
  status: string;
  detail: string;
  soffice_path: string | null;
  pdftoppm_path: string | null;
  versions: Record<string, string>;
  templates: {
    template_id: string;
    version: number;
    name: string;
    format: ArtifactExportFormat;
    description: string;
  }[];
};

export type ArtifactExportView = {
  id: string;
  project_id: string;
  analysis_id: string;
  artifact_version_id: string | null;
  version: number | null;
  filename: string;
  format: ArtifactExportFormat;
  media_type: string;
  template_id: string;
  template_version: number;
  mode: string;
  data_origin: string;
  state: "running" | "succeeded" | "failed";
  validation_status: string;
  revision: number;
  art_sha256: string | null;
  size_bytes: number | null;
  preview_pdf_sha256: string | null;
  preview_png_sha256: string | null;
  page_count: number | null;
  validation: {
    status?: string;
    scope?: string;
    checks?: {
      code: string;
      status: string;
      message: string;
      [key: string]: unknown;
    }[];
    formula_checks?: {
      code: string;
      status: string;
      message: string;
      sheet?: string;
      cell?: string;
      cached_value?: unknown;
      expected?: unknown;
    }[];
    tool_versions?: Record<string, string>;
    limitations?: string[];
    [key: string]: unknown;
  };
  source_sha256: string;
  report_sha256: string;
  error_code: string | null;
  error_message: string | null;
  download_url: string | null;
  preview_pdf_url: string | null;
  preview_png_url: string | null;
  created_at: string;
  completed_at: string | null;
};

export type MailAccountView = {
  id: string;
  address: string;
  display_name: string;
  provider_id: string;
  mode: "mock" | "live";
  state: string;
  external_send_enabled: boolean;
  note: string;
};

export type MailMessageView = {
  id: string;
  provider_message_id: string;
  internet_message_id: string | null;
  in_reply_to: string | null;
  references: string[];
  direction: "inbound" | "outbound";
  sender: string;
  recipients: { to: string[]; cc: string[]; bcc: string[] };
  subject: string;
  body_text: string;
  body_sha256: string;
  sent_at: string;
  delivery_state: string;
  synthetic: boolean;
};

export type MailThreadView = {
  id: string;
  project_id: string | null;
  provider_thread_id: string;
  subject: string;
  link_state: "unlinked" | "linked";
  revision: number;
  last_message_at: string;
  messages: MailMessageView[];
};

export type MailAttachmentView = {
  id: string;
  source_type: "artifact_version" | "knowledge_version";
  source_id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  sha256: string;
};

export type MailDraftView = {
  id: string;
  project_id: string;
  account_id: string;
  thread_id: string | null;
  recipients: { to: string[]; cc: string[]; bcc: string[] };
  subject: string;
  body_text: string;
  body_sha256: string;
  content_sha256: string;
  state: string;
  revision: number;
  attachments: MailAttachmentView[];
  created_at: string;
  updated_at: string;
};

export type MailAuthorizationView = {
  id: string;
  project_id: string;
  account_id: string;
  draft_id: string;
  action: "mail.send";
  recipients: { to: string[]; cc: string[]; bcc: string[] };
  attachment_hashes: string[];
  content_sha256: string;
  max_sends: number;
  used_sends: number;
  valid_from: string;
  expires_at: string;
  state: string;
  revision: number;
  created_at: string;
};

export type MailAttemptView = {
  id: string;
  project_id: string;
  draft_id: string;
  authorization_id: string;
  state: string;
  subject: string;
  recipients: { to: string[]; cc: string[]; bcc: string[] };
  body_sha256: string;
  attachment_manifest: {
    filename: string;
    media_type: string;
    size_bytes: number;
    sha256: string;
  }[];
  provider_message_id: string | null;
  provider_thread_id: string | null;
  internet_message_id: string | null;
  outcome_detail: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type MailSendResultView = {
  attempt: MailAttemptView;
  draft_state: string;
};

export type ProviderType =
  | "cdmo"
  | "cro"
  | "smo"
  | "central_lab"
  | "testing_lab"
  | "sample_provider"
  | "prototype_provider"
  | "regulatory"
  | "ethics"
  | "other";

export type ExternalOrganizationView = {
  id: string;
  project_id: string;
  name: string;
  provider_type: ProviderType;
  capability_summary: string;
  source_refs: string[];
  verification_state: string;
  revision: number;
};

export type ExternalContactView = {
  id: string;
  organization_id: string;
  name: string;
  role: string;
  email: string | null;
  source_refs: string[];
  verification_state: string;
  revision: number;
};

export type ExternalExpertView = {
  id: string;
  name: string;
  expertise: string;
  public_source_refs: string[];
  contact_email: string | null;
  conflict_notes: string;
  state: string;
  revision: number;
};

export type ExternalEngagementView = {
  id: string;
  organization_id: string;
  title: string;
  scope: {
    scientific_question: string;
    decision_impact: string;
    input_requirements: string[];
    deliverables: string[];
    method_and_quality: string[];
    rights_and_confidentiality: string[];
    acceptance_responsibility: string;
    target_start?: string | null;
    target_end?: string | null;
    budget_lower?: string | null;
    budget_upper?: string | null;
    currency: string;
  };
  scope_sha256: string;
  state: string;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type ExternalQuoteView = {
  id: string;
  engagement_id: string;
  amount: string | null;
  currency: string;
  tax_included: boolean | null;
  shipping_included: boolean | null;
  assumptions: string[];
  excluded_work: string[];
  valid_until: string | null;
  document_version_id: string | null;
  state: string;
  scope_sha256: string;
  created_at: string;
};

export type ExternalContractView = {
  id: string;
  engagement_id: string;
  quote_id: string | null;
  title: string;
  terms_summary: string;
  document_version_id: string | null;
  state: string;
  internal_signed: boolean;
  external_signed: boolean;
  signed_at: string | null;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type ExternalDeliverableView = {
  id: string;
  engagement_id: string;
  title: string;
  kind: string;
  expected_items: string[];
  state: string;
  knowledge_version_id: string | null;
  manifest: Record<string, unknown>;
  missing_items: string[];
  receipt_summary: string | null;
  received_at: string | null;
  reviewer_role: string | null;
  review_summary: string | null;
  findings: string[];
  due_at: string | null;
  revision: number;
  created_at: string;
  updated_at: string;
};

export type ProfessionalRecordView = {
  id: string;
  kind: string;
  state: string;
  title: string;
  source_tier: string;
  source_title: string | null;
  source_ref: string | null;
  checked_at: string | null;
  market: string | null;
  product_scope: string | null;
  jurisdiction: string | null;
  patent_status: string | null;
  application_number: string | null;
  publication_number: string | null;
  financial_event_type: string | null;
  amount: string | null;
  currency: string | null;
  commercial_evidence_type: string | null;
  facts: string[];
  limitations: string[];
  metadata: Record<string, unknown>;
  revision: number;
  created_at: string;
};

export type ExternalAuthorizationView = {
  id: string;
  engagement_id: string;
  action_scope: string;
  scope_sha256: string;
  amount_max: string;
  currency: string;
  valid_from: string;
  expires_at: string;
  state: string;
  revision: number;
  created_at: string;
};

export type ExternalWorkspaceView = {
  organizations: ExternalOrganizationView[];
  contacts: ExternalContactView[];
  experts: ExternalExpertView[];
  engagements: ExternalEngagementView[];
  quotes: ExternalQuoteView[];
  contracts: ExternalContractView[];
  deliverables: ExternalDeliverableView[];
  professional_records: ProfessionalRecordView[];
  authorizations: ExternalAuthorizationView[];
};

export type AuditTargetType =
  | "claim_version"
  | "analysis_run"
  | "external_deliverable";

export type AuditTargetView = {
  target_type: AuditTargetType;
  target_id: string;
  label: string;
  detail: string;
};

export type AuditFindingView = {
  id: string;
  code: string;
  severity: "critical" | "major" | "minor";
  category: string;
  message: string;
  evidence_refs: string[];
  affected_objects: Record<string, string>[];
  status: "open" | "resolved" | "accepted_risk";
  resolution: string | null;
  created_at: string;
};

export type AuditRunView = {
  id: string;
  project_id: string;
  target_type: AuditTargetType;
  target_id: string;
  linked_task_id: string | null;
  target_sha256: string;
  input_sha256: string;
  reviewer_role: "A25" | "A26";
  producer_role: string | null;
  method: string;
  state: "passed" | "changes_requested" | "blocked";
  downstream_blocked: boolean;
  summary: string;
  review_version: number;
  input_snapshot: Record<string, unknown>;
  findings: AuditFindingView[];
  created_at: string;
};

export type AuditEvaluationView = {
  id: string;
  fixture_name: string;
  fixture_sha256: string;
  metrics: {
    cases: number;
    true_positives: number;
    false_positives: number;
    false_negatives: number;
    precision: number;
    recall: number;
  };
  case_results: {
    case_id: string;
    reviewer_role: string;
    expected_codes: string[];
    predicted_codes: string[];
    matched_codes: string[];
    unexpected_codes: string[];
    missed_codes: string[];
  }[];
  limitations: string[];
  created_at: string;
};

export type AuditWorkspaceView = {
  targets: AuditTargetView[];
  reviews: AuditRunView[];
  evaluations: AuditEvaluationView[];
  limitations: string[];
};

export type TrashEntryView = {
  id: string;
  document_id: string;
  title: string;
  reference_count: number;
  blocked_reason: string | null;
  reason: string;
  state: "trashed" | "restored" | "purged";
  purge_after: string;
  deleted_at: string;
  restored_at: string | null;
};

export type IndexRebuildView = {
  version_id: string;
  chunks: number;
  state: string;
  index_version: string;
  rebuilt: boolean;
};

export type BackupView = {
  id: string;
  project_id: string;
  format: string;
  file_name: string;
  state: "completed" | "failed";
  backup_sha256: string | null;
  plaintext_sha256: string | null;
  encrypted_size_bytes: number;
  manifest: {
    schema_version: number;
    counts: Record<string, number>;
    objects: {
      object_key: string;
      sha256: string;
      size_bytes: number;
      source: string;
    }[];
    limitations: string[];
  };
  error_code: string | null;
  created_at: string;
};

export type RestoreCheckView = {
  id: string;
  backup_id: string;
  state: "verified" | "failed";
  object_count: number;
  table_counts: Record<string, number>;
  detail: Record<string, unknown>;
  created_at: string;
};

export type RecoveryWorkspaceView = {
  trash: TrashEntryView[];
  backups: BackupView[];
  restore_checks: RestoreCheckView[];
  limitations: string[];
};

export type QuoteComparisonView = {
  engagement_id: string;
  scope_sha256: string;
  comparable: ExternalQuoteView[];
  excluded: ExternalQuoteView[];
  warnings: string[];
};

export type KnowledgeDocumentSummary = {
  id: string;
  title: string;
  document_kind: string;
  revision: number;
  current_version_id: string | null;
  version_id: string | null;
  version_label: string | null;
  filename: string | null;
  media_type: string | null;
  size_bytes: number | null;
  ingest_state: string;
  evidence_status: string;
  version_status: string;
  access_state: string;
  cloud_policy: string;
  ingested_at: string | null;
  created_at: string;
  versions_count: number;
  citations_count: number;
};

export type KnowledgeDocumentDetail = {
  document: KnowledgeDocumentSummary;
  versions: {
    id: string;
    version_label: string;
    filename: string;
    media_type: string;
    size_bytes: number;
    content_hash: string;
    ingest_state: string;
    evidence_status: string;
    version_status: string;
    access_state: string;
    cloud_policy: string;
    ingested_at: string;
  }[];
  passages: {
    id: string;
    version_id: string;
    locator: Record<string, unknown>;
    text: string;
    content_hash: string;
    extraction_quality: Record<string, unknown>;
  }[];
  tables_count: number;
};

export type KnowledgeSearch = {
  snapshot_id: string;
  query: string;
  hits: {
    chunk_id: string;
    version_id: string;
    document_id: string;
    title: string;
    locator: Record<string, unknown>;
    excerpt: string;
    content_hash: string;
    extraction_quality: Record<string, unknown>;
    score: number;
  }[];
  permitted_version_ids: string[];
};

type UploadStatus = {
  session_id: string;
  filename: string;
  expected_bytes: number;
  received_bytes: number;
  chunk_size: number;
  received_ranges: [number, number][];
  state: string;
  expires_at: string;
};

type UploadCommit = {
  session_id: string;
  blob_id: string;
  document_id: string;
  version_id: string;
  job_id: string;
  ingest_state: string;
  duplicate_document_ids: string[];
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

let sessionPromise: Promise<void> | null = null;

export function notifyProjectChanged(): void {
  window.dispatchEvent(new Event("medical-one-project-changed"));
}

async function parseError(response: Response): Promise<Error> {
  const body = (await response.json().catch(() => null)) as
    | {
        detail?: { message?: string; code?: string } | string;
        message?: string;
        code?: string;
      }
    | null;
  const detail =
    typeof body?.detail === "string"
      ? body.detail
      : (body?.detail?.message ?? body?.message);
  return new Error(detail ?? `API 请求失败（HTTP ${response.status}）`);
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const hasBody = init?.body !== undefined;
  return fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
}

export async function ensureLocalSession(): Promise<void> {
  if (sessionPromise) return sessionPromise;
  sessionPromise = (async () => {
    const existing = await apiFetch("/api/v1/system/session");
    if (existing.ok) return;
    if (existing.status !== 401) throw await parseError(existing);
    const created = await apiFetch("/api/v1/system/local-session", {
      method: "POST",
    });
    if (!created.ok) throw await parseError(created);
  })().catch((error: unknown) => {
    sessionPromise = null;
    throw error;
  });
  return sessionPromise;
}

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  await ensureLocalSession();
  let response = await apiFetch(path, init);
  if (response.status === 401) {
    sessionPromise = null;
    await ensureLocalSession();
    response = await apiFetch(path, init);
  }
  return response;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authFetch(path, init);
  if (!response.ok) throw await parseError(response);
  return (await response.json()) as T;
}

export function fetchHealth(
  kind: "live" | "ready",
  signal?: AbortSignal,
): Promise<HealthReport> {
  return apiFetch(`/health/${kind}`, { signal }).then(async (response) => {
    if (!response.ok) throw await parseError(response);
    return (await response.json()) as HealthReport;
  });
}

export function fetchCapabilities(signal?: AbortSignal): Promise<CapabilityReport> {
  return apiFetch("/api/v1/system/capabilities", { signal }).then(async (response) => {
    if (!response.ok) throw await parseError(response);
    return (await response.json()) as CapabilityReport;
  });
}

export function runMockSmoke(input: string): Promise<MockSmokeResponse> {
  return request<MockSmokeResponse>("/api/v1/system/mock-smoke", {
    method: "POST",
    body: JSON.stringify({ input }),
  });
}

export async function fetchSession(signal?: AbortSignal): Promise<SessionView> {
  await ensureLocalSession();
  return request<SessionView>("/api/v1/system/session", { signal });
}

export function fetchProjects(signal?: AbortSignal): Promise<ProjectListItem[]> {
  return request<ProjectListItem[]>("/api/v1/projects", { signal });
}

export function fetchProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectSnapshot> {
  return request<ProjectSnapshot>(`/api/v1/projects/${projectId}`, { signal });
}

export function createProject(
  name: string,
  scope: string,
  idempotencyKey: string,
): Promise<ProjectSnapshot> {
  return request<ProjectSnapshot>("/api/v1/projects", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({ name, scope }),
  });
}

export function fetchOverview(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectOverview> {
  return request<ProjectOverview>(`/api/v1/projects/${projectId}/overview`, {
    signal,
  });
}

export function fetchProjectPolicy(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectPolicyView> {
  return request<ProjectPolicyView>(`/api/v1/projects/${projectId}/policy`, {
    signal,
  });
}

export function fetchTasks(
  projectId: string,
  signal?: AbortSignal,
): Promise<TaskView[]> {
  return request<TaskView[]>(`/api/v1/projects/${projectId}/tasks`, { signal });
}

export function reviseTaskInputs(
  projectId: string,
  taskId: string,
  payload: {
    expected_revision: number;
    input_version: string;
    input_refs: string[];
  },
): Promise<{
  task_id: string;
  state: string;
  input_validity: string;
  input_snapshot_sha256: string;
}> {
  return request<{
    task_id: string;
    state: string;
    input_validity: string;
    input_snapshot_sha256: string;
  }>(
    `/api/v1/projects/${projectId}/tasks/${taskId}/inputs`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function fetchAgents(
  projectId: string,
  signal?: AbortSignal,
): Promise<AgentScene[]> {
  return request<AgentScene[]>(`/api/v1/projects/${projectId}/agents`, {
    signal,
  });
}

export function fetchEvents(
  projectId: string,
  after = 0,
  limit = 100,
): Promise<ProjectEvent[]> {
  return request<ProjectEvent[]>(
    `/api/v1/projects/${projectId}/events?after=${after}&limit=${limit}`,
  );
}

export async function subscribeProjectEvents(
  projectId: string,
  after: number,
  onEvent: (event: ProjectEvent) => void,
): Promise<() => void> {
  await ensureLocalSession();
  const source = new EventSource(
    `${apiBaseUrl}/api/v1/projects/${projectId}/events/stream?after=${after}`,
    { withCredentials: true },
  );
  source.addEventListener("project-event", (message) => {
    const event = JSON.parse((message as MessageEvent<string>).data) as ProjectEvent;
    onEvent(event);
  });
  return () => source.close();
}

export function fetchOpportunities(
  projectId: string,
  signal?: AbortSignal,
): Promise<OpportunityView[]> {
  return request<OpportunityView[]>(
    `/api/v1/projects/${projectId}/opportunities`,
    { signal },
  );
}

export function selectOpportunity(
  projectId: string,
  opportunityId: string,
  expectedRevision: number,
  reason: string,
  scope: string,
  idempotencyKey: string,
): Promise<SelectionView> {
  return request<SelectionView>(
    `/api/v1/projects/${projectId}/opportunities/${opportunityId}/select`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        expected_revision: expectedRevision,
        reason,
        scope,
        evidence_version_ids: [],
      }),
    },
  );
}

export function fetchPlans(
  projectId: string,
  signal?: AbortSignal,
): Promise<PlanView[]> {
  return request<PlanView[]>(`/api/v1/projects/${projectId}/plans`, {
    signal,
  });
}

export function submitPlan(
  projectId: string,
  sourceDecisionId: string,
  spec: PlanSpecInput,
  idempotencyKey: string,
): Promise<PlanView> {
  return request<PlanView>(`/api/v1/projects/${projectId}/plans`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({
      source_decision_id: sourceDecisionId,
      spec,
    }),
  });
}

export function activatePlan(
  projectId: string,
  planId: string,
  expectedRevision: number,
): Promise<PlanView> {
  return request<PlanView>(
    `/api/v1/projects/${projectId}/plans/${planId}/activate`,
    {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    },
  );
}

export function dispatchPlan(
  projectId: string,
  planId: string,
  expectedRevision: number,
): Promise<PlanDispatchView> {
  return request<PlanDispatchView>(
    `/api/v1/projects/${projectId}/plans/${planId}/dispatch`,
    {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    },
  );
}

export function executePlan(
  projectId: string,
  planId: string,
  maxTasks = 4,
): Promise<PlanExecutionView> {
  return request<PlanExecutionView>(
    `/api/v1/projects/${projectId}/plans/${planId}/execute`,
    {
      method: "POST",
      body: JSON.stringify({ max_tasks: maxTasks }),
    },
  );
}

export function pausePlan(
  projectId: string,
  planId: string,
  expectedRevision: number,
  reason: string,
): Promise<PlanView> {
  return request<PlanView>(
    `/api/v1/projects/${projectId}/plans/${planId}/pause`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_revision: expectedRevision,
        reason,
      }),
    },
  );
}

export function resumePlan(
  projectId: string,
  planId: string,
  expectedRevision: number,
  additionalReworkRounds = 0,
): Promise<PlanView> {
  return request<PlanView>(
    `/api/v1/projects/${projectId}/plans/${planId}/resume`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_revision: expectedRevision,
        additional_rework_rounds: additionalReworkRounds,
      }),
    },
  );
}

export function stopPlan(
  projectId: string,
  planId: string,
  expectedRevision: number,
  reason: string,
): Promise<PlanView> {
  return request<PlanView>(
    `/api/v1/projects/${projectId}/plans/${planId}/stop`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_revision: expectedRevision,
        reason,
      }),
    },
  );
}

export function reviewTask(
  projectId: string,
  taskId: string,
  review: {
    planId: string;
    expectedRevision: number;
    reviewerRole: string;
    decision: ReviewDecision;
    summary: string;
    findings: ReviewFinding[];
  },
  idempotencyKey: string,
): Promise<TaskReviewView> {
  return request<TaskReviewView>(
    `/api/v1/projects/${projectId}/tasks/${taskId}/review`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        plan_id: review.planId,
        expected_revision: review.expectedRevision,
        reviewer_role: review.reviewerRole,
        decision: review.decision,
        summary: review.summary,
        findings: review.findings,
      }),
    },
  );
}

export function fetchProjectWorkflows(
  projectId: string,
  signal?: AbortSignal,
): Promise<WorkflowDescriptor[]> {
  return request<WorkflowDescriptor[]>(
    `/api/v1/projects/${projectId}/workflows`,
    { signal },
  );
}

export function fetchWorkflowAssessments(
  projectId: string,
  track?: string,
  signal?: AbortSignal,
): Promise<StageAssessmentView[]> {
  const suffix = track ? `?track=${encodeURIComponent(track)}` : "";
  return request<StageAssessmentView[]>(
    `/api/v1/projects/${projectId}/workflow-assessments${suffix}`,
    { signal },
  );
}

export function assessWorkflowStage(
  projectId: string,
  track: string,
  stageId: string,
  criterionResults: CriterionResult[],
  rationale: string,
): Promise<StageAssessmentView> {
  return request<StageAssessmentView>(
    `/api/v1/projects/${projectId}/workflows/${track}/stages/${stageId}/assessments`,
    {
      method: "POST",
      body: JSON.stringify({
        criterion_results: criterionResults,
        rationale,
      }),
    },
  );
}

export function decideWorkflowStage(
  projectId: string,
  assessmentId: string,
  decision: "accepted" | "changes_requested" | "blocked",
  reviewerRole: string,
  reason: string,
): Promise<StageAssessmentView> {
  return request<StageAssessmentView>(
    `/api/v1/projects/${projectId}/workflow-assessments/${assessmentId}/decision`,
    {
      method: "POST",
      body: JSON.stringify({
        decision,
        reviewer_role: reviewerRole,
        reason,
      }),
    },
  );
}

export function createWorkflowStagePlan(
  projectId: string,
  track: string,
  stageId: string,
  sourceDecisionId: string,
  idempotencyKey: string,
): Promise<PlanView> {
  return request<PlanView>(
    `/api/v1/projects/${projectId}/workflows/${track}/stages/${stageId}/plans`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ source_decision_id: sourceDecisionId }),
    },
  );
}

export function fetchDatasets(
  projectId: string,
  signal?: AbortSignal,
): Promise<DatasetView[]> {
  return request<DatasetView[]>(`/api/v1/projects/${projectId}/datasets`, {
    signal,
  });
}

export function importDataset(
  projectId: string,
  payload: {
    documentVersionId: string;
    title: string;
    sourceLabel: string;
    synthetic: boolean;
    sheetName: string | null;
  },
  idempotencyKey: string,
): Promise<DatasetView> {
  return request<DatasetView>(`/api/v1/projects/${projectId}/datasets/import`, {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify({
      document_version_id: payload.documentVersionId,
      title: payload.title,
      source_label: payload.sourceLabel,
      synthetic: payload.synthetic,
      sheet_name: payload.sheetName,
    }),
  });
}

export function deriveDatasetVersion(
  projectId: string,
  datasetId: string,
  parentVersionId: string,
  spec: {
    select_columns: string[];
    numeric_columns: string[];
    rename_columns: Record<string, string>;
    drop_missing_columns: string[];
    rationale: string;
  },
  idempotencyKey: string,
): Promise<DatasetView> {
  return request<DatasetView>(
    `/api/v1/projects/${projectId}/datasets/${datasetId}/versions`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        parent_version_id: parentVersionId,
        spec,
      }),
    },
  );
}

export function createStatisticalPlan(
  projectId: string,
  versionId: string,
  spec: StatisticalPlanSpecInput,
  idempotencyKey: string,
): Promise<StatisticalPlanView> {
  return request<StatisticalPlanView>(
    `/api/v1/projects/${projectId}/dataset-versions/${versionId}/statistical-plans`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ spec }),
    },
  );
}

export function runStatisticalAnalysis(
  projectId: string,
  planId: string,
  idempotencyKey: string,
): Promise<AnalysisRunView> {
  return request<AnalysisRunView>(
    `/api/v1/projects/${projectId}/statistical-plans/${planId}/run`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
    },
  );
}

export function fetchDatasetAnalyses(
  projectId: string,
  versionId: string,
  signal?: AbortSignal,
): Promise<AnalysisRunView[]> {
  return request<AnalysisRunView[]>(
    `/api/v1/projects/${projectId}/dataset-versions/${versionId}/analyses`,
    { signal },
  );
}

export function reviewAnalysis(
  projectId: string,
  analysisId: string,
  payload: {
    reviewerRole: string;
    decision: ReviewDecision;
    summary: string;
    findings: ReviewFinding[];
  },
  idempotencyKey: string,
): Promise<AnalysisReviewView> {
  return request<AnalysisReviewView>(
    `/api/v1/projects/${projectId}/analyses/${analysisId}/review`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        reviewer_role: payload.reviewerRole,
        decision: payload.decision,
        summary: payload.summary,
        findings: payload.findings,
      }),
    },
  );
}

export function fetchArtifactExports(
  projectId: string,
  signal?: AbortSignal,
): Promise<ArtifactExportView[]> {
  return request<ArtifactExportView[]>(
    `/api/v1/projects/${projectId}/artifact-exports`,
    { signal },
  );
}

export function fetchArtifactExportRuntime(
  projectId: string,
  signal?: AbortSignal,
): Promise<ArtifactExportRuntime> {
  return request<ArtifactExportRuntime>(
    `/api/v1/projects/${projectId}/artifact-exports/runtime`,
    { signal },
  );
}

export function createArtifactExport(
  projectId: string,
  payload: {
    analysisId: string;
    format: ArtifactExportFormat;
    templateId: string | null;
    title: string | null;
  },
  idempotencyKey: string,
): Promise<ArtifactExportView> {
  return request<ArtifactExportView>(
    `/api/v1/projects/${projectId}/artifact-exports`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        analysis_id: payload.analysisId,
        format: payload.format,
        template_id: payload.templateId,
        title: payload.title,
      }),
    },
  );
}

export async function downloadArtifactExport(
  projectId: string,
  exportId: string,
  filename: string,
): Promise<void> {
  const response = await authFetch(
    `/api/v1/projects/${projectId}/artifact-exports/${exportId}/download`,
  );
  if (!response.ok) throw await parseError(response);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function fetchArtifactPreview(
  projectId: string,
  exportId: string,
  kind: "png" | "pdf",
): Promise<string> {
  const response = await authFetch(
    `/api/v1/projects/${projectId}/artifact-exports/${exportId}/preview.${kind}`,
  );
  if (!response.ok) throw await parseError(response);
  return URL.createObjectURL(await response.blob());
}

export function fetchMailAccount(
  projectId: string,
  signal?: AbortSignal,
): Promise<MailAccountView> {
  return request<MailAccountView>(
    `/api/v1/projects/${projectId}/mail/account`,
    { signal },
  );
}

export function syncMockInbox(
  projectId: string,
): Promise<MailThreadView[]> {
  return request<MailThreadView[]>(
    `/api/v1/projects/${projectId}/mail/inbox/sync-mock`,
    { method: "POST" },
  );
}

export function fetchMailThreads(
  projectId: string,
  signal?: AbortSignal,
): Promise<MailThreadView[]> {
  return request<MailThreadView[]>(
    `/api/v1/projects/${projectId}/mail/threads`,
    { signal },
  );
}

export function linkMailThread(
  projectId: string,
  threadId: string,
  expectedRevision: number,
): Promise<MailThreadView> {
  return request<MailThreadView>(
    `/api/v1/projects/${projectId}/mail/threads/${threadId}/link`,
    {
      method: "POST",
      headers: { "X-Expected-Revision": String(expectedRevision) },
    },
  );
}

export function fetchMailDrafts(
  projectId: string,
  signal?: AbortSignal,
): Promise<MailDraftView[]> {
  return request<MailDraftView[]>(
    `/api/v1/projects/${projectId}/mail/drafts`,
    { signal },
  );
}

export function createMailDraft(
  projectId: string,
  payload: {
    toAddresses: string[];
    subject: string;
    bodyText: string;
    attachmentIds: string[];
    threadId: string | null;
  },
  idempotencyKey: string,
): Promise<MailDraftView> {
  return request<MailDraftView>(
    `/api/v1/projects/${projectId}/mail/drafts`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        to_addresses: payload.toAddresses,
        cc_addresses: [],
        bcc_addresses: [],
        subject: payload.subject,
        body_text: payload.bodyText,
        attachments: payload.attachmentIds.map((sourceId) => ({
          source_type: "artifact_version",
          source_id: sourceId,
        })),
        thread_id: payload.threadId,
      }),
    },
  );
}

export function fetchMailAuthorizations(
  projectId: string,
  draftId: string,
  signal?: AbortSignal,
): Promise<MailAuthorizationView[]> {
  return request<MailAuthorizationView[]>(
    `/api/v1/projects/${projectId}/mail/drafts/${draftId}/authorizations`,
    { signal },
  );
}

export function authorizeMailDraft(
  projectId: string,
  draftId: string,
  idempotencyKey: string,
): Promise<MailAuthorizationView> {
  return request<MailAuthorizationView>(
    `/api/v1/projects/${projectId}/mail/drafts/${draftId}/authorizations`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        spec: { expires_in_minutes: 30, max_sends: 1 },
      }),
    },
  );
}

export function revokeMailAuthorization(
  projectId: string,
  authorizationId: string,
): Promise<MailAuthorizationView> {
  return request<MailAuthorizationView>(
    `/api/v1/projects/${projectId}/mail/authorizations/${authorizationId}/revoke`,
    { method: "POST" },
  );
}

export function sendMailDraft(
  projectId: string,
  draftId: string,
  authorizationId: string,
  idempotencyKey: string,
): Promise<MailSendResultView> {
  return request<MailSendResultView>(
    `/api/v1/projects/${projectId}/mail/drafts/${draftId}/send`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ authorization_id: authorizationId }),
    },
  );
}

export function fetchMailAttempts(
  projectId: string,
  signal?: AbortSignal,
): Promise<MailAttemptView[]> {
  return request<MailAttemptView[]>(
    `/api/v1/projects/${projectId}/mail/attempts`,
    { signal },
  );
}

export function reconcileMailSend(
  projectId: string,
  attemptId: string,
): Promise<MailSendResultView> {
  return request<MailSendResultView>(
    `/api/v1/projects/${projectId}/mail/attempts/${attemptId}/reconcile`,
    { method: "POST" },
  );
}

export function fetchExternalWorkspace(
  projectId: string,
  signal?: AbortSignal,
): Promise<ExternalWorkspaceView> {
  return request<ExternalWorkspaceView>(
    `/api/v1/projects/${projectId}/external`,
    { signal },
  );
}

export function createExternalOrganization(
  projectId: string,
  spec: {
    name: string;
    provider_type: ProviderType;
    capability_summary: string;
    source_refs: string[];
    verification_state: "candidate" | "contacted" | "verified" | "rejected";
  },
  idempotencyKey: string,
): Promise<ExternalOrganizationView> {
  return request<ExternalOrganizationView>(
    `/api/v1/projects/${projectId}/external/organizations`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function createExternalContact(
  projectId: string,
  spec: {
    organization_id: string;
    name: string;
    role: string;
    email: string | null;
    source_refs: string[];
    verification_state: "candidate" | "contacted" | "verified" | "rejected";
  },
): Promise<ExternalContactView> {
  return request<ExternalContactView>(
    `/api/v1/projects/${projectId}/external/contacts`,
    { method: "POST", body: JSON.stringify(spec) },
  );
}

export function createExternalExpert(
  projectId: string,
  spec: {
    name: string;
    expertise: string;
    public_source_refs: string[];
    contact_email: string | null;
    conflict_notes: string;
    state: "candidate" | "contacted" | "replied" | "limited_review" | "engaged" | "declined";
  },
  idempotencyKey: string,
): Promise<ExternalExpertView> {
  return request<ExternalExpertView>(
    `/api/v1/projects/${projectId}/external/experts`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function createExternalEngagement(
  projectId: string,
  spec: {
    organization_id: string;
    title: string;
    scope: ExternalEngagementView["scope"];
  },
  idempotencyKey: string,
): Promise<ExternalEngagementView> {
  return request<ExternalEngagementView>(
    `/api/v1/projects/${projectId}/external/engagements`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function transitionExternalEngagement(
  projectId: string,
  engagementId: string,
  expectedRevision: number,
  state: string,
): Promise<ExternalEngagementView> {
  return request<ExternalEngagementView>(
    `/api/v1/projects/${projectId}/external/engagements/${engagementId}/state`,
    {
      method: "PUT",
      body: JSON.stringify({ expected_revision: expectedRevision, state }),
    },
  );
}

export function createExternalQuote(
  projectId: string,
  spec: {
    engagement_id: string;
    amount: string | null;
    currency: string;
    tax_included: boolean | null;
    shipping_included: boolean | null;
    assumptions: string[];
    excluded_work: string[];
    valid_until: string | null;
    document_version_id: string | null;
    state: "received" | "accepted" | "rejected" | "expired";
  },
  idempotencyKey: string,
): Promise<ExternalQuoteView> {
  return request<ExternalQuoteView>(
    `/api/v1/projects/${projectId}/external/quotes`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function fetchQuoteComparison(
  projectId: string,
  engagementId: string,
  signal?: AbortSignal,
): Promise<QuoteComparisonView> {
  return request<QuoteComparisonView>(
    `/api/v1/projects/${projectId}/external/engagements/${engagementId}/quote-comparison`,
    { signal },
  );
}

export function createExternalContract(
  projectId: string,
  spec: {
    engagement_id: string;
    quote_id: string | null;
    title: string;
    terms_summary: string;
    document_version_id: string | null;
    state: "draft";
  },
  idempotencyKey: string,
): Promise<ExternalContractView> {
  return request<ExternalContractView>(
    `/api/v1/projects/${projectId}/external/contracts`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function transitionExternalContract(
  projectId: string,
  contractId: string,
  payload: {
    expected_revision: number;
    state: string;
    internal_signed: boolean;
    external_signed: boolean;
    document_version_id: string | null;
    reason: string;
  },
): Promise<ExternalContractView> {
  return request<ExternalContractView>(
    `/api/v1/projects/${projectId}/external/contracts/${contractId}/state`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
}

export function createExternalDeliverable(
  projectId: string,
  spec: {
    engagement_id: string;
    title: string;
    kind: string;
    expected_items: string[];
    due_at: string | null;
  },
  idempotencyKey: string,
): Promise<ExternalDeliverableView> {
  return request<ExternalDeliverableView>(
    `/api/v1/projects/${projectId}/external/deliverables`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function receiveExternalDeliverable(
  projectId: string,
  deliverableId: string,
  payload: {
    expected_revision: number;
    knowledge_version_id: string;
    manifest: Record<string, unknown>;
    missing_items: string[];
    summary: string;
  },
): Promise<ExternalDeliverableView> {
  return request<ExternalDeliverableView>(
    `/api/v1/projects/${projectId}/external/deliverables/${deliverableId}/receive`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function reviewExternalDeliverable(
  projectId: string,
  deliverableId: string,
  payload: {
    expected_revision: number;
    decision: "accepted" | "rejected";
    reviewer_role: "A25" | "A26";
    summary: string;
    findings: string[];
    missing_items: string[];
  },
): Promise<ExternalDeliverableView> {
  return request<ExternalDeliverableView>(
    `/api/v1/projects/${projectId}/external/deliverables/${deliverableId}/review`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function fetchAuditWorkspace(
  projectId: string,
  signal?: AbortSignal,
): Promise<AuditWorkspaceView> {
  return request<AuditWorkspaceView>(
    `/api/v1/projects/${projectId}/audits`,
    { signal },
  );
}

export function createAuditReview(
  projectId: string,
  payload: {
    target_type: AuditTargetType;
    target_id: string;
    reviewer_role: "A25" | "A26";
    producer_role: string | null;
    linked_task_id?: string | null;
  },
  idempotencyKey: string,
): Promise<AuditRunView> {
  return request<AuditRunView>(
    `/api/v1/projects/${projectId}/audits`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(payload),
    },
  );
}

export function resolveAuditFinding(
  projectId: string,
  auditId: string,
  findingId: string,
  payload: {
    status: "resolved" | "accepted_risk";
    resolution: string;
  },
): Promise<AuditFindingView> {
  return request<AuditFindingView>(
    (
      `/api/v1/projects/${projectId}/audits/${auditId}/findings/`
      + `${findingId}/disposition`
    ),
    { method: "POST", body: JSON.stringify(payload) },
  );
}

export function runAuditEvaluation(
  projectId: string,
): Promise<AuditEvaluationView> {
  return request<AuditEvaluationView>(
    `/api/v1/projects/${projectId}/audits/evaluate`,
    { method: "POST" },
  );
}

export function fetchRecoveryWorkspace(
  projectId: string,
  signal?: AbortSignal,
): Promise<RecoveryWorkspaceView> {
  return request<RecoveryWorkspaceView>(
    `/api/v1/projects/${projectId}/recovery`,
    { signal },
  );
}

export function trashKnowledgeDocument(
  projectId: string,
  documentId: string,
  reason: string,
): Promise<TrashEntryView> {
  return request<TrashEntryView>(
    `/api/v1/projects/${projectId}/recovery/trash/${documentId}`,
    { method: "POST", body: JSON.stringify({ reason }) },
  );
}

export function restoreKnowledgeDocument(
  projectId: string,
  documentId: string,
): Promise<TrashEntryView> {
  return request<TrashEntryView>(
    `/api/v1/projects/${projectId}/recovery/trash/${documentId}/restore`,
    { method: "POST" },
  );
}

export function rebuildKnowledgeIndex(
  projectId: string,
  versionId: string,
): Promise<IndexRebuildView> {
  return request<IndexRebuildView>(
    `/api/v1/projects/${projectId}/recovery/versions/${versionId}/rebuild-index`,
    { method: "POST" },
  );
}

export function createEncryptedBackup(
  projectId: string,
  passphrase: string,
  idempotencyKey: string,
): Promise<BackupView> {
  return request<BackupView>(
    `/api/v1/projects/${projectId}/recovery/backups`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ passphrase }),
    },
  );
}

export function runRestoreCheck(
  projectId: string,
  backupId: string,
  passphrase: string,
): Promise<RestoreCheckView> {
  return request<RestoreCheckView>(
    `/api/v1/projects/${projectId}/recovery/backups/${backupId}/restore-check`,
    { method: "POST", body: JSON.stringify({ passphrase }) },
  );
}

export function createProfessionalRecord(
  projectId: string,
  spec: Record<string, unknown>,
  idempotencyKey: string,
): Promise<ProfessionalRecordView> {
  return request<ProfessionalRecordView>(
    `/api/v1/projects/${projectId}/external/professional-records`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function createExternalAuthorization(
  projectId: string,
  spec: {
    engagement_id: string;
    action_scope: string;
    amount_max: string;
    currency: string;
    expires_at: string;
  },
  idempotencyKey: string,
): Promise<ExternalAuthorizationView> {
  return request<ExternalAuthorizationView>(
    `/api/v1/projects/${projectId}/external/authorizations`,
    {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(spec),
    },
  );
}

export function revokeExternalAuthorization(
  projectId: string,
  authorizationId: string,
): Promise<ExternalAuthorizationView> {
  return request<ExternalAuthorizationView>(
    `/api/v1/projects/${projectId}/external/authorizations/${authorizationId}/revoke`,
    { method: "POST" },
  );
}

export function fetchKnowledgeDocuments(
  projectId: string,
  query = "",
  signal?: AbortSignal,
): Promise<KnowledgeDocumentSummary[]> {
  const suffix = query.trim()
    ? `?q=${encodeURIComponent(query.trim())}`
    : "";
  return request<KnowledgeDocumentSummary[]>(
    `/api/v1/projects/${projectId}/knowledge/documents${suffix}`,
    { signal },
  );
}

export function fetchKnowledgeDocument(
  projectId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<KnowledgeDocumentDetail> {
  return request<KnowledgeDocumentDetail>(
    `/api/v1/projects/${projectId}/knowledge/documents/${documentId}`,
    { signal },
  );
}

export function searchKnowledge(
  projectId: string,
  taskId: string,
  query: string,
): Promise<KnowledgeSearch> {
  return request<KnowledgeSearch>(
    `/api/v1/projects/${projectId}/knowledge/search`,
    {
      method: "POST",
      body: JSON.stringify({ task_id: taskId, query }),
    },
  );
}

export async function uploadKnowledgeFile(
  projectId: string,
  file: File,
  batchReservedBytes: number,
  onProgress: (value: number) => void,
): Promise<UploadCommit> {
  const wholeHash = await sha256(await file.arrayBuffer());
  const started = await request<UploadStatus>(
    `/api/v1/projects/${projectId}/knowledge/uploads`,
    {
      method: "POST",
      body: JSON.stringify({
        filename: file.name,
        expected_bytes: file.size,
        media_type_hint: file.type || null,
        expected_sha256: wholeHash,
        batch_reserved_bytes: batchReservedBytes,
      }),
    },
  );
  let offset = 0;
  while (offset < file.size) {
    const end = Math.min(offset + started.chunk_size, file.size);
    const chunk = file.slice(offset, end);
    const chunkHash = await sha256(await chunk.arrayBuffer());
    const response = await authFetch(
      `/api/v1/projects/${projectId}/knowledge/uploads/${started.session_id}/parts/${offset}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/octet-stream",
          "X-Part-SHA256": chunkHash,
        },
        body: chunk,
      },
    );
    if (!response.ok) throw await parseError(response);
    offset = end;
    onProgress(end / file.size);
  }
  const committed = await request<UploadCommit>(
    `/api/v1/projects/${projectId}/knowledge/uploads/${started.session_id}/commit`,
    { method: "POST" },
  );
  onProgress(1);
  return committed;
}

export async function downloadKnowledgeVersion(
  projectId: string,
  versionId: string,
  filename: string,
): Promise<void> {
  const response = await authFetch(
    `/api/v1/projects/${projectId}/knowledge/versions/${versionId}/download`,
  );
  if (!response.ok) throw await parseError(response);
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function sha256(content: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", content);
  return Array.from(new Uint8Array(digest))
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}
