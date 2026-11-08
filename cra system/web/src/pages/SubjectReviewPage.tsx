import { useEffect, useState } from "react";

import {
  type CapabilityResponse,
  getCapabilities
} from "../api/client";
import { ImportPreview } from "../features/edc/ImportPreview";
import { LabComparison } from "../features/laboratory/LabComparison";
import { RecognitionReview } from "../features/laboratory/RecognitionReview";
import { AssessmentPanel } from "../features/safety/AssessmentPanel";
import { SubjectTimeline } from "../features/subjects/SubjectTimeline";

type Props = {
  studyId: string;
  siteId: string;
};

type Tab = "subject" | "edc" | "lab" | "compare" | "safety";

const TABS: {
  key: Tab;
  step: string;
  label: string;
  detail: string;
}[] = [
  {
    key: "subject",
    step: "01",
    label: "患者上下文",
    detail: "分层list、日期与断点"
  },
  {
    key: "edc",
    step: "02",
    label: "EDC 数据",
    detail: "Excel范围、映射与快照"
  },
  {
    key: "lab",
    step: "03",
    label: "原始文件",
    detail: "PDF、拍照或清晰图像"
  },
  {
    key: "compare",
    step: "04",
    label: "一致性核对",
    detail: "先匹配，再比较字段"
  },
  {
    key: "safety",
    step: "05",
    label: "安全与逻辑",
    detail: "依据方案/IB生成问题"
  }
];

export function SubjectReviewPage({ studyId, siteId }: Props) {
  const [tab, setTab] = useState<Tab>("subject");
  const [capabilities, setCapabilities] =
    useState<CapabilityResponse | null>(null);

  useEffect(() => {
    getCapabilities().then(setCapabilities).catch(() => setCapabilities(null));
  }, []);

  const ocr = capabilities?.providers.ocr;
  const analysis = capabilities?.providers.analysis;
  return (
    <section className="workspace-module subject-review-page">
      <div className="module-heading">
        <div>
          <p className="eyebrow">逐患者核查</p>
          <h2>分层list、源文件与EDC在同一患者上下文接续</h2>
          <p>正常范围可按批简记；低可信、异常、跳过和安全问题集中展开。</p>
        </div>
      </div>
      <div className="review-capability-strip">
        <span>
          <strong>EDC Excel</strong> 已接入
        </span>
        <span>
          <strong>原始文件</strong>{" "}
          {ocr?.validated ? "清晰图像 OCR 已验证" : "文字 PDF 可用"}
        </span>
        <span>
          <strong>安全与逻辑</strong>{" "}
          {analysis?.status === "configured"
            ? "规则与模型受限启用"
            : "规则/人工路径可用，模型未配置"}
        </span>
        <span>
          <strong>医学结论</strong> 始终需要人工确认
        </span>
      </div>
      <div className="review-workbench-shell">
        <aside className="review-step-rail" aria-label="核查步骤">
          <div>
            <p className="eyebrow">本次核查路径</p>
            <h3>源数据 → EDC → 问题</h3>
            <p>
              上传与核对集中在同一患者上下文。每一步保留来源、未知和人工操作。
            </p>
          </div>
          <nav>
            {TABS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={item.key === tab ? "active" : ""}
                data-testid={`review-tab-${item.key}`}
                onClick={() => setTab(item.key)}
              >
                <span>{item.step}</span>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </button>
            ))}
          </nav>
        </aside>
        <div className="review-stage-canvas">
          {tab === "subject" && (
            <SubjectTimeline studyId={studyId} siteId={siteId} />
          )}
          {tab === "edc" && (
            <ImportPreview studyId={studyId} siteId={siteId} />
          )}
          {tab === "lab" && (
            <RecognitionReview studyId={studyId} siteId={siteId} />
          )}
          {tab === "compare" && (
            <LabComparison studyId={studyId} siteId={siteId} />
          )}
          {tab === "safety" && (
            <AssessmentPanel studyId={studyId} siteId={siteId} />
          )}
        </div>
      </div>
    </section>
  );
}
