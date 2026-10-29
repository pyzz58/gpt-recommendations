"""Generate and check implementation handoffs without changing task state."""
import json
from pathlib import Path


def load_plan(root):
    return json.loads((root / "plan/implementation.json").read_text(encoding="utf-8"))


def validate_implementation(root, tasks):
    plan = load_plan(root)
    errors = []
    by_id = {t["id"]: t for t in tasks}
    phase_ids = [p["id"] for p in plan["phases"]]
    assigned = [tid for p in plan["phases"] for tid in p["task_ids"]]
    profiles = [p["task_id"] for p in plan["verification_profiles"]]
    if len(phase_ids) != len(set(phase_ids)) or sorted(assigned) != sorted(by_id):
        errors.append("implementation: each task must belong to exactly one phase")
    if sorted(profiles) != sorted(by_id):
        errors.append("implementation: each task needs exactly one verification profile")
    milestones = plan["milestones"]
    if len({m["id"] for m in milestones}) != len(milestones):
        errors.append("implementation: duplicate milestone ID")
    for milestone in milestones:
        if not milestone.get("proof") or not milestone.get("after_tasks") or any(t not in by_id for t in milestone["after_tasks"]):
            errors.append("implementation: incomplete milestone " + milestone["id"])
    for task in tasks:
        tid = task["id"]
        for key in ("phase_id", "design_refs", "entry_conditions", "handoff_outputs", "verification_profile"):
            if not task.get(key):
                errors.append(tid + ": missing implementation handoff " + key)
        if task.get("verification_profile") != tid:
            errors.append(tid + ": incorrect verification profile")
        matching = [p for p in plan["phases"] if tid in p["task_ids"]]
        if len(matching) != 1 or matching[0]["id"] != task.get("phase_id"):
            errors.append(tid + ": phase mapping mismatch")
        for ref in task.get("design_refs", []):
            path = (root / ref.split("#", 1)[0]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                errors.append(tid + ": missing/outside implementation reference " + ref)
    for profile in plan["verification_profiles"]:
        if profile.get("workflow_path") != ".github/workflows/cra-system.yml" or not profile.get("required_job") or not profile.get("required_steps") or not profile.get("binding_paths"):
            errors.append("implementation: incomplete CI profile " + profile["task_id"])
        if profile["task_id"] != "CRA-W00" and profile.get("required_job") != profile["task_id"].lower():
            errors.append("implementation: task-specific job name required " + profile["task_id"])
        for prefix in profile.get("binding_paths", []):
            if not (root / prefix).resolve().is_relative_to(root.resolve()):
                errors.append("implementation: source binding outside project " + profile["task_id"])
        if len(profile["required_steps"]) != len(set(profile["required_steps"])):
            errors.append("implementation: duplicate required step " + profile["task_id"])
    return errors


def render_implementation(root, tasks):
    plan = load_plan(root)
    lines = [
        "# 完整技术实施路径", "",
        "技术执行版" + plan["version"] + "。本页由plan/implementation.json与plan/tasks.json生成，任务卡是各项代码交付入口。设计完成不等于应用已实现。", "",
        "先读[第一性原理复核](../audit/FIRST_PRINCIPLES_REVIEW_V04.md)、[总技术路线](../architecture/IMPLEMENTATION_ROUTE.md)和[Codex入口](../CODEX_START_HERE.md)。", "",
        "## 按阶段推进", "",
        "| 阶段 | 工作包 | CRA实际能得到什么 |", "| --- | --- | --- |",
    ]
    for p in plan["phases"]:
        lines.append(f'| {p["id"]} {p["title"]} | {"、".join(p["task_ids"])} | {p["clinical_result"]} |')
    lines += ["", "P6为复杂格式增强，P7需实际授权环境。默认继续沿V1A按W01—W13推进，不自动增加付费服务、实际部署或非检验OCR。", "", "## 每项的进入条件和交接", ""]
    for task in tasks:
        lines += [
            f'### [{task["id"]} {task["title"]}]({task["instruction_path"].removeprefix("plan/")})', "",
            "状态：" + task["status"] + "；前置：" + ("、".join(task["depends_on"]) or "无") + "。", "",
            "进入条件：" + "；".join(task["entry_conditions"]), "",
            "交接产物：" + "；".join(task["handoff_outputs"]), "",
            "技术输入：" + "、".join(f'[{Path(p).name}](../{p})' for p in task["design_refs"]), "",
            "专属CI：" + task["verification_profile"] + "。具体代码目标、步骤、命令和完成标准见上方任务卡。", "",
        ]
    lines += ["## 可观察里程碑", "", "| 里程碑 | 前置工作包 | 必须看到的实际证据 |", "| --- | --- | --- |"]
    for m in plan["milestones"]:
        lines.append(f'| {m["id"]} {m["label"]} | {"、".join(m["after_tasks"])} | {m["proof"]} |')
    lines += ["", "## 完成证据和能力边界", "",
              "W00保留历史工程基线证据。W01以后verified必须绑定实际源码/任务规范指纹、精确测试提交、GitHub run及任务专属job/步骤；基础CI或自报文字不能代替。详见[验证与发布](../architecture/VALIDATION_AND_RELEASE.md)。", "",
              "工程完成、合成/provider评估和获授权临床试用分别记录。开发任务通过不代表所有格式、所有项目或医学结论可靠，支持范围以实测SupportProfile和能力清单为准。", "",
              "## 仍需实测", ""]
    lines += ["- " + x for x in plan["open_performance_questions"]]
    return "\n".join(lines).rstrip() + "\n"
