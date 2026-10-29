"""Code-ready task cards and deterministic next-task selection; no clinical operations."""
from __future__ import annotations
from pathlib import Path


def next_task(tasks: list[dict], track: str = "v1a") -> dict:
    by_id = {task["id"]: task for task in tasks}
    ordered = sorted((task for task in tasks if task.get("track") in ("baseline", track)), key=lambda task: task["id"])
    for task in ordered:
        if task["status"] == "verified":
            continue
        missing = [dep for dep in task["depends_on"] if by_id.get(dep, {}).get("status") != "verified"]
        blocked = task["status"] == "blocked" or bool(missing)
        return {
            "state": "blocked" if blocked else ("in_progress" if task["status"] == "in_progress" else "ready"),
            "task_id": task["id"], "title": task["title"],
            "instruction_path": task["instruction_path"], "track": track,
            "blocked_by": missing,
            "note": "Do not skip this task automatically. Record actual blockers and completion evidence.",
        }
    return {"state": "complete", "task_id": None, "track": track}


def render_execution_views(tasks: list[dict], module_map: dict) -> dict[str, str]:
    tick, fence = chr(96), chr(96) * 3
    views = {}
    for task in tasks:
        tid = task["id"]
        lines = [
            f'# {tid} {task["title"]}', "",
            "本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。", "",
            f'状态：{task["status"]}；分支路线：{task.get("track", "未填写")}。',
            "前置：" + ("、".join(task["depends_on"]) or "无") + "。必须按实际verified状态核实。", "",
            "## 临床工作目标", "", task.get("clinical_goal", "未填写"), "",
            "## 对应理论和模块", "",
            "理论：" + "、".join(f'[{rid}](../../theory/REQUIREMENTS.md#{rid.lower()})' for rid in task["requirement_ids"]), "",
            "模块：" + "、".join(f'[{mid}](../../{module_map[mid]["design_path"]})' for mid in task["module_ids"]), "",
            "先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。", "",
            "## 要创建或修改的目标文件", "",
            "| 路径（相对cra system） | 类型 | 用途 |", "| --- | --- | --- |",
        ]
        for item in task.get("deliverables", []):
            lines.append(f'| {tick}{item["path"]}{tick} | {item["kind"]} | {item["purpose"]} |')
        lines += ["", "以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。", "", "## 关键接口和数据约定", ""]
        lines += ["- " + value for value in task.get("contracts", [])]
        lines += ["", "## 实现步骤", ""]
        lines += [f"{index}. {value}" for index, value in enumerate(task.get("steps", []), 1)]
        lines += ["", "## 验证命令", "", "available表示当前已有入口；to_implement表示本任务必须先实现该入口，不能现在就声称已经运行。进入后续阶段使用合成数据和临时服务。", ""]
        for check in task.get("verification", []):
            lines += [f'- [{check["availability"]}] {check["purpose"]}', "", fence + "bash", check["command"], fence, ""]
        lines += ["## 完成标准", "", "原工作包验收：" + task["acceptance"], ""]
        lines += ["- " + value for value in task.get("done_when", [])]
        lines += ["", "关联完整场景：" + "、".join(task.get("scenario_ids", [])) + "。局部测试通过不自动把全部场景标为verified。", "", "## 本步不包含", ""]
        lines += ["- " + value for value in task.get("not_in_scope", [])]
        lines += [
            "", "## 完成后必须记录", "",
            "- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。",
            "- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。",
            "- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。",
            "- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。",
            "- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。",
        ]
        path = task.get("instruction_path", f"plan/work_packages/{tid}.md")
        views[path] = "\n".join(lines).rstrip() + "\n"
    selected = next_task(tasks)
    lines = [
        "# Codex逐项开发入口", "",
        "本页与16份任务卡均由plan/tasks.json生成，编号和状态沿用原计划。先读根目录CODEX_START_HERE.md。", "",
        "当前V1A默认下一项：" + (selected.get("task_id") or "本路线已完成") + "；状态：" + selected["state"] + "。", "",
        "默认按V1A编号顺序推进，遇阻塞先说明，不自动跳项。V1A/W08必须包含支持格式的自动读取；V1B复杂格式增强和获准部署分别选择，不混进普通下一项。", "",
        "| 工作包 | 具体执行说明 | 前置 | 路线 | 状态 |", "| --- | --- | --- | --- | --- |",
    ]
    for task in tasks:
        relative = task["instruction_path"].removeprefix("plan/")
        lines.append(f'| {task["id"]} | [{task["title"]}]({relative}) | {"、".join(task["depends_on"]) or "无"} | {task["track"]} | {task["status"]} |')
    lines += [
        "", "每张卡都列出临床目标、对应理论/模块、目标文件、接口、实现步骤、命令、完成标准和不包含范围。",
        "目标文件在任务未实现前可以不存在；task标verified时必须确实存在，待实现命令不能继续保留为to_implement。", "",
        "当前选择命令：" + tick + "python3 tools/next_task.py" + tick + "。该工具只读计划，不运行开发、部署或外部操作。",
    ]
    views["plan/CODEX_TASKS.md"] = "\n".join(lines).rstrip() + "\n"
    return views


def validate_execution(root: Path, tasks: list[dict], module_map: dict, requirement_map: dict, scenario_map: dict) -> list[str]:
    errors = []
    required = ("track", "instruction_path", "clinical_goal", "deliverables", "contracts", "steps", "verification", "done_when", "not_in_scope", "scenario_ids")
    for task in tasks:
        tid = task["id"]
        for key in required:
            if not task.get(key):
                errors.append(f"{tid}: missing execution field {key}")
        expected = f"plan/work_packages/{tid}.md"
        if task.get("instruction_path") != expected:
            errors.append(f"{tid}: task-card path must be {expected}")
        if task.get("track") not in ("baseline", "v1a", "v1b", "deployment"):
            errors.append(f"{tid}: invalid execution track")
        for rid in task["requirement_ids"]:
            requirement = requirement_map.get(rid)
            if requirement and not (set(requirement["modules"]) & set(task["module_ids"])):
                errors.append(f"{tid}: requirement {rid} has no owning module in this task")
        for sid in task.get("scenario_ids", []):
            if sid not in scenario_map:
                errors.append(f"{tid}: unknown execution scenario {sid}")
        for item in task.get("deliverables", []):
            path = (root / item["path"]).resolve()
            if not path.is_relative_to(root.resolve()):
                errors.append(f"{tid}: target path outside project")
                continue
            if item["kind"] not in ("code", "test", "migration", "config", "document"):
                errors.append(f"{tid}: invalid target kind")
            if task["status"] == "verified" and not path.is_file():
                errors.append(f"{tid}: verified task missing deliverable {item['path']}")
        for check in task.get("verification", []):
            if not check.get("command") or check.get("availability") not in ("available", "to_implement"):
                errors.append(f"{tid}: invalid verification command")
            if task["status"] == "verified" and check.get("availability") != "available":
                errors.append(f"{tid}: verified task still has a to_implement command")
        if task["status"] == "verified":
            by_id = {item["id"]: item for item in tasks}
            if any(by_id.get(dep, {}).get("status") != "verified" for dep in task["depends_on"]):
                errors.append(f"{tid}: verified task has unverified prerequisite")
    return errors
