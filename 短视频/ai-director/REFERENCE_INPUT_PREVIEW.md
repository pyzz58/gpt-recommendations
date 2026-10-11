# 视频模型参考图输入适配（GitHub-only）

## 当前目标

本模块 `reference_input_preview.py` 把已经设计好的镜头、制作路线与参考资产清单，转换成**供应商无关的输入需求预览**。它只整理资产 ID、所需视角和用途，不读取图片、不输出私有文件路径、也不包含图像二进制内容。

这不是 Wan、Seedance 等服务的真实 API 请求格式；没有选择模型、没有 provider 参数、没有身份认证、没有真实图片上传，也没有发起 API 调用。

## 参考的成熟 GitHub 方案

- [CineCrew](https://github.com/Ironieser/CineCrew)（Apache-2.0）：在一个结构化规格中维护角色、场景、道具资产引用和每镜镜头约束；本项目只借鉴稳定 asset_id + shot bindings。
- [AI Cinematic Pipeline](https://github.com/billpar/ai-cinematic-pipeline)（MIT）：人物转面参考图与场景/道具资产分层，模型生成与素材制作分开。未复制源代码、未安装模型权重。
- [python-jsonschema](https://github.com/python-jsonschema/jsonschema)（MIT）：建议参照已提交的 `schemas/reference_assets.schema.json` 定义并检验数据类型，但当前运行时不强制安装依赖。

## 输入

- 基础分镜 `plan.json`（含角色 ID 和场景 ID）
- 导演方向 `direction_v02.json`（含实际 `generation.route`，可选 `generation.reference_bindings`）
- 私有参考资产目录 `reference_assets.json`（人物正面/3/4侧面/全身，场景 establishing，道具 detail）

程序必须先调用 `director_v2.validate(..., catalog)`。如果资产绑定引用不存在，审批字段矛盾，或严重安全检查失败，则**直接拒绝创建预览**。如果只是参考图尚未制作，可以创建待补全清单，但它会显示 missing，不会把图像状态标为已准备就绪。

## 输出示例

```json
{
  "kind": "offline_reference_input_preview",
  "model_provider": "not_selected",
  "actual_provider_request": false,
  "private_paths_included": false,
  "media_bytes_included": false,
  "images_uploaded": false,
  "user_payment_authorized": false,
  "reference_preflight": {
    "blockers": 0,
    "missing": 5,
    "files_verified": false,
    "identity_consistency_verified": false
  },
  "jobs": [{
    "shot_id": "S01",
    "execution_route": "ai_video",
    "reference_requirements": [
      {"asset_id": "CH_MAIN", "view": "three_quarter", "role": "identity",
       "asset_kind": "character", "catalog_status": "not_created",
       "media_bytes_included": false, "reference_uploaded_to_provider": false,
       "provider_binding_verified": false}
    ],
    "runtime_input_ready": false,
    "upload_authorized": false,
    "paid_execution_authorized": false
  }],
  "runtime_execution_allowed": false
}
```

这里是示例片段，完整文件还有版本和安全说明。即使目录里的参考图已人工标为 approved，该预览也**不会**改写为可以上传或调用付费服务。未来如果接入真正的供应商适配器，需要严格验证版本、隐私和供应商参数，并由用户在当次执行前单独明确批准上传与具体人民币预算。

## 测试与安全边界

`tests/test_reference_input_preview.py` 包含 9 项**新增待运行**的回归测试：镜头顺序、资产 ID、离镜人物不误绑定、私有路径/来源不泄露、旧制作路由兼容、无效资产拒绝、输入只读、候选清单不覆盖等。

截至本次提交，GitHub 最新源文件全量快照尚未在同一测试环境执行完整测试。本阶段仅确认已成功提交源码与测试用例，不能声称它在你的 Mac 上工作。

### 未来运行示例（当前不要执行）

```bash
python3 reference_input_preview.py \
  --base plan.json \
  --direction direction_v02.json \
  --catalog reference_assets.json \
  --out reference_input_preview.json
```

命令属于未来经用户批准后的私有运行过程。GitHub-only 阶段**不要求你同步、下载或运行**，也不上传私人素材。
