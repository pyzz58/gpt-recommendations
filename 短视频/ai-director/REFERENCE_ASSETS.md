# Reference Assets · 跨镜头人物/场景/道具参考资产库（GitHub-only 开发）

> **当前状态**：完成参考资产清单生成、离线校验和导演编译器接口设计。**不生成参考图、不锁脸、不执行付费视频模型、不安装到 Mac、不访问用户私人 jobs/ 或图库。**
> 所有真实图像只能将来保存在用户明确选择的私有目录；**绝不能作为公开 GitHub 资产提交**。

## 成熟项目研究与选择

1. [CineCrew / FilmDSL](https://github.com/Ironieser/CineCrew)（仓库标记 Apache-2.0）：使用稳定 `char_* / loc_* / prop_*` ID、人物角色表、场景和道具资产引用，以及跨镜约束。**采用稳定 ID 与单一资产库的思路，不复制源码或引入完整多 Agent 框架**；该项目仍属新近公布的研究型项目。
2. [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline)（MIT）：角色参考图转面表、场景参考图和道具参考图分别收集，成功生成的前后帧可以作为后续图像衔接线索。**采用人物不同角度的资产需求表，前后帧实际能力以后依模型支持再验证**。
3. [python-jsonschema](https://github.com/python-jsonschema/jsonschema)（MIT）：本项目用 Draft 2020-12 结构规范 `schemas/reference_assets.schema.json`，校验器纯 Python 实现必要检查，避免给用户的 Mac 强制添加安装负担。

借鉴实现的是**资产模型、验证机制与使用流程**，不是已经对第三方模型进行了实际接入。

## 新文件的职责

- `reference_assets.py`：`scaffold` 根据**当前已声明**的角色、场景、结构化道具 ID，为各参考角度生成 `not_created` 清单；`audit` 逐镜检查绑定、审批元数据、来源/权利状态、文件路径和哈希。不调用外部服务。初次 scaffold 使用不可覆盖写入模式，不能无声覆写已有私有清单。
- `schemas/reference_assets.schema.json`：公共 JSON Schema；**不包含真实私人图片、路径或姓名**。
- `director_v2.py`：`validate(...,assets,asset_root)` 及 `compile_package(...,assets,asset_root)` 可选择使用私有清单；编译输出将显示引用需求、是否通过参考资产预检、未获授权的警告。**旧 director_v02.json 没有清单时仍可编译导演图纸，但状态为 `not_assessed`、不代表已满足生成条件。**

### 清单结构（示例仅包含合成 ID）

```json
{
  "schema_version": "1.0",
  "assets": {
    "CH_MAIN": {
      "kind": "character",
      "description": "Fictional actor, fixed facial description",
      "wardrobe": "dark top",
      "views": {
        "three_quarter": {
          "status": "not_created",
          "path": null,
          "sha256": null,
          "source": null,
          "rights_status": "unchecked",
          "rights_evidence": null,
          "reviewer": null,
          "human_approved": false
        }
      }
    }
  },
  "shot_requirements": {
    "S01": [{"asset_id": "CH_MAIN", "view": "three_quarter", "role": "identity"}]
  },
  "policy": {
    "generated_media": false,
    "identity_consistency_verified": false,
    "private_media_in_public_repo": false
  }
}
```

该片段用于说明字段，真实完整资产清单需要每个镜头都出现一个 requirements 数组，还要登记已声明的场景和道具。多镜头引用同一个资产 ID，避免每一镜重定义脸和场景。

## 状态与验收规则

| 状态 | 意义 | 生成前置检查 |
|---|---|---|
| `not_created` | 尚未制作参考图 | 记录 missing，不允许声称已经有参考图 |
| `candidate` | 已产生候选，但未被批准 | 仍标记 missing |
| `approved` | 有人工核对记录 | 必须有图片相对路径、SHA-256、来源、授权核对依据、审核者、人工批准标志；实际文件必须在用户给定的私有根目录内 |

资产校验器能检测路径穿越、符号链接、缺失文件、已知图片头和文件哈希变化，并对每个镜头输出 `REFERENCE_NOT_READY`、`REQUIRED_REFERENCE_UNBOUND`、`IMAGE_DIGEST_MISMATCH` 等问题。它无法证明图片一定可完整解码、拥有合法版权，或 AI 视频模型能够保持人脸一致；人工审批状态仅代表**清单记录**，不能取代实物审核、供应商授权协议或影像试验。

### 道具不应自动认为出镜

完整连续性合同会记录一个物品即使此时在另一个房间的状态。**不能把合同所有道具自动绑定到每个镜头**。目前默认自动绑定视频/静态路线中可见的人物和场景；`generation.reference_bindings` 可显式指定当前镜头还需要某个道具的 `detail` 视图。未知道具 ID 或不存在的视角必须报错，不会猜测补图。

### 编译与安全阈值

- `reference_asset_preflight.status` 可报告 `preflight_only`，`ready_for_reference_preflight` 仅代表被声明的图像文件与元数据通过检查；**`human_visual_consistency_verified=false`、`media_generated=false` 永远不被当前脚本自动改成 true**。
- 当尚未配置参考目录，编译结果为 `not_assessed`；不应据此发起真实视频 API。
- 对缺失参考图仍允许保存离线导演提示词草稿，但不应启动真正的生成工具；将来若接入视频生成器，必须由它独立执行此门禁和用户费用授权。
- 自始至终不自动生成图片、不拷贝本机文件、不操作云盘、不发布视频。
- 目前只是 GitHub 源码阶段；必须等用户单独批准本地运行，才能用真实图像和镜头执行 preflight。

## 未来部署时的命令参考（**当前不要执行**）

```bash
python3 reference_assets.py scaffold --base plan.json --direction direction_v02.json --out reference_assets.json
python3 reference_assets.py audit --base plan.json --direction direction_v02.json --manifest reference_assets.json --asset-root PRIVATE_IMAGE_FOLDER
python3 director_v2.py compile --base plan.json --direction direction_v02.json --assets reference_assets.json --asset-root PRIVATE_IMAGE_FOLDER --out compiled.json
```

这些命令用于未来的私有本地目录，不属于当前 GitHub-only 阶段的执行要求。

**尚未完成**：真正的角色多角度参考图制作、镜间姿势控制、图片一致性视觉检测、供应商图像/视频 API 接口、生产实际镜头、后期合成与人审。
