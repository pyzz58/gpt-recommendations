# F02-09｜摄影阶段冻结与 F03 交接

日期：2026-10-31  
机器可读交接：[F02_STAGE_HANDOFF_2026-10-31.json](F02_STAGE_HANDOFF_2026-10-31.json)  
PR：[#79](https://github.com/pyzz58/gpt-recommendations/pull/79)（Draft，stacked 在 F01 分支上）

## 1. 当前结论

**F02 软件层进入 review-ready；QO-F02 仍为 `audit_pending`。**

已完成严格摄影/灯光/美术合同、公开合成双镜正反回归与关键阻断点。尚未完成独立 DOP/灯光/美术审阅、真实摄影机/镜头/灯具/场景测试、AI 视频光学一致性和最终成片验收。

## 2. 已完成

- camera 强制景别、焦段、screen axis、camera side、eyeline、movement trigger、运动原因和安全区；
- art 强制灯态、实用光源、主光位置/方向、灯光变化原因、色彩路径、场景几何；
- 同场景几何漂移、无理由越轴、主光方向跳变阻断；
- 有理由越轴/灯光变化进入 review；
- 摄影泛词进入 review，不自动判错；
- 公开合成双镜正反应回归。

## 3. 仍阻塞

- 独立摄影指导/DOP、灯光师、美术指导的专业盲评；
- 真实摄影机/镜头/灯具/场景测试；
- 真实 AI 视频或实拍光学一致性；
- 色彩、构图、光照与最终成片验收。

## 4. 冻结规则

F02 进入软件阶段冻结：

- 不再无边界增加摄影 schema 或新岗位；
- 只接受真实缺陷修复、专业审稿意见、证据补齐和相关回归；
- PR #79 保持 Draft，待 #77/#78 合并后 retarget/rebase 到 `main`；
- 不用绿色测试替代摄影审片或真实媒体。

## 5. 向 F03 交接

F03（对白、配音、拟音、音乐）应读取：

- F02 的 camera side、eyeline、light state、key-light direction、scene geometry 与 safe area；
- F01 的 physical state、handoff 与 performance context；
- 现有 `agent_role_contracts` sound 合约、`director_speech_cues.py` 与 `director_av_sync_smoke.py` 的边界。

F03 不得声称：

- F02 已完成或摄影质量已验证；
- 真实摄影/灯光/媒体已测试；
- 独立 DOP 审片完成；
- 最终成片已批准。

## 6. 下一项

进入 **QO-F03 对白/配音/拟音/音乐专业审计**。F02 的真实摄影与独立审片继续保持阻塞，不在没有授权素材时补造证据。
