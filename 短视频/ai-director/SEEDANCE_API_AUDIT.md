# API 路线审查与第一条视频链路

日期：2026-10-12。源码基线 a2bb380938de025ba6d960066700f63b73128d67；代码修复 49702712088d829a5a684ee0880dc164900c18eb。

## 结论

用户愿景是“输入文案，由系统完成导演设计，并在系统内通过第三方 API 制作、审片、返工和合成短视频”。此前文档将终点限定在导演图纸，属于产品方向落后于用户决定；现已统一修正。现有专业分工与编译器可保留，缺的是可靠的媒体制作衔接和实际作品验证，不需要继续增加通用框架。

本次审查覆盖目标定义、文案/专业交接、时间线与对白、供应商请求、任务状态、保存与重复提交、参考图、媒体质量和最终合成。使用公开虚构样例、代码阅读、官方接口资料及离线回归；没有评估未部署服务的真实安全性或任何真实视频质量。

| 发现 | 证据与本轮处理 | 状态 |
| --- | --- | --- |
| 产品终点停留在图纸 | PRODUCT_NORTH_STAR/README/计划及 AGENTS 原指令；改为 API 制作到成片 | 文档已纠正 |
| 制作包遗漏精确对白 | production_delivery 只传旁白/字幕，director_v2 后期单未带 speech；现在完整深拷贝对白、配音与时间 | AUD-027 回归修复 |
| 出镜/画外对白在时间线混同 | sync_dialogue 原先只保留人物/文本/表演；现在保存 kind 并派生 lip_sync_required，旧数据明确 unknown，非法类型阻断 | AUD-028 回归修复 |
| 没有真实视频网络接头 | 现有候选提示词无法提交；新增 seedance_adapter 单镜函数 | 最小接口已完成，未运行真实请求 |
| 多段镜头不能直接当单镜发送 | split_stitch 与单连续提示词不匹配；适配器只接 single_take，复杂分段拒绝并待后续设计 | 能力边界保留 |
| 参考素材只是元数据 | 当前清单不能自动给供应商提供实际文件；适配器可接显式审阅 HTTPS 图片 URL，但未连接上传、资产哈希及权利链 | AUD-003 仍开放 |
| 供应商成功不能当审片通过 | 保存回执和文件，不标记人审/完整解码/最终成片完成 | 实际音画仍待验证 |
| 缺少整片输出闭环 | 没有真实片段解码、实测时长回写、合成渲染及成片验收；时间线只是计划 | AUD-029 确认开放 |
| 十岗位真实创作质量尚未证明 | 两个完整样例来自当前会话创作，不能充当自动团队质量证据 | 继续追踪，不虚报 |
| 私人生产运行条件不足 | 存储、真实身份、账单核验和恢复等旧生产问题未部署验收 | AUD-002 / Issue #1 继续 P0 |

9:16 是当前基础计划明确支持的 MVP 范围，不能把适配器不支持横屏另报成已有回归缺陷。

## 已实现的单镜范围

[seedance_adapter.py](seedance_adapter.py) 提供四个函数，均不在导入或 CI 时执行网络：

- prepare_shot：离线严格编译完整导演稿，生成可审阅请求并绑定原计划/方向稿摘要；支持 4–15 整数秒、720p、9:16、single_take 的 AI 视频镜头。该范围是项目主动缩小的子集，不是供应商全部能力。
- submit_once：接受外部真实操作者已批准的准确请求与费用估计，先保存私有 intent，再发一次 POST 并保存任务 ID。每个任务目录一旦存在 intent 就不能重发；超时、回复不完整或回执保存失败只允许人工核对，不能用换目录当重试。没有跨目录/跨主机全局去重，也没有供应商幂等保证。
- query_once：只对已存 ID 发 GET，识别 queued/running/succeeded/failed/cancelled/expired。成功时核对任务和模型并保存结果，失败不自动付费重做。
- download_result：仅允许配置中已审阅区域的 HTTPS TOS 子域，不转发 API Key、不跟随重定向，检查声明长度/实际长度、256MiB 上限和 MP4 容器标识后私有保存，记录 SHA。其它官方区域/CDN 也可能合法，但当前会拒绝，需核实后扩充，不能临时取消限制。

原生对白模式显式开启 generate_audio，要求逐句出镜/画外类型并传递原句；有 VO 的镜头暂不走此模式。静音模式保留全部 speech 给后期。原生声音仍须检查是否说错字、谁开口、停顿和口型，不能再叠一份相同配音。

私有目录 0700、文件 0600 与 fsync 是当前进程内保存措施；请求 SHA 不是认证，approval 字典不是账户鉴权，quoted_cost/max_cost 是人工估计与意图字段，不是供应商硬性消费上限。禁止把此模块直接暴露为公共 HTTP 服务。尚无 UI、自动执行器挂接、长期存储、账户额度控制、字幕烧录、音频混音或影片渲染。

## 可以直接审阅的第一镜

[《先吃饭》S02 API 请求候选](examples/dinner-dialogue-review/seedance_s02_request.json)：8 秒，母亲问句，9:16、720p，Volcengine 配置、原生对白。精确提示词、台词/时间、后期任务及来源摘要均已写入，未包含 Key、实际素材 URL 或费用批准。

当前无人物参考图，scope=reference_free_technical_probe。它只能成为接口与对白技术试验，不能代表双人跨镜一致性；正式作品试制前还须锁定两人和场景参考。BytePlus 是另一套区域配置，不会因火山账号失败而自动切换发送。

下一步顺序：可信私人运行环境与账号区域/模型开通核对 → 确定这一镜的实际报价、费用额度与素材传输授权 → 一次真实 S02 生成并及时保存 → 对照台词、口型、动作、轴线、声音及实测时长审片 → 通过后加入 S03 验证跨镜 → 接入字幕/声音/剪辑合成。失败只针对已确认原因修镜并重新获准费用，不整片盲目重跑。

## 官方合同与开源选择

核对官方资料及官方 SDK 后采用异步 task 合同：

- [火山视频生成教程](https://docs.volcengine.com/docs/ark/video-generation-tutorial?lang=zh)：创建任务、查询并下载输出；模型和区域以实际开通为准。
- [火山创建视频任务 API](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh)：内容数组、图片 role、音频参数等。
- [火山查询任务 API](https://www.volcengine.com/docs/82379/1521309)：任务状态与结果；结果链接有效期有限，应及时下载，不能当永久素材库。
- [官方 Python SDK tasks.py](https://github.com/volcengine/volcengine-python-sdk/blob/master/volcenginesdkarkruntime/resources/content_generation/tasks.py) 与 [_constants.py](https://github.com/volcengine/volcengine-python-sdk/blob/master/volcenginesdkarkruntime/_constants.py)：核实 create/get 和默认重试，选择不重试的薄 HTTP 适配。完整取舍见 [复用决策](GITHUB_REUSE_POLICY.md)。

配置记录的模型：Volcengine doubao-seedance-2-5-260628、BytePlus dreamina-seedance-2-5-260628。区域主机和模型不能混用；文档支持不保证用户账号已开通，具体可用性和费率仍未实测。

## 验证结果及边界

隔离 Linux / Python 3.12：全量 **592 tests PASS**，含新增 **19** 项。测试覆盖对白交接和类型、原生声音请求、请求篡改及超出子集、未批准/费用估计异常、私有权限、写盘失败、提交超时阻断、回执失败、只 GET 查询、错误任务/模型、下载域名、重定向、截断/过大与容器标识。全部供应商网络均为 mock；合成字节不是真实视频，不证明解码或艺术质量。GitHub CI 以本次 main 提交对应 Actions 为准。

本轮没有真实 API 调用、用户私稿外传、收费生成、Mac 部署或作品发布。原有未解决事项不因接口代码完成而关闭。
