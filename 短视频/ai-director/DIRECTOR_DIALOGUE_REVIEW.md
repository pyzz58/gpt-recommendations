# AUD-026：正常表演用语被当成占位符

## 复现与影响

编写公开虚构对白样例《先吃饭》时，director_v2.validate 拒绝“母亲闭口等待”“保留三秒等待”“闭口等待，肩膀稍松”等已写好的表演。原因是全局方向和逐秒节拍用单字“待”判断未完成内容。“时间窗口待实录校准”也会被误判，导致完整文字方案无法编译。

## 最小修复

复用同模块已有明确占位标记检查思想，集中为 _has_unfinished_placeholder：只查“待填”“待导演”“待设计”“待确认”“TODO”“TBD”，递归检查全局字段值，不再将所有含“待”的汉字句子拒绝。基础格式、时间范围、留白限制和真正脚手架占位仍检查。这是明确标记规则，不是自然语言质量理解。

新增两项回归覆盖正常“等待/期待”、诚实的实录校准说明，以及五种占位标记仍遭拒绝。已有 scaffold 不可交付测试继续保留。变更范围仅 director_v2.py 和对应测试，无新依赖。

## GitHub 参考与取舍

核对 [python-jsonschema 的关键字校验实现](https://github.com/python-jsonschema/jsonschema/blob/main/jsonschema/_keywords.py) 和 [Pydantic 的类型定义模块](https://github.com/pydantic/pydantic/blob/main/pydantic/types.py) 的公开源码入口；本次问题是既有中文占位判据过宽，并非缺少 Schema 库。选择修订已有判据，不复制第三方源码、不引入库或改变模型编排。未作完整上游许可证/供应链接入审查，因为没有引入新依赖；不宣称已经融合这两个项目。

## 作品交付与边界

[48秒、6镜头完整样例](examples/dinner-dialogue-review/director_workbook.md)包含一句女儿回忆VO、五句对白，其中一处母亲画外对白、四处出镜对白；额外提供[配音交接表](examples/dinner-dialogue-review/speech_handoff.json)和[计划字幕](examples/dinner-dialogue-review/subtitles.planned.srt)。

原文、逐镜语音、字幕窗口与说话人已核对；严格编译通过，六项未审阅提示保留。真实录音、语速、口型、画面与艺术效果尚未验证。sync_dialogue 是既有时间线字段名，包含画外对白，不能据字段名自动派发口型；本次用明确交接表和逐镜 lip_sync_policy 交付，未来应在现有结构中保留类型，不新增一套系统。

全量回归证据见本轮提交对应 GitHub Actions；不将缺依赖的失败尝试或只通过专项测试写成全量成功。


隔离 Linux/Python 3.12 补齐项目固定 jsonschema==4.25.1、Pillow==12.3.0 后，全量 **573 tests PASS**（首次尝试因临时环境缺依赖未通过，未记作代码缺陷）。代码提交 `62dd1046217387516fdc893b7714814fc369b85a`。GitHub CI 以该提交或后续仅文档提交的实际 Actions 状态为准。
