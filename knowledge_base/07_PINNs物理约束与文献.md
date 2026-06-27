# PINNs 物理信息约束（AI 辅助 · 可选阅读）

## 文献
Raissi et al., *Physics-informed neural networks*, J. Comput. Phys. 378 (2019).

## 在本实验中的简化用法
未求解完整流体 PDE，而在损失中加入**先验**：
$$\mathcal{L} = \mathcal{L}_{MSE} + 0.01\mathcal{L}_{smooth} + 0.005\mathcal{L}_{sym}$$

- **光滑项**：抑制非物理剧烈振荡；
- **对称项**：理想衍射左右近似对称（权重小，保留轻微真实不对称）。

## 辩证
纯 MSE 易跟噪声出伪峰；约束过强可能抹平真实不对称照明——需结合剖面图判断。

## 引导问题
若样品明显单侧照明，你还应强制对称吗？如何用物理图样判断？
