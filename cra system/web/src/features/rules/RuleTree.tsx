import type {
  NodeEvaluationView,
  RuleConditionView,
  RuleNodeView,
  RuleSourceRefView
} from "../../api/client";

function operandLabel(
  operand: RuleConditionView["left"]
): string {
  if (!operand) {
    return "缺失操作数";
  }
  if (operand.kind === "fact_ref") {
    return operand.fact_key ?? "未命名事实";
  }
  const unit = operand.unit ? ` ${operand.unit}` : "";
  return `${String(operand.value)}${unit}`;
}

export function conditionLabel(
  condition: RuleConditionView | null | undefined
): string {
  if (!condition) {
    return "需要人工分析，当前无有限AST";
  }
  switch (condition.op) {
    case "all":
      return (condition.children ?? [])
        .map(conditionLabel)
        .map((item: string) => `(${item})`)
        .join(" 且 ");
    case "any":
      return (condition.children ?? [])
        .map(conditionLabel)
        .map((item: string) => `(${item})`)
        .join(" 或 ");
    case "not":
      return `非 (${conditionLabel(condition.child ?? null)})`;
    case "present":
      return `${condition.fact_key ?? "事实"} 存在`;
    case "eq":
      return `${operandLabel(condition.left)} = ${operandLabel(condition.right)}`;
    case "ne":
      return `${operandLabel(condition.left)} ≠ ${operandLabel(condition.right)}`;
    case "gt":
      return `${operandLabel(condition.left)} > ${operandLabel(condition.right)}`;
    case "ge":
      return `${operandLabel(condition.left)} ≥ ${operandLabel(condition.right)}`;
    case "lt":
      return `${operandLabel(condition.left)} < ${operandLabel(condition.right)}`;
    case "le":
      return `${operandLabel(condition.left)} ≤ ${operandLabel(condition.right)}`;
    case "in":
      return `${operandLabel(condition.left)} ∈ (${(condition.values ?? [])
        .map(operandLabel)
        .join("、")})`;
    case "date_interval":
      return `${condition.fact_key ?? "事件日期"} 相对 ${
        condition.anchor_fact_key ?? "锚点"
      } 位于 ${condition.min_days}…${condition.max_days} 天`;
    default:
      return condition.op;
  }
}

function SourceList({ refs }: { refs: RuleSourceRefView[] }) {
  return (
    <div className="rule-source-list">
      <strong>4 · 原文依据</strong>
      {refs.map((ref, index) => (
        <blockquote key={`${ref.anchor_key}-${index}`}>
          <p>{ref.quote}</p>
          <small>
            {ref.locator ?? ref.anchor_key}
          </small>
        </blockquote>
      ))}
    </div>
  );
}

export function RuleTree({
  tree,
  evaluation,
  depth = 0
}: {
  tree: RuleNodeView;
  evaluation?: NodeEvaluationView | null;
  depth?: number;
}) {
  return (
    <article className={`rule-node depth-${depth}`}>
      <div className="rule-level rule-level-one">
        <span>1 · 关键要求</span>
        <h4>{tree.summary}</h4>
        <code>{tree.node_key}</code>
        {evaluation && (
          <span className={`evaluation-state ${evaluation.status}`}>
            {evaluation.status}
          </span>
        )}
      </div>

      <div className="rule-level rule-level-two">
        <strong>2 · 完整条件与例外</strong>
        {(tree.preconditions ?? []).length > 0 ? (
          <ul>
            {(tree.preconditions ?? []).map((condition, index: number) => (
              <li key={index}>
                <span>前提</span> {conditionLabel(condition)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="unknown-copy">前提未提供</p>
        )}
        <p>
          <span>触发</span> {conditionLabel(tree.trigger ?? null)}
        </p>
        {(tree.exceptions ?? []).length > 0 ? (
          <ul className="exception-list">
            {(tree.exceptions ?? []).map((exception) => (
              <li key={exception.exception_key}>
                <b>{exception.exception_key}</b> {exception.description}
                {exception.condition && (
                  <small>{conditionLabel(exception.condition)}</small>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="unknown-copy">未结构化例外；不表示没有例外。</p>
        )}
      </div>

      <div className="rule-level rule-level-three">
        <strong>3 · 分支与具体事项</strong>
        {(tree.branches ?? []).map((branch) => (
          <section className="rule-branch" key={branch.branch_key}>
            <h5>{branch.label}</h5>
            <p>{conditionLabel(branch.condition)}</p>
            <small>{(branch.actions ?? []).join("；") || "来源未给后续动作"}</small>
          </section>
        ))}
        {(tree.children ?? []).map((child) => (
          <RuleTree key={child.node_key} tree={child} depth={depth + 1} />
        ))}
        <dl className="rule-details">
          <div>
            <dt>后续动作</dt>
            <dd>{tree.follow_up ?? "待完善"}</dd>
          </div>
          <div>
            <dt>完成方式</dt>
            <dd>{tree.completion ?? "待完善"}</dd>
          </div>
          <div>
            <dt>所需事实</dt>
            <dd>{(tree.required_facts ?? []).join("、") || "待明确"}</dd>
          </div>
        </dl>
        {tree.semantic_status === "analysis_required" && (
          <p className="notice notice-error" role="status">
            {(tree.unknowns ?? []).join("；") || "该条款需要人工分析，不能自动判定。"}
          </p>
        )}
      </div>

      <SourceList refs={tree.source_refs ?? []} />
    </article>
  );
}
