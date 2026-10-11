# 生成前门禁 · Fail-closed Production Gate（GitHub-only）

> 状态：源码已经写入 GitHub；仅用于**离线检查导演编译工作包**。没有启动器、没有实际图片/视频生成器、没有外部 API 请求、没有部署用户 Mac。**任何 JSON 报告都不能单独代表用户允许付费或发布。**

## 为什么需要它

第三阶段导演稿可以分成 AI 视频、静态后期、剪辑合成和实拍镜头；第四阶段参考资产系统可以声明人物、场景、道具所需图片。问题是**“已经计划好了”不等于“素材准备完毕”**。导演编译器曾能输出可用的候选模型提示词，但有提示词不等于允许自动把它们送给付费服务。

新模块 `production_gate.py` 执行**无副作用**审查；`director_v2.compile_package()` 在编译结果附加 `generation_gate` 报告。

## 阻断条件

| 检查对象 | 何时阻断 |
|---|---|
| 结构和版本 | 输入不是有效编译包、镜头为空或编号重复 |
| 路由 | 任何镜头的 `execution_route` 不在已批准的规划路由内 |
| 导演人审 | `human_review_required` 不存在/不为 true，或 `direction.qa.human_approved` 尚未为 true |
| 参考资产 | AI 视频/静态后期镜头未通过目录校验，或者 `reference_preflight_ready` 不为 true |
| 真正交付参考媒体 | `reference_media_supplied` 不为 true（本阶段编译器永远标 false，因为它没有向模型实际上传图片） |
| 候选视频提示词 | 选了 AI 视频但没有非空候选 prompt |
| 非视频路线 | 后期/实拍镜头错误地携带视频模型 prompt，或者缺少后期工作单 |
| 全局状态 | 标记为“已生成/可发布”、或者生产路线数量和实际镜头不匹配 |

门禁输出的 `blocker_count` 明确报告问题；`metadata_preflight_passed` **只表示部分离线结构审查**，不是已经通过真实画面、人脸、版权和费用审查。

## 不可绕过的授权边界

```json
{
  "status": "offline_review_only",
  "execution_authorized": false,
  "paid_api_enabled": false,
  "publishing_authorized": false
}
```

这三个安全字段在当前模块中**恒为 false**；即使把输入 JSON 的 `qa.human_approved` 人为改成 true，或者完整填写来源与哈希，也不会变成 true。真实视频供应商接入时，必须另做**运行时**授权/预算检查，核查用户当次同意的服务、金额、调用次数、视频模型和私人参考图传输，并拒绝通过篡改 JSON 激活付费行为。

注意：`human_approved=true` 是**人工审查记录字段，不是可验证的数字签名**，不能被当成用户当次资金授权。

## 提前发现场景风险

- S09/S10 复杂交互：即使 JSON 连续性为零阻断，还必须做图像参考资产和最终画面的人审。
- 没有真正产生人物参考图：目录中 `not_created` -> 门禁阻断。
- 参考图文件存在但版权仍未确认：门禁阻断，必须核验来源及授权。
- 静态图+后期镜头：没有素材时仍被门禁阻断；**但不会被误当成视频模型调用**。
- 老导演档没有参考目录：仍允许编译**文字制作草稿**，`reference_asset_preflight.status=not_assessed`，门禁阻断。

## 测试与开发状态

测试文件为 `tests/test_production_gate.py`（11 项新回归用例，覆盖伪造安全状态、未交付参考图、缺失人工审查、路由错误和真实公开示例的编译器接口）。隔离开发环境已对 83 项旧基线 + 10 项门禁独立测试完成运行：93 项通过；GitHub 最新资产模块和新增第 11 项编译器联动测试尚未在完整最新快照执行，**不得夸大为全套回归通过**。

## 未来调用示例（仅文档，当前不要在 Mac 执行）

```bash
python3 production_gate.py --compiled compiled_director_package.json
```

它只是读取 JSON 并打印报告；无法真正付款、生成参考图或成片。只有用户未来明确批准正式部署，才可能进入真机测试阶段。
