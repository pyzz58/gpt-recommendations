# CRA-W14 增强复杂检验格式与识别效果

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1b。
前置：CRA-W08。必须按实际verified状态核实。

## 临床工作目标

扩大已可自动读取的检验格式范围，进一步减少失败、补录和复核负担。

## 对应理论和模块

理论：[CRA-R013](../../theory/REQUIREMENTS.md#cra-r013)、[CRA-R015](../../theory/REQUIREMENTS.md#cra-r015)、[CRA-R016](../../theory/REQUIREMENTS.md#cra-r016)、[CRA-R017](../../theory/REQUIREMENTS.md#cra-r017)、[CRA-R034](../../theory/REQUIREMENTS.md#cra-r034)、[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R036](../../theory/REQUIREMENTS.md#cra-r036)、[CRA-R038](../../theory/REQUIREMENTS.md#cra-r038)

模块：[M08](../../architecture/modules/M08-laboratory.md)、[M12](../../architecture/modules/M12-providers.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/providers/lab_ocr.py` | code | 可替换OCR适配 |
| `backend/cra_app/laboratory/recognition.py` | code | 作业、图像区域和候选 |
| `web/src/features/laboratory/RecognitionReview.tsx` | code | 原图字段复核 |
| `tests/integration/test_recognition.py` | test | 误识别、失败和替换 |
| `validation/OCR_EVALUATION.md` | document | 字段错误和复核负担 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- RecognizeLab输出候选、图像区域及版本/失败，不直接写成已确认事实。
- 确认或跳过后接M08现有服务，不另建比对系统。

## 进入条件与交接

阶段：P6；CI profile：CRA-W14

- 进入：W08已有自动读取，当前范围的错误及负担记录可复用。
- 交接：复杂格式新增SupportProfile和独立回归；既有业务数据不变。

技术输入：[LAB_AUTOMATION.md](../../architecture/LAB_AUTOMATION.md)、[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 在W08已有adapter和SupportProfile上评估复杂版式、图像质量及更多格式，重新核对许可/成本/授权条件。
2. 保存图像位置、候选和识别状态，重点可复核小数点、单位、比较符和实例。
3. 按同一校验/集中复核策略进入原比对，少量失败可补录或按用户选择跳过相关路径。
4. 更换provider不覆盖已确认事实；以字段错误及总复核时间评价。

## 验证命令

available表示当前已有入口；to_implement表示本任务必须先实现该入口，不能现在就声称已经运行。进入后续阶段使用合成数据和临时服务。

- [available] 理论/技术/任务卡同步

```bash
python3 tools/check_traceability.py
```

- [available] 现有基础与反例检查

```bash
python3 -m unittest discover -s tests -v
```

- [to_implement] 识别及人工退化

```bash
uv run --frozen pytest -q tests/integration/test_recognition.py
```

- [to_implement] 接入后的整体流程

```bash
npm --prefix web run test:e2e -- --project=chromium
```

## 完成标准

原工作包验收：V1B在W08已有自动读取基础上扩展难版式/图像，沿用同一字段、匹配和比较；按关键错误与总负担实测决定支持范围。

- 识别确实进入原比对服务，不重复建立问题和报告状态。
- 不支持格式明确提示，不预设未经验证的通用准确率。
- 人工确认和跳过路径保留，非检验源图不自动核对。

关联完整场景：CRA-S13、CRA-S19、CRA-S20、CRA-S21、CRA-S22、CRA-S30。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不后置第一次自动读取，不扩展用药或样本OCR，不重建核对/问题/报告系统。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
