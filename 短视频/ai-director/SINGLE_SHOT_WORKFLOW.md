# 单镜制作操作流程

2026-10-12。基线提交 3967567f2efb68e625c094ff17d791748cd9402d。本轮把独立 Seedance 函数接入既有 local_director 的 video 子入口，增加只读审阅页面和绑定视频的审片记录。代码已接通；尚未部署到用户电脑或私人服务器，没有真实 API 请求。

## 本轮可以做什么

同一任务目录完成：离线准备 → 明确提交一次 → 明确查询 → 下载 → 完整观看 → 记录保留/修改/弃用。没有后台循环、默认网络请求、自动重发或付费返工。操作入口是命令行和函数，不是已经完成的网页控制台。

[公开虚构 S02 请求审阅页](examples/dinner-dialogue-review/video_review.prepared.html) 展示 8 秒母亲问句、说话人、出镜对白、计划时间、完整生成指令与后期安排。该 HTML 是可用浏览器阅读的独立文件，GitHub 源码页可能显示 HTML 文本。页面明确显示尚无视频，无占位片段，不包含密钥、素材 URL 或真实任务数据。

## 操作合同（未来私人运行环境的开发参考）

入口 local_director.py 的 video 子命令转交 video_workflow.py；现有文案创作/预演入口保持原样。本节不是要求用户现在安装、运行或部署。

| 子命令 | 输入 | 结果与限制 |
| --- | --- | --- |
| prepare | base、direction、shot、provider、audio-mode、job，可选 reference-image | 严格编译，写入空的0700私人目录中的 proposal.json；不请求模型，不能覆盖旧任务 |
| status | job | 读取本地凭据和最近查询记录，明确不是供应商实时状态；不联网 |
| page | job | 生成0600只读 HTML，显示台词/计划/状态；视频保存且哈希正确后才显示本地播放器；无API按钮 |
| submit | job、私有approval文件、execute-reviewed-request明确开关 | 通过不回显的交互终端读取Key，调用原适配器一次；无环境Key自动读取，禁止命令行参数传Key |
| query | job | 交互读取Key，仅对已有任务GET一次；保存带时间的查询记录，不重发POST |
| download | job | 从已保存的成功结果下载，不向视频主机发送API Key；保存失败需核对 |
| review-template | job | 仅在视频已保存后生成review.draft.json，自动带请求/视频摘要，默认全部未检查，不是批准 |
| review | job、私有record文件 | 导入人工完整观看后的审片记录；一镜一个不可覆盖的决定，不触发重做或成片发布 |

页面是查看和播放入口，审片信息当前通过私人JSON草稿录入；浏览器内填写/保存、身份认证及服务端部署尚未实现。这里不掩盖这一步仍需开发者操作的事实。

审片字段：request_digest、media_sha256、reviewer、watched_full_clip、observed_duration_s、decision、checks、notes。decision 可选 retain_candidate/revise/reject；checks 包含 story_action/framing/dialogue/lip_sync/audio/timing/character_consistency，值为 pass/fail/not_applicable/not_checked。保留候选必须全部完成且无失败，故事动作/构图/时长必过；原生对白还要求台词/声音必过，出镜对白口型必过，不可用“不适用”绕过。

observed_duration_s 为人工填写，不是 ffprobe 实测；reviewer 是操作者声明，不是认证身份。视频 SHA 绑定只检测替换，不证明视频解码有效或审阅意见客观正确。所有状态始终 production_approved=false、final_film_completed=false；无参考图的技术候选尤其不能算正式人物一致性验收。

## 结果与恢复

- intent 已写但回执缺失：显示提交结果不明，不能重发或复制到新目录绕过；须核对供应商任务与账单。
- 查询失败：保留原凭据与最近成功查询记录；status 仍明确是本地状态。
- 视频与media.json未同时完整保存：显示save_incomplete，不能审片或再下载覆盖；先人工核对。
- 视频替换/损坏：摘要和长度复核失败，旧审片记录不能继续使用。
- 审片要求修改：保留意见，不自动重做；后续仍需镜头修订、版本选择和新的具体费用授权。
- 生成页面按内容产生新文件名，不覆盖已有人工修改页面；新状态需重新生成页面，不会自行实时刷新。

长期存储、备份、账号权限、费用硬额度、供应商账单恢复、跨目录去重仍属于未完成生产条件，AUD-002 和 AUD-029 不关闭。PRIVATE_RUNTIME 和 UI 不能靠新增开关字段冒充已部署。

## 实际验证

隔离 Linux/Python 3.12 全量 **609 tests PASS**，含新增 **17** 项。模拟完整prepare/submit/query/download/review、超时不重发、历史查询状态、视频被改后审片失效、部分保存阻断、草稿未填不得通过、原生对白不能跳过口型、HTML转义、统一入口路由、不回显输入降级阻断及错误不泄露内容。

合成字节仅验证文件传输和状态衔接，不是有效短片、真实播放或口型测试。没有真实模型、真实费用、私稿传输或Mac操作。GitHub CI 以本轮提交对应 Actions 为准。

## 开源选择与下一步

核对 CPython 3.12 getpass.py 的无法禁用回显时退化行为，选择将 GetPassWarning 作为错误拒绝；沿用已有 argparse，不增加 Click 依赖，详见 [复用决策](GITHUB_REUSE_POLICY.md)。未复制上游实现、未新增运行依赖。

接下来落实账号区域、可用模型、这一镜的报价/预算和可信私人运行环境，执行一次 S02 实测。随后接人物/场景参考和 S03，最后补齐镜头版本、真实解码与时长回写、配音字幕及合成。未经这些实际结果，不宣称整套系统已完成。
