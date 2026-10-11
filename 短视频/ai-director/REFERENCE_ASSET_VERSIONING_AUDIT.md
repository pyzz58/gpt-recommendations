# AUD-003 · 私有参考资产版本与逐镜绑定（2026-10-11）

## 本轮真正实现的内容

前一轮 `film_continuity.py` 只追踪“演员外观描述/道具状态”的文字，不具备正式参考图、版本与内容识别的关联。本轮新增 [asset_reference_manifest.py](asset_reference_manifest.py) —— **仅用于可信私人运行环境的资产元数据层**；通过 SHA-256、稳定资产 ID 和版本链，为人物、服装、场景、道具建立不覆盖历史的参考信息，并按镜头绑定。

重点借鉴 [Ironieser/CineCrew](https://github.com/Ironieser/CineCrew) FilmDSL 中的共享 `assets` + `clips[]` 资产引用与跨镜 memory 设计。CineCrew 研究仓库许可证为 Apache-2.0，但它本身不等同于广泛成熟的商用资产库；这里只借鉴思路，**没有复制其源码或安装其生成引擎**。内容 SHA-256 和不可覆盖版本是通用数据工程原则，本项目自行实现，无需增加重型 DVC 或视频模型依赖。

### 资产清单

元数据将每个来源已声明的 `CHAR01` / `PROP01` / `LOC01` 与新的 `ASSET_xxx` 资产关联；每个资产包含：

| 元数据 | 说明 |
| --- | --- |
| `asset_id` | 稳定参考资产编号；不能复用到另一个角色/道具 |
| `entity_id` | 权威原稿中登记的角色、道具或场景 ID |
| `slot` | `identity_front` / `identity_side` / `wardrobe` / `prop_reference` / `location_reference` |
| `version` | 从 1 开始按序增加，不覆写历史 |
| `sha256`、`size_bytes`、`media_type` | 在私人执行环境中由传入的内存字节计算，只保存摘要/尺寸/声明类型 |
| `previous_revision_digest` | 绑定上一个版本的 SHA-256 内容结构摘要，防止静默修订 |
| `rights_status` / `consent_status` / `review_status` | 目前固定 `unverified/unverified/pending`，绝不假称人工/版权已通过 |

`shot_bindings[S01][CHAR01] = {asset_id,version,sha256}`；每个镜头对来源中已登记的实体（包括同一房间 LOC ID）有明确槽位，未配置为 `null`，不得填入模型猜测的人物或外部资源链接。改动人物参考图后增加新版本，之前绑定旧版的镜头在校验时被拒绝，必须由操作者逐镜明确重新绑定；不同镜头采用不同人物参考时会返回 `reference_switch_requires_human_review`，不能冒充同一张脸已确立。

## 增量修复：同一角色一镜多参考槽位（AUD-021）

在审查原版 `asset_reference_manifest.py` 后，发现一个确定性缺陷：虽然每张卡支持 `identity_front / identity_side / wardrobe`，但 `shot_bindings[S01][CHAR01]` 只有一个引用，绑定服装会直接替换脸部主参考。原设计因此**无法同时提供面孔、侧视和服装**，不利于视频创作岗位保留同一演员的统一视觉设计。

现在将清单版本提升为 `private-visual-reference-manifest-v2`，在保留原主参考 `shot_bindings[shot][entity]` 的同时，添加：

```json
{
  "shot_slot_bindings": {
    "S01": {
      "CHAR01": {
        "identity_front": {"asset_id": "ASSET_FACE", "version": 1, "sha256": "（示意：64位哈希）"},
        "identity_side": {"asset_id": "ASSET_SIDE", "version": 1, "sha256": "（示意：64位哈希）"},
        "wardrobe": {"asset_id": "ASSET_COAT", "version": 1, "sha256": "（示意：64位哈希）"}
      }
    }
  }
}
```

上方仅说明字段，**不是可直接提交的有效数据**；真实 SHA-256 必须在受信任的私人进程里从对应文件字节计算。

### 新的 fail-closed 规则

- 人物可同时绑定正脸、侧脸、服装；道具和场景分别支持其自身槽位，**绑定另一槽不会覆盖已锁定的脸部主参考**。
- 每个槽位必须指向**同一个来源人物/道具/场景**登记的正确版本，校验 asset ID、slot、版本号、SHA-256；不能把服装卡塞进正脸槽或凭空增加未在权威计划登记的人。
- 参考图版本发生变化时，引用旧版的每一个镜头绑定都被识别为过期；只能逐镜明确更新，不可静默批量升级。
- 同一人物的 **wardrobe** 槽位在相邻镜头切换，即使其正脸未变，也会输出独立的人工审核记录。此为“需要判断是否换装”，不是算法已经证明有问题。
- 对每镜建议人物至少有 `identity_front` 与 `wardrobe`，对道具建议 `prop_reference`，场景建议 `location_reference`；缺失仅输出 `missing_recommended_slots`，绝不自动捏造图或拒绝合理的无道具纯物镜。
- 总导演和各岗位的 JSON 上下文现在包含 `shot_slot_bindings`；最终视频工作单也带 `versioned_reference_slot_bindings`，只包含编号、版本和哈希，不携带私人图像或可访问路径。
- **迁移说明**：v1 清单不会被当作 v2 随意复用；老 v1 快照在 v2 校验时明确失败，必须由可信操作者从合法来源和原版本重新建立 v2 资产映射、逐镜复核；不能自行伪造哈希或身份批准。

### 还没有实现的事

这仍然只是元数据模型，不是图片托管或图片模型。没有持久化的私有原图、没有真实的正面/侧面识别比较，也没有实际 Wan / Seedance 使用这些图片生成并保持同一人物的证据。资产 `rights_status`、`consent_status`、`review_status` 继续保持未验证/待确认。AUD-003/Issue #2 仍 OPEN。

---

## 代码级隐私与许可边界

- 只接受 `bytes` 作为**私人进程内的输入**，校验 PNG/JPEG/WEBP 文件头、文件大小上限，立即计算 SHA-256。**不会保存图片内容、路径、文件名、任意 URL、EXIF 或图像特征到公开仓库**；不会自动下载、重新上传、生成图片、修改硬盘上的任何媒体。
- 旧版只检查文件头而不能保证图片可解码（AUD-022 已补全私有进程中的解码校验）；**即使可解码，仍不等于人物视觉一致，也不等于已获照片版权、肖像同意或生成许可**。所有这些标记均保持 `False`，需要日后的私有存储层、真正图片解析/视觉验收和认证的人类授权流程。
- 不接受调用方写入 `human_approved=true`、`rights_verified=true`、`paid_api_authorized=true`，也不接受把外部 URL/私人绝对路径附加到 manifest。
- 由权威 `plan_digest` + `source_digest` 绑定资产版本；改变文案、修改镜头或调换资产所属人物都 fail closed。
- 该模块只保存**元数据**：原始图片字节需要未来建立可信长期私人库，项目目前并没有自动持久保存图片、备份、媒体上传/引用到生成模型的执行通道。

## 真正接入十岗位的路径

1. `editorial_review_lock.attach_reference_manifest(snapshot, source, manifest)` 返回**新的**私人规划快照，既不改已有快照，也不授予人工批准。重新 `stage_locked_team` 会在 team 状态中绑定 `asset_reference_manifest_digest`；原始未附资产的旧状态不能悄悄用新资产继续付费。
2. `agent_live_crew.inspect_locked_role` 对 source/plan/asset digest 做三重检验，不一致时在网络请求前停止；`roles.build_role_messages(..., reference_manifest=...)` 仅在私人 user JSON 中传递资产 ID、版本、哈希和逐镜关联，没有真实图像输入给模型，明确告诉其身份、权属未经验证。
3. `production_delivery.build_locked_crew_delivery` 再检查 team 与快照资产 digest，并在最终工单里以 `versioned_reference_bindings` 传递固定引用版本。工单会标明没有真实照片、没有可核实的人物视觉匹配、也没有已批准的使用许可；**不把已有的图片元数据暗示成可直接生成视频**。

所有来源未提供资产的旧式规划仍可以继续离线生成**供人审核的候选工单**，但不能宣称参考图已完成，也不会给模型凭空生成独立身份证据。

## 验收与未解决项

`tests/test_asset_reference_manifest.py` 离线合成用例验证：

- 新的资料卡、来源绑定、hash、不可覆盖版本链，历史与新版本之间的过期镜头报错；
- 演员和道具 ID 不可互换、镜头不可引用未知资产、每镜手动绑定；
- 伪造人工批准、肖像许可、外部 URL、改变原始稿版本会被拒绝；
- reference SHA 与给定内存字节不一致时被阻断；换参考版本依然要人工审核；
- 绑定到规划快照后，旧团队状态不得继续复用；最终工作包的资产引用只含元数据。

**AUD-003 仍未关闭**：没有真实参考图存储与备份、没有真实用户许可审计/审核身份，也没有 Wan/Seedance 中的角色变脸/道具漂移视频比对。未来要创建长期私人图像库时，需单独确认本机/云环境权限与用户是否允许传输私有媒体；不能直接将 GitHub Actions 公开制品视为媒体库。

[主审计账](DEEP_AUDIT_MASTER.md) · [问题清单](AUDIT_FINDINGS.json) · [AUD-003 GitHub Issue #2](https://github.com/pyzz58/gpt-recommendations/issues/2)

## AUD-022 · 文件头不是图片：已修复严格解析缺口（2026-10-11）

**已证实的 P1 缺陷**：此前允许仅有 PNG/JPEG/WEBP 文件头（任意尾部字节）的“图片”进入参考资产卡；SHA-256 只能证明所提供字节没有被替换，不能证明媒体真的可读。旧合成测试原本就使用故意无效的魔数假图片。

**本轮最小融合**：在私有内存的 `register_image` 和 `verify_bytes` 采用 [Pillow](https://github.com/python-pillow/Pillow) 固定 `12.3.0`（MIT-CMU），强制 `Image.verify()` 与重新打开后的 `Image.load()` 完整解码；只允许 PNG/JPEG/WEBP、单帧、最大 8192 边长、16M 像素、12MB 源数据。解码器缺失、允许截断文件的宽松配置、格式冒名、文件截断、非图片、异常维度会 fail-closed。正常示例由标准库构造 1×1 的真实有效虚构 PNG，不使用真人图片。

**回归证据**：[修复 commit](https://github.com/pyzz58/gpt-recommendations/commit/7bbf40f21eecea7b80650eb19ce1aa11b33cfe31)，[GitHub Actions 38120478073](https://github.com/pyzz58/gpt-recommendations/actions/runs/38120478073) **564 tests passed**，新添 5 项反例测试；CI 只处理非敏感合成字节，未发生模型调用、存储私人图像或支付模型费用。

**已解决的边界**仅为“已接收图片数据在当前受信任运行进程内可以真正解析”；解析不等于人脸/衣着的跨镜视觉一致、授权许可、人审，更不代表能够将图交给 Wan/Seedance 或生成出合格画面。真实图片仍不在 GitHub/CI 持久保存，私有长期存储与人工审批流程尚未实现。高风险不可信图片将来还需进程沙箱、资源限制与第三方解码器安全公告复核，此次没有在 Mac 部署。Issue #2 保持 OPEN。
