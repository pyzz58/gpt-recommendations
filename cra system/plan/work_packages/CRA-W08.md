# CRA-W08 实现检验源文件自动读取与EDC核对

本页由plan/tasks.json生成；目标文件和待实现命令是执行约定，不表示功能已经完成。

状态：planned；分支路线：v1a。
前置：CRA-W06、CRA-W07。必须按实际verified状态核实。

## 临床工作目标

自动承担最耗时的检验抄读和对照，给出一致性/逻辑差异并把安全线索交给M09，减少CRA总工作量。

## 对应理论和模块

理论：[CRA-R013](../../theory/REQUIREMENTS.md#cra-r013)、[CRA-R015](../../theory/REQUIREMENTS.md#cra-r015)、[CRA-R016](../../theory/REQUIREMENTS.md#cra-r016)、[CRA-R017](../../theory/REQUIREMENTS.md#cra-r017)、[CRA-R034](../../theory/REQUIREMENTS.md#cra-r034)、[CRA-R035](../../theory/REQUIREMENTS.md#cra-r035)、[CRA-R038](../../theory/REQUIREMENTS.md#cra-r038)

模块：[M08](../../architecture/modules/M08-laboratory.md)、[M12](../../architecture/modules/M12-providers.md)

先读对应模块设计及architecture/DATA_MODEL.md、API_CONTRACTS.md；实现接口变化时同步这些契约。

## 要创建或修改的目标文件

| 路径（相对cra system） | 类型 | 用途 |
| --- | --- | --- |
| `backend/cra_app/laboratory/models.py` | code | 报告、确认、匹配和比较 |
| `backend/cra_app/laboratory/matching.py` | code | 对象和重复实例匹配 |
| `backend/cra_app/laboratory/comparison.py` | code | Decimal与单位/逻辑比较 |
| `backend/cra_app/laboratory/service.py` | code | 确认、跳过及结果复用 |
| `backend/cra_app/laboratory/api.py` | code | 源字段和核对接口 |
| `web/src/features/laboratory/LabComparison.tsx` | code | 并排核查 |
| `tests/integration/test_laboratory.py` | test | 错配、单位、边界和跳过 |
| `backend/cra_app/providers/lab_ocr.py` | code | 首版实际检验读取适配，可替换实现 |
| `backend/cra_app/laboratory/recognition.py` | code | 自动作业、字段提取和源定位 |
| `web/src/features/laboratory/RecognitionReview.tsx` | code | 集中复核低可信/歧义，不要求逐字段点击 |
| `tests/integration/test_recognition.py` | test | 文件读取、关键错误、失败和跳过 |
| `validation/LAB_AUTOMATION_SCOPE.md` | document | 支持格式、实际provider证据、人工负担与限制 |
| `backend/cra_app/providers/evaluate_labs.py` | code | 实际文件识别/匹配/比较和人工负担评估入口 |

以上是计划位置。落地时如需调整，更新同一tasks.json和相关契约，再生成本页；不能只保留一份过时路径说明。

## 关键接口和数据约定

- RecognizeLab返回有原文/坐标的候选字段、provider版本、结构校验和失败，SupportProfile明确支持格式及评估范围。
- LabComparison返回match_status、field_results、unknowns及scope；自动候选与CRA核实状态分开。
- 自动提取通过身份/结构校验后可比较，低可信/歧义集中复核，正常范围可批量确认；不得要求全量手抄或逐字段机械点击。
- 手动为少量例外；用户拒绝缺失数据或不用管时执行有范围的CheckDecision，不反复追问，不计正常。

## 进入条件与交接

阶段：P3；CI profile：CRA-W08

- 进入：W06/W07通过；W03探测已给出可安装、可运行的识别候选，支持格式和代表性评估输入已确定。
- 交接：自动源文件读取→匹配→比较→差异/未知与待办、实际provider证据、人工负担和支持范围。

技术输入：[LAB_AUTOMATION.md](../../architecture/LAB_AUTOMATION.md)、[EXECUTION_CONTRACTS.md](../../architecture/EXECUTION_CONTRACTS.md)、[VALIDATION_AND_RELEASE.md](../../architecture/VALIDATION_AND_RELEASE.md)、[REUSE_ASSESSMENT.md](../../architecture/REUSE_ASSESSMENT.md)


## 实现步骤

1. 复用W03实测选择的PaddleOCR/结构识别适配器（或有证据更合适的Docling）接源文件→字段/坐标→原匹配比较服务，不自写OCR或表格结构引擎。
2. 匹配中心、患者、时间、项目、样本、访视、初检复查和报告修订；歧义不按数值近似挑选。
3. 用Decimal及批准映射比较，保留大于小于等符号，未知单位不猜换算。
4. 分别返回一致、差异、单位待核实、本次未见、无法识别和跳过，限定结论范围。
5. 并排查看和记录差异，关联M06待办，不直接自动认定PD或临床安全。
6. 评估候选OCR/多模态接入的格式效果与授权条件，不绑定未验证供应商；记录支持范围和关键字段错误。
7. 集中展示低可信/歧义/差异，已通过校验字段自动比较候选；人工更正只重算相关结果。
8. 明确code/synthetic/provider验证等级；provider缺失只记录接口/人工兜底，不得把W08核心自动能力标验证完成。
9. 并排核对表格复用AG Grid Community，源PDF复用React-PDF；只定制匹配、差异展示与坐标映射，不用组件排序/编辑结果替代服务端事实。

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

- [to_implement] 匹配、单位、精度及人工路径

```bash
uv run --frozen pytest -q tests/integration/test_laboratory.py
```

- [to_implement] 检验文件实际自动读取与原核对管道

```bash
uv run --frozen pytest -q tests/integration/test_recognition.py
```

- [to_implement] 实际识别到自动核对的独立样本评估

```bash
uv run --frozen python -m cra_app.providers.evaluate_labs --dataset tests/fixtures/manifest.json
```

## 完成标准

原工作包验收：支持格式的检验源文件自动提取/定位后，与EDC Excel先匹配再核对；集中复核低可信、歧义和异常，少量失败才补录或跳过。

- 初检、复查和修订不误配，多候选明确待核实。
- 带比较符结果不被猜成精确值。
- OCR关闭仍可工作，用户跳过后不重复追问且报告不写正常。
- 真实可读的合成检验文件和EDC Excel从上传走入自动提取、匹配和差异记录；不是只预造字段JSON。
- 自动支持范围、人工更正/补录比例及总复核负担有实际记录；未测项明确未验证。

关联完整场景：CRA-S13、CRA-S19、CRA-S20、CRA-S21、CRA-S22、CRA-S36、CRA-S39。局部测试通过不自动把全部场景标为verified。

## 本步不包含

- 不扩展用药/样本OCR；不宣称支持所有医院版式、模糊图像或最终医学安全判断。
- W14只增强复杂格式，不能用于后置本任务第一次自动读取。

## 完成后必须记录

- 实际修改/创建的代码、迁移和接口路径；不只提交说明或空壳。
- 实际执行的命令、结果及GitHub Actions链接；未运行或服务缺失如实列出。
- 可复现的合成操作结果和剩余限制；任务状态与实际证据一致。
- 将已实现命令更新为available，补充evidence，生成可读视图并通过同步检查。
- 仅按约定交付此项；下一项由tools/next_task.py定位，不跳过失败或阻塞项。
