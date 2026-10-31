# 后端实施区域

`cra_core`保留分项整改、PD上报、访前选择、历史快照和有限检验比较示例。CRA-W01已建立`cra_app/governance`的PostgreSQL项目/中心授权、显式修订、幂等、审计事务及真实数据库迁移测试；尚无正式OIDC、FastAPI、OCR、医学分析或生产文件存储，不能放入真实临床数据。

完整应用继续按architecture/modules登记的`cra_app/{module}/`结构实现，FastAPI只做传输和验证，业务服务与provider分开。W01服务只解决共用权限、幂等、并发修订与审计底座，不代表后续业务模块或正式身份服务已经完成。

执行合成示例：在cra system工作目录中用PYTHONPATH=backend python3 -m cra_core.demo。
