# SIREN 约束拟合智能实验系统

面向液体表面张力实验的 AI 辅助测量与教学试点软件。系统使用 EasyOCR 建立标尺映射，以 SIREN 连续拟合光强剖面，并通过光滑与弱对称先验抑制噪声伪峰；随后由含重力项和有限液深修正的色散关系计算表面张力。

当前实现不是控制方程 PINN，也不声明未经盲测验证的固定测量精度。演示教师数据为确定性合成数据，不代表真实课堂效果。

## 已实现范围

- 单张衍射图像上传、标尺识别、连续坐标峰位估计和质量指标输出。
- 重力—毛细波完整色散计算、非物理解拒绝与多组最小二乘拟合。
- 预习、采集、计算、拟合、实验状态保存及 RAG 实验助手。
- 教师工作台、关注项处理、干预任务下发/完成和审计记录。
- SQLite 事务存储、签名 HttpOnly 教师会话、上传与并发限制。
- 真实聚合教学数据导入工具和测量盲测基准工具。

动态图像和变温实验尚未实现，界面中不展示对应入口。

## 本地开发

要求 Python 3.12、Node.js 20。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
cd frontend
npm ci
cd ..
.\scripts\dev.ps1
```

默认仅监听本机。教师访问码为空时只适合本机开发；非本机监听或生产环境会拒绝启动，直到配置至少 16 字符的 `TEACHER_ACCESS_CODE`。

## 验证

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python -m pytest
cd frontend
npm run check
npm run build
npm audit --audit-level=high
```

测量盲测和真实数据导入参见 [VALIDATION.md](VALIDATION.md)。

## Docker

先在 `.env` 中设置强访问码，再运行：

```powershell
docker compose up --build
```

Compose 强制使用生产环境和 `0.0.0.0` 监听；缺少访问码时启动会安全失败。`data/` 与 `output/` 挂载到宿主机，请纳入学校的备份与访问控制策略。公网部署还必须在可信反向代理后启用 HTTPS，并接入学校 SSO/OIDC；当前签名会话只面向单教师本地试点。

## 数据边界

- `data/teacher_demo_records.json` 与 `data/teacher_workspace_seed.json` 是合成演示数据。
- 运行数据库、实验状态、分析输出、访问码和 API 密钥均被 Git 忽略。
- 不应把真实学生明细提交到仓库；教师端只导入完成教学所需的最小聚合信息。

## 技术边界

SIREN 输出连续坐标不等于具备相同量级的测量精度。正式交付应以跨设备真实样本的 MAE、RMSE、最大误差、失败率和耗时为验收依据，并保留人工复核和失败样本。
