import { expect, test, type APIRequestContext } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

type Scope = {
  id: string;
  code: string;
  sites: { id: string; code: string; name: string }[];
};

const API_BASE = process.env.CRA_E2E_API_URL ?? "http://127.0.0.1:8000";
const ROOT = resolve(process.cwd(), "..");

function artifact(relative: string): Buffer {
  return readFileSync(resolve(ROOT, relative));
}

async function loginApi(request: APIRequestContext): Promise<string> {
  const login = await request.post(`${API_BASE}/api/v1/auth/synthetic/session`);
  expect(login.ok()).toBeTruthy();
  const state = await request.storageState();
  const csrf = state.cookies.find((item) => item.name === "cra_csrf")?.value;
  expect(csrf).toBeTruthy();
  return csrf!;
}

async function uploadDocument(
  request: APIRequestContext,
  csrf: string,
  values: {
    studyId: string;
    siteId: string;
    idempotencyKey: string;
    title: string;
    purpose: string;
    documentType: string;
    filename: string;
    mediaType: string;
    content: Buffer;
  }
) {
  const response = await request.post(
    `${API_BASE}/api/v1/studies/${values.studyId}/documents`,
    {
      headers: {
        "X-CSRF-Token": csrf,
        "Idempotency-Key": values.idempotencyKey
      },
      multipart: {
        file: {
          name: values.filename,
          mimeType: values.mediaType,
          buffer: values.content
        },
        title: values.title,
        document_type: values.documentType,
        purpose: values.purpose,
        version_label: "v1",
        expected_revision: "0",
        site_id: values.siteId
      }
    }
  );
  expect(response.status()).toBe(202);
  return response.json();
}

async function createMapping(
  request: APIRequestContext,
  csrf: string,
  versionId: string,
  kind: "letter" | "report" | "track"
) {
  const fields = {
    study_code: "study_code",
    site_code: "site_code",
    site_name: "site_name",
    visit_title: "visit_title",
    generated_on: "generated_on",
    visit_scope_note: "visit_scope_note",
    coverage_summary: "coverage_summary",
    not_checked_summary: "not_checked_summary",
    next_steps_summary: "next_steps_summary",
    user_summary: "user_summary",
    user_conclusion: "user_conclusion"
  };
  const mapping =
    kind === "track"
      ? {
          output_kind: kind,
          output_format: "xlsx",
          xlsx: {
            cells: {},
            table: {
              sheet: "Track",
              start_row: 2,
              columns: {
                A: "issue_number",
                B: "section",
                C: "original_finding",
                D: "location",
                E: "recommendation",
                F: "status",
                G: "known_progress",
                H: "next_steps_text",
                I: "source_refs_text"
              }
            },
            required_variables: []
          }
        }
      : {
          output_kind: kind,
          output_format: "docx",
          docx: {
            fields,
            loops:
              kind === "letter"
                ? { letter_issues: "letter_issues" }
                : {
                    prior_issues: "prior_issues",
                    current_findings: "current_findings"
                  },
            required_variables:
              kind === "letter"
                ? ["study_code"]
                : ["study_code", "user_summary", "user_conclusion"]
          }
        };
  const response = await request.post(`${API_BASE}/api/v1/template-versions`, {
    headers: {
      "X-CSRF-Token": csrf,
      "Idempotency-Key": `w12-template-${kind}`
    },
    data: {
      expected_revision: 0,
      idempotency_key: `w12-template-${kind}`,
      source_document_version_id: versionId,
      title: `Synthetic W12 ${kind} template`,
      mapping
    }
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

test("two monitoring cycles survive refresh, relogin and device change", async ({
  page,
  browser,
  request
}) => {
  const csrf = await loginApi(request);
  const scopesResponse = await request.get(`${API_BASE}/api/v1/me/scopes`);
  expect(scopesResponse.ok()).toBeTruthy();
  const scopes = (await scopesResponse.json()) as { studies: Scope[] };
  const study = scopes.studies.find((item) => item.code === "W12-E2E");
  expect(study).toBeTruthy();
  const siteA = study!.sites.find((item) => item.code === "E12A");
  expect(siteA).toBeTruthy();

  const subjectResponse = await request.post(
    `${API_BASE}/api/v1/studies/${study!.id}/subjects`,
    {
      headers: { "X-CSRF-Token": csrf },
      data: {
        expected_revision: 0,
        idempotency_key: "w12-e2e-subject",
        site_id: siteA!.id,
        external_id: "SYN-EDC-001",
        identity_namespace: "edc",
        deidentified_label: "Synthetic E2E Subject"
      }
    }
  );
  expect(subjectResponse.ok()).toBeTruthy();
  const subject = await subjectResponse.json();

  const trackUpload = await uploadDocument(request, csrf, {
    studyId: study!.id,
    siteId: siteA!.id,
    idempotencyKey: "w12-e2e-carryover-track",
    title: "Synthetic previous track",
    purpose: "track",
    documentType: "track",
    filename: "synthetic_carryover_track.xlsx",
    mediaType:
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    content: artifact("tests/fixtures/issues/artifacts/synthetic_carryover_track.xlsx")
  });
  const carryPreview = await request.post(
    `${API_BASE}/api/v1/document-versions/${trackUpload.document_version_id}/carryover-imports/preview`,
    {
      headers: { "X-CSRF-Token": csrf },
      data: {
        expected_revision: 0,
        idempotency_key: "w12-e2e-carryover-preview",
        site_id: siteA!.id
      }
    }
  );
  expect(carryPreview.ok()).toBeTruthy();
  const carryBody = await carryPreview.json();
  const carryConfirm = await request.post(
    `${API_BASE}/api/v1/carryover-imports/${carryBody.import_record.id}/confirm`,
    {
      headers: { "X-CSRF-Token": csrf },
      data: {
        expected_revision: carryBody.import_record.revision,
        idempotency_key: "w12-e2e-carryover-confirm",
        corrections: []
      }
    }
  );
  expect(carryConfirm.ok()).toBeTruthy();

  const urgent = await request.post(
    `${API_BASE}/api/v1/studies/${study!.id}/issues`,
    {
      headers: { "X-CSRF-Token": csrf },
      data: {
        expected_revision: 0,
        idempotency_key: "w12-e2e-urgent-issue",
        site_id: siteA!.id,
        issue_number: "E2E-URGENT",
        original_finding: "Synthetic urgent PD and correction follow-up.",
        location: "Synthetic E2E source",
        known_progress: "Open at the previous synthetic visit.",
        source_kind: "manual",
        source_refs: [{ locator: "Synthetic E2E track row" }],
        actions: [
          {
            action_key: "PD",
            kind: "pd_reporting",
            requirement: "Confirm synthetic PD reporting."
          },
          {
            action_key: "CORRECT",
            kind: "edc_correction",
            requirement: "Correct the synthetic EDC value."
          }
        ]
      }
    }
  );
  expect(urgent.ok()).toBeTruthy();

  const edcPreview = await request.post(
    `${API_BASE}/api/v1/studies/${study!.id}/edc-imports/preview`,
    {
      headers: {
        "X-CSRF-Token": csrf,
        "Idempotency-Key": "w12-e2e-edc-preview"
      },
      multipart: {
        file: {
          name: "synthetic_edc_lab.xlsx",
          mimeType:
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          buffer: artifact("tests/fixtures/edc/artifacts/synthetic_edc_lab.xlsx")
        },
        site_id: siteA!.id,
        title: "Synthetic E2E EDC export",
        export_started_at: "2026-01-03T08:00:00+00:00",
        export_completed_at: "2026-01-03T08:05:00+00:00",
        export_scope_json: JSON.stringify({
          status: "declared",
          forms: ["Hematology", "Chemistry"],
          subjects: ["SYN-EDC-001"],
          sites: ["E12A"],
          date_start: "2026-01-01",
          date_end: "2026-01-03",
          filters: {},
          declared_complete: false,
          note: "Synthetic browser E2E export."
        }),
        included_sheets_json: JSON.stringify(["Hematology", "Chemistry"]),
        identity_namespace: "edc"
      }
    }
  );
  expect(edcPreview.ok()).toBeTruthy();
  const edcBody = await edcPreview.json();
  const mapping = {
    sheets: {
      Hematology: {
        header_row: 1,
        data_start_row: 2,
        columns: {
          subject_external_id: "Subject ID",
          visit_key: "Visit",
          analyte: "Analyte",
          value_raw: "Result",
          unit: "Unit",
          collected_on: "Collection Date",
          collected_at: "Collection Time",
          instance_type: "Instance",
          repeat_instance: "Repeat No",
          report_on: "Report Date",
          specimen: "Specimen",
          lower_limit: "LLN",
          upper_limit: "ULN"
        },
        included: true
      },
      Chemistry: {
        header_row: 1,
        data_start_row: 2,
        columns: {
          subject_external_id: "Subject ID",
          visit_key: "Visit",
          analyte: "Analyte",
          value_raw: "Result",
          unit: "Unit",
          collected_on: "Collection Date",
          collected_at: "Collection Time",
          instance_type: "Instance",
          repeat_instance: "Repeat No",
          report_on: "Report Date",
          specimen: "Specimen",
          lower_limit: "LLN",
          upper_limit: "ULN"
        },
        included: true
      }
    }
  };
  const edcConfirm = await request.post(
    `${API_BASE}/api/v1/edc-imports/${edcBody.id}/confirm`,
    {
      headers: { "X-CSRF-Token": csrf },
      data: {
        expected_revision: edcBody.revision,
        idempotency_key: "w12-e2e-edc-confirm",
        mapping,
        identity_namespace: "edc"
      }
    }
  );
  expect(edcConfirm.ok()).toBeTruthy();

  const safety = await request.post(`${API_BASE}/api/v1/safety-assessments`, {
    headers: { "X-CSRF-Token": csrf },
    data: {
      expected_revision: 0,
      idempotency_key: "w12-e2e-safety",
      study_id: study!.id,
      site_id: siteA!.id,
      subject_id: subject.id,
      event_type: "protocol_deviation",
      event_date: "2026-01-03",
      requested_dimensions: ["protocol_deviation", "reporting_timeliness"],
      related_fact_ids: []
    }
  });
  expect(safety.ok()).toBeTruthy();

  for (const kind of ["report", "track"] as const) {
    const file =
      kind === "report"
        ? "synthetic_monitoring_report.docx"
        : "synthetic_track_template.xlsx";
    const upload = await uploadDocument(request, csrf, {
      studyId: study!.id,
      siteId: siteA!.id,
      idempotencyKey: `w12-e2e-${kind}-template`,
      title: `Synthetic W12 ${kind} template`,
      purpose: "template",
      documentType: "template",
      filename: file,
      mediaType:
        kind === "report"
          ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      content: artifact(`tests/fixtures/reports/artifacts/${file}`)
    });
    await createMapping(request, csrf, upload.document_version_id, kind);
  }

  await page.goto("/");
  const loginButton = page.getByRole("button", { name: "进入合成工作台" });
  if (await loginButton.isVisible().catch(() => false)) {
    await loginButton.click();
  }
  await page.locator(".selector-panel select").nth(0).selectOption(study!.id);
  await page.locator(".selector-panel select").nth(1).selectOption(siteA!.id);
  await expect(page.getByRole("heading", { name: "从访前遗留开始，逐患者核查，最后生成报告" })).toBeVisible();
  await page.getByRole("button", { name: "开始本次监查" }).click();
  await expect(page.locator(".previsit-options")).toBeVisible();

  for (const issueNumber of ["CRA-SYN-101", "E2E-URGENT"]) {
    const option = page
      .locator(".previsit-options label")
      .filter({ hasText: issueNumber });
    await option.locator('input[type="checkbox"]').check();
  }
  await page.getByRole("button", { name: "保存访前选择" }).click();
  await expect(page.getByText("访前选择已保存")).toBeVisible();
  await page.getByTestId("stage-carryover_review").click();

  const urgentSummary = page
    .locator(".carryover-summary")
    .filter({ hasText: "E2E-URGENT" });
  await urgentSummary.click();
  await page
    .getByRole("button", { name: "CRA确认PD已上报" })
    .evaluate((button) => (button as HTMLButtonElement).click());
  await expect(urgentSummary).toContainText("部分完成");
  const urgentSummaryAfterPd = page
    .locator(".carryover-summary")
    .filter({ hasText: "E2E-URGENT" });
  if ((await urgentSummaryAfterPd.getAttribute("aria-expanded")) !== "true") {
    await urgentSummaryAfterPd.click();
  }
  await expect(urgentSummaryAfterPd).toHaveAttribute("aria-expanded", "true");
  await page
    .getByRole("button", { name: "CRA确认已整改" })
    .evaluate((button) => (button as HTMLButtonElement).click());
  await expect(
    page.locator(".carryover-summary").filter({ hasText: "E2E-URGENT" })
  ).toHaveCount(0);

  await page.getByTestId("stage-subject_review").click();
  await expect(page.getByRole("heading", { name: "分层list、源文件与EDC在同一患者上下文接续" })).toBeVisible();
  await page.getByRole("button", { name: "EDC检验快照" }).click();
  await expect(page.getByRole("heading", { name: "导出范围、映射与原始行" })).toBeVisible();

  await page.getByTestId("stage-handover").click();
  await expect(page.getByRole("heading", { name: "同一记录生成多份材料" })).toBeVisible();
  await page.getByRole("button", { name: "生成监查报告草稿" }).click();
  await expect(page.getByText("监查报告草稿已从同一问题")).toBeVisible();
  await page.getByLabel("CRA说明").fill("Synthetic E2E CRA summary.");
  await page.getByLabel("结论").fill("Only the documented synthetic scope is covered.");
  await page.getByRole("button", { name: "保存文案并标记可审阅" }).click();
  await page.getByLabel("状态").selectOption("issued");
  await page.getByLabel("用户声明").fill("CRA confirms synthetic report issuance.");
  await page.getByText("已看到 unknown/未核查范围").click();
  await page.getByRole("button", { name: "生成不可变快照" }).click();
  await expect(page.getByRole("heading", { name: "已签发" })).toBeVisible();
  await page.getByRole("button", { name: "导出 Excel Track" }).click();
  await expect(page.locator(".report-download")).toBeVisible();

  await page.getByRole("button", { name: "开始下一次监查" }).click();
  await page.getByLabel("监查标题").fill("Synthetic second E2E visit");
  await page.getByRole("button", { name: "建立下一次监查" }).click();
  await expect(page.getByRole("heading", { name: "Synthetic second E2E visit" })).toBeVisible();
  await page.getByTestId("stage-carryover_review").click();
  await expect(
    page.locator(".carryover-summary").filter({ hasText: "CRA-SYN-101" })
  ).toBeVisible();

  await page.evaluate(() => window.localStorage.clear());
  await page.reload();
  await expect(page.getByRole("heading", { name: "Synthetic second E2E visit" })).toBeVisible();

  const tablet = await browser.newContext({
    viewport: { width: 834, height: 1112 },
    userAgent:
      "Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/605.1.15"
  });
  const tabletPage = await tablet.newPage();
  await tabletPage.goto("/");
  const tabletLogin = tabletPage.getByRole("button", { name: "进入合成工作台" });
  if (await tabletLogin.isVisible().catch(() => false)) {
    await tabletLogin.click();
  }
  await tabletPage
    .locator(".selector-panel select")
    .nth(0)
    .selectOption(study!.id);
  await tabletPage
    .locator(".selector-panel select")
    .nth(1)
    .selectOption(siteA!.id);
  await expect(
    tabletPage.getByRole("heading", { name: "Synthetic second E2E visit" })
  ).toBeVisible();

  const tabletState = await tablet.storageState();
  const tabletCsrf = tabletState.cookies.find(
    (item) => item.name === "cra_csrf"
  )?.value;
  expect(tabletCsrf).toBeTruthy();
  const labUpload = await tablet.request.post(
    `${API_BASE}/api/v1/studies/${study!.id}/lab-reports`,
    {
      headers: {
        "X-CSRF-Token": tabletCsrf!,
        "Idempotency-Key": "w12-e2e-ipad-lab"
      },
      multipart: {
        file: {
          name: "synthetic_lab_report.pdf",
          mimeType: "application/pdf",
          buffer: artifact("tests/fixtures/labs/artifacts/synthetic_lab_report.pdf")
        },
        site_id: siteA!.id,
        title: "Synthetic W12 iPad laboratory",
        version_label: "v1"
      }
    }
  );
  expect(labUpload.status()).toBe(202);
  const labBody = await labUpload.json();
  await expect
    .poll(async () => {
      const response = await tablet.request.get(
        `${API_BASE}/api/v1/lab-reports/${labBody.id}`
      );
      return (await response.json()).state;
    }, { timeout: 60_000 })
    .toMatch(/^(succeeded|recognized)$/);

  await tabletPage.getByTestId("stage-subject_review").click();
  await tabletPage.getByRole("button", { name: "源检验读取" }).click();
  await expect(
    tabletPage.getByRole("heading", { name: "读取、来源定位与集中复核" })
  ).toBeVisible();
  await expect(tabletPage.getByText(/5 条候选/)).toBeVisible();
  await tabletPage
    .getByRole("button", { name: "批量确认已通过结构校验的候选" })
    .click();
  await expect(tabletPage.getByText(/已批量确认/)).toBeVisible();

  await page.getByRole("button", { name: "从服务端刷新" }).click();
  await expect(page.getByText("检验报告")).toBeVisible();
  await tablet.close();
});
