# 系统技术摘要（辅）

## 测量能力边界
系统输出连续坐标峰位和标定残差，但输出小数位不代表测量精度。当前仓库尚无足量、带参考真值的跨设备盲测数据，不声明固定精度。交付前应使用 `scripts/benchmark_measurement.py` 对真实样本计算误差、失败率和耗时。

## 技术栈（实现）
PyTorch、SIREN、先验正则、EasyOCR、OpenCV、FastAPI、Vue、SSE、MIMO API、RAG。

## 目录
`modules/high_precision.py` 测量核心；`backend/` API；`frontend/` 展示端；`knowledge_base/` 本库；`rag/` 检索。

## 物理提醒
README 指标依赖**条纹清晰、标尺可靠**；不满足时精度意义下降——先改实验条件。
