# CRA 浏览器工作台

React 19、TypeScript与Vite构成的工作台外壳。W02已实现合成身份登录、授权项目/中心选择、刷新后恢复上下文、统一错误状态及真实能力状态。访前、遗留、受试者、检验、目录和报告页面仍由后续工作包实现。

接口类型只从`../contracts/openapi.json`生成，不能手写第二套响应类型。项目/中心上下文保存在浏览器仅用于选择，服务端仍根据可信会话和数据库授权决定可访问范围；模型及OCR密钥不进入浏览器。

```bash
npm ci
npm run typecheck
npm test
npm run build
npm run api:check
npm run dev
```

开发代理默认连接`http://127.0.0.1:8000`，可通过`CRA_API_PROXY_TARGET`改为其他本地端口。页面不得把“服务在线”或“provider已配置”显示为自动临床能力已经完成。
