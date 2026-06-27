# SIREN 智能物理实验平台

基于 FastAPI、Vue 3、SIREN 与检索增强生成（RAG）的激光衍射实验平台。项目将图像分析、物理量计算、实验状态管理和 AI 实验 Agent 组织为可测试、可替换的应用服务。

## 架构

```text
Vue 3 + Vue Router
        │ HTTP / SSE / NDJSON
FastAPI API layer
        ├── Experiment Agent ── RAG ── OpenAI-compatible LLM
        ├── Diffraction Analysis Service ── SIREN / OCR / PINN regularization
        ├── Surface-tension Calculation Service
        └── Session Store (local adapter; replaceable by Redis/PostgreSQL)
```

核心边界：

- `backend/api/routes`：HTTP 协议、校验和响应契约。
- `backend/services`：图像分析、Agent、计算和状态持久化业务逻辑。
- `models`、`training`、`calibration`：与 Web 框架无关的科学计算代码。
- `frontend`：Vue 3 + TypeScript + Vite 前端。
- `tests`：API、数学计算、状态存储和模型梯度测试。

## 前端架构

所有页面均为原生 Vue SFC，不依赖 iframe、Jinja 或服务端模板。共享布局、实验状态、API 客户端和 AI 助手分别位于 `components`、`composables` 与 `api` 目录。Vue Router 保留旧页面 URL，因此原有书签和实验流程无需改变。

## 本地运行

要求 Python 3.10+、Node.js 18+。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `.env` 中填写 `MIMO_API_KEY`。未配置密钥时，图像与计算功能仍可使用，Agent 接口会明确返回 HTTP 503。

启动后端：

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

开发时访问 `http://localhost:5173`。执行 `npm run build` 后，FastAPI 会直接托管 Vue SPA，可通过 `http://127.0.0.1:8000` 访问。接口文档位于 `/docs`。

## 测试

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest
Set-Location frontend
npm run build
```

## 容器与持续集成

```powershell
docker compose up --build
```

容器以非 root 用户运行，并持久化分析输出和实验会话。`.github/workflows/ci.yml` 会在 push 与 pull request 时分别验证 Python 和 Vue 工程。

关闭 pytest 插件自动加载是为了避免全局 Conda 环境中的第三方 pytest 插件污染项目测试；独立虚拟环境通常不需要该变量。

## API

- `POST /api/laser-diffraction-stream`：上传图像并以 NDJSON 返回分析进度。
- `POST /api/calculate`、`POST /api/fit`：物理量计算与多组拟合。
- `POST /api/ask/stream`：RAG Agent SSE 流式对话。
- `GET|POST /api/experiment-state`：实验状态读取与保存。
- `GET /health`：服务健康检查。

## 工程决策

- 密钥只从环境变量读取，仓库不提供默认密钥。
- 上传文件按块读取并限制大小，文件名不进入服务端路径。
- 每次图像分析使用独立 `runId` 输出目录，避免并发请求覆盖结果。
- Pydantic 模型在 API 边界校验数值范围。
- Agent 与 HTTP 层解耦，便于替换模型供应商、增加工具调用或接入工作流引擎。

## 科学结果边界

输出的小数位数不代表真实测量精度。若要证明亚像素测量能力，需要提供带真值的数据集、重复测量统计、标定不确定度、消融实验及与传统峰值检测的对照结果。
