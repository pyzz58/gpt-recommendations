# 契约区域

当前为计划入口，没有伪造已实现的OpenAPI或前端类型。

W02从实际FastAPI应用导出openapi.json，再生成web/src/api/generated.ts并实现api:check。以后每个模块新增或更改接口，都同步生成契约、消费者和有意义的兼容测试。不可同时手写两份互相不同的DTO定义。

架构层字段和行为先遵循architecture/API_CONTRACTS.md及DATA_MODEL.md。实际领域对象的JSONSchema/Pydantic模型由各工作包实现，保留来源、适用性、未知状态和版本语义；模板文件存在不证明业务契约已经实现。
