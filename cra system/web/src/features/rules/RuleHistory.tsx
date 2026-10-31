import type {
  RuleRelationView,
  RuleVersionSummaryView
} from "../../api/client";

const RELATION_LABEL: Record<string, string> = {
  unchanged: "未改变",
  new: "新增",
  supplement: "补充",
  exception: "增加例外",
  replaces: "替代",
  withdraws: "撤销",
  restores: "恢复",
  conflict: "含义冲突/待核实"
};

export function RuleHistory({
  versions,
  selectedVersionId,
  currentVersionId,
  relations,
  onSelect
}: {
  versions: RuleVersionSummaryView[];
  selectedVersionId: string;
  currentVersionId: string | null;
  relations: RuleRelationView[];
  onSelect: (versionId: string) => void;
}) {
  return (
    <section className="rule-history" aria-label="规则版本与修改轨迹">
      <div className="confirmation-heading">
        <div>
          <p className="eyebrow">不可变版本与逐条关系</p>
          <h4>修改轨迹</h4>
        </div>
        <span className="status-chip muted">{versions.length} 个版本</span>
      </div>
      <div className="version-list">
        {versions.map((version) => (
          <button
            key={version.id}
            type="button"
            className={version.id === selectedVersionId ? "active" : ""}
            onClick={() => onSelect(version.id)}
          >
            <strong>v{version.version_no}</strong>
            <span>{version.state}</span>
            <small>
              {version.id === currentVersionId ? "当前 · " : ""}
              {version.confirmation_basis}
            </small>
          </button>
        ))}
      </div>
      {relations.length > 0 ? (
        <ul className="relation-list">
          {relations.map((relation) => (
            <li key={relation.id}>
              <strong>{RELATION_LABEL[relation.relation_type] ?? relation.relation_type}</strong>
              <span>{relation.reason}</span>
              <small>
                {relation.from_version_id
                  ? `来自 ${relation.from_version_id.slice(0, 8)}…`
                  : "无前驱"}
              </small>
            </li>
          ))}
        </ul>
      ) : (
        <p className="unknown-copy">该版本尚未登记逐条更新关系。</p>
      )}
    </section>
  );
}
