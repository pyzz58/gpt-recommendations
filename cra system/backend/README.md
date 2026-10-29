# 后端实施区域

当前只有cra_core中的纯Python示例：分项整改任务、PD上报确认、访前选择、历史快照和极小范围的检验字段比较。用于验证约束，**没有身份、数据库、API、OCR、医学分析或生产文件存储**，不能放入真实临床数据。

完整应用在CRA-W01之后按architecture/modules登记的cra_app/{module}/结构实现，FastAPI只做传输和验证，业务服务与provider分开。首批cra_core示例可吸收进入对应域模块，不能据此把任何完整模块标成实现完成。

执行合成示例：在cra system工作目录中用PYTHONPATH=backend python3 -m cra_core.demo。
