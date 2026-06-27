# 系统技术摘要（辅）

## 测量精度（理想条件）
峰值定位约 0.0001 px 量级；标定后几何量约 0.0001 cm 量级；较粗糙手读显著减小随机误差。单张含训练约数十秒。

## 技术栈（实现）
PyTorch、SIREN、PINNs 约束、EasyOCR、OpenCV、Flask、SSE、DeepSeek API、RAG。

## 目录
`main.py` 测量核心；`FLASK_Web.py` Web；`knowledge_base/` 本库；`rag/` 检索。

## 物理提醒
README 指标依赖**条纹清晰、标尺可靠**；不满足时精度意义下降——先改实验条件。
