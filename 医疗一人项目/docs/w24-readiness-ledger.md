# W24 试点就绪与覆盖账本

日期：2026-11-07（Pacific/Auckland）。

状态：工具与基线已实现；W24仍为PREPARED，没有现实联系、授权、执行、交付或
验收。本账本只验证声明结构和引用完整性，不认证证据真实性，也不自动完成
第一阶段。

## 用途

固定16个研发环节，持续回答：

- 哪些环节已设计、内部演练、接触、授权、执行、交付或验收；
- 每个外部动作是否有总授权、执行、交付和验收引用；
- 哪些内部环节需要以具体理由标记不适用；
- 当前缺口、负责岗位和下一现实动作是什么。

W24当前基线：

- `fixtures/w24-pilot-baseline.json`；
- 16/16环节有声明；
- 0个环节具有真实证据；
- 16个缺口保留；
- `phase_one_complete=false`；
- `human_confirmation_required=true`。

## 证据等级

| 等级 | 最低结构要求 |
| --- | --- |
| not_started | 保留缺口 |
| designed | 设计或合同存在 |
| mock_rehearsed | 软件内合成演练 |
| contacted | 真实通信/联系证据引用 |
| authorized | 真实证据 + 对象/范围/金额/有效期授权引用 |
| executing | 上述 + 实际执行引用 |
| delivered | 上述 + 原始交付引用 |
| accepted | 上述 + 指定责任方验收引用 |
| not_applicable | 具体研究范围和不适用理由 |

任何真实等级缺少对应引用时，Pydantic合同直接拒绝。即使全部环节声明为
accepted，报告也只到`declared_complete_pending_human_review`，不会自动把
`phase_one_complete`设为true。

## 运行

```bash
make pilot-readiness
```

或：

```bash
uv run --project services/core --frozen python tools/evaluate_pilot_readiness.py
```

替换输入时使用`--input <json>`。输出包含required/declared步骤、真实证据步骤、
缺失步骤和全部缺口。

## 升级规则

1. 发起人先确认具体候选、物种/场景、目标市场、资源、资料截止、成功/停止
   条件；
2. 联系、授权、执行、交付和验收各自新增真实引用，不能用一个“合作中”状态
   合并；
3. 外部事实与数据库状态分开核对；本地回滚不撤销已发生的外部动作；
4. 人工确认被引证据后才能修改阶段结论；
5. 科学阳性、流程通过和现实合作分别评价。

## 当前未覆盖

- 没有发起人选定候选或现实预算；
- 没有真实专家、CRO/CDMO/SMO/中心实验室接触或报价；
- 没有合同、付款、实验、原始数据或现实验收；
- 工具不能识别伪造引用、篡改原件或未披露冲突；
- 不扩大本轮任何外联、采购、发送或实验授权。
