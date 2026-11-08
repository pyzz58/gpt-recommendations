import { type FormEvent, useCallback, useEffect, useState } from "react";

import {
  ApiError,
  type DocumentVersionView,
  type DocumentView,
  type ReviewTemplatePreviewView,
  type ReviewTemplateView,
  createReviewTemplate,
  getDocumentVersions,
  getDocuments,
  getReviewTemplates,
  previewReviewTemplate
} from "../../api/client";

type Props = {
  studyId: string;
  siteId: string;
};

type TemplateCandidate = {
  document: DocumentView;
  version: DocumentVersionView;
};

function errorMessage(reason: unknown): string {
  return reason instanceof ApiError
    ? `${reason.message}（${reason.code}）`
    : reason instanceof Error
      ? reason.message
      : "模板核查配置失败";
}

export function TemplateReviewConfig({ studyId, siteId }: Props) {
  const [templates, setTemplates] = useState<ReviewTemplateView[]>([]);
  const [candidates, setCandidates] = useState<TemplateCandidate[]>([]);
  const [preview, setPreview] = useState<ReviewTemplatePreviewView | null>(
    null
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const [nextTemplates, documents] = await Promise.all([
        getReviewTemplates(studyId, siteId),
        getDocuments(studyId, siteId)
      ]);
      const nextCandidates: TemplateCandidate[] = [];
      for (const document of documents.filter(
        (item) => item.purpose === "template"
      )) {
        const versions = await getDocumentVersions(document.id);
        const latest = versions[0];
        if (
          latest &&
          latest.original_filename.toLowerCase().endsWith(".docx")
        ) {
          nextCandidates.push({ document, version: latest });
        }
      }
      setTemplates(nextTemplates);
      setCandidates(nextCandidates);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }, [siteId, studyId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const refresh = () => {
      void load();
    };
    window.addEventListener("cra-document-updated", refresh);
    return () =>
      window.removeEventListener("cra-document-updated", refresh);
  }, [load]);

  async function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const versionId = String(form.get("version_id") ?? "");
    if (!versionId) {
      setError("请选择已上传的 DOCX 报告模板。");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setPreview(await previewReviewTemplate(versionId));
      setMessage(
        "已提取章节和明确问句。请集中核对问句、来源与覆盖缺口后保存配置。"
      );
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!preview) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const items = preview.questions.map((item, index) => ({
      ...item,
      question_text:
        String(form.get(`question_${index}`) ?? "").trim() ||
        item.question_text,
      applicability: {
        ...item.applicability,
        reviewer_conditions:
          String(form.get(`conditions_${index}`) ?? "")
            .split(/[,，;；]/)
            .map((value) => value.trim())
            .filter(Boolean),
        reviewer_exceptions:
          String(form.get(`exceptions_${index}`) ?? "")
            .split(/[,，;；]/)
            .map((value) => value.trim())
            .filter(Boolean)
      }
    }));
    setBusy(true);
    setError(null);
    try {
      await createReviewTemplate({
        sourceDocumentVersionId: preview.source_document_version_id,
        title: String(form.get("title") ?? "").trim(),
        items,
        warnings: preview.warnings,
        idempotencyKey: crypto.randomUUID()
      });
      setPreview(null);
      await load();
      setMessage("模板核查项已集中确认，后续监查可直接复用。");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const sections = preview?.sections ?? [];
  return (
    <section
      className="workspace-module template-review-config"
      aria-labelledby="template-review-config-title"
    >
      <div className="module-heading">
        <div>
          <p className="eyebrow">报告模板 · 集中配置</p>
          <h2 id="template-review-config-title">
            从章节和问句生成可复用核查项
          </h2>
          <p>
            只提取明确标题和问句；无法稳定解析的章节保留为覆盖缺口，
            不要求 CRA 手写技术模板。
          </p>
        </div>
        <span className="status-chip muted">{templates.length} 个配置</span>
      </div>

      {message && <div className="notice" role="status">{message}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}

      <div className="report-template-grid">
        <form
          className="subject-import-form"
          onSubmit={(event) => void prepare(event)}
        >
          <p className="eyebrow">第一次集中配置</p>
          <h3>选择报告模板</h3>
          <label>
            DOCX 模板
            <select name="version_id" required>
              <option value="">选择已上传模板</option>
              {candidates.map((item) => (
                <option key={item.version.id} value={item.version.id}>
                  {item.document.title} · {item.version.version_label}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary-button"
            type="submit"
            disabled={busy || candidates.length === 0}
          >
            提取章节与问句
          </button>
        </form>

        <section className="source-reference">
          <p className="eyebrow">已保存配置</p>
          {templates.length === 0 ? (
            <p>尚无复核模板配置。</p>
          ) : (
            templates.map((template) => (
              <div key={template.id}>
                <strong>{template.title}</strong>
                <small>
                  {template.items.length} 个核查项 · r{template.revision} ·{" "}
                  {new Date(template.created_at).toLocaleString()}
                </small>
              </div>
            ))
          )}
        </section>
      </div>

      {preview && (
        <form className="template-review-confirm" onSubmit={confirm}>
          <div className="applicable-heading">
            <div>
              <p className="eyebrow">集中修订</p>
              <h3>确认章节、问句与来源</h3>
            </div>
            <span className="status-chip">
              {preview.questions.length} 问句 / {sections.length} 章节
            </span>
          </div>
          <label>
            配置名称
            <input
              name="title"
              defaultValue={`${preview.title} · 核查配置`}
              required
            />
          </label>
          {preview.warnings.map((warning, index) => (
            <div className="inline-warning" key={index}>
              {String(warning.message ?? warning.code)}
            </div>
          ))}
          {sections.map((section) => {
            const sectionQuestions = preview.questions
              .map((item, index) => ({ item, index }))
              .filter(
                ({ item }) => item.section_key === section.section_key
              );
            return (
              <section
                className="template-section-card"
                key={String(section.section_key)}
              >
                <div>
                  <p className="eyebrow">
                    {String(section.section_locator ?? "模板位置")}
                  </p>
                  <h4>{String(section.title ?? "未分类章节")}</h4>
                </div>
                {sectionQuestions.length === 0 ? (
                  <p className="inline-warning">
                    该章节未解析出明确问句，已保留覆盖缺口。
                  </p>
                ) : (
                  sectionQuestions.map(({ item, index }) => (
                    <article key={item.item_key}>
                      <span className="status-chip muted">
                        {item.item_key}
                      </span>
                      <label>
                        问句
                        <textarea
                          name={`question_${index}`}
                          rows={2}
                          defaultValue={item.question_text}
                        />
                      </label>
                      <label>
                        条件（逗号分隔）
                        <input
                          name={`conditions_${index}`}
                          placeholder="例如：V1、检验报告、EDC快照"
                        />
                      </label>
                      <label>
                        例外（逗号分隔）
                        <input
                          name={`exceptions_${index}`}
                          placeholder="例如：中心已批准延期"
                        />
                      </label>
                      <small>
                        原文：{item.source_locator} · {item.source_quote}
                      </small>
                    </article>
                  ))
                )}
              </section>
            );
          })}
          <button
            className="primary-button compact"
            type="submit"
            disabled={busy}
          >
            保存并复用此核查配置
          </button>
        </form>
      )}
    </section>
  );
}
