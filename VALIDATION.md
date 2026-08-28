# 测量与试点验收

本项目不以输出小数位替代精度证明。对外给出测量指标前，必须完成带参考真值的盲测。

## 数据集要求

- 至少 100 张真实仪器图像，覆盖不同设备、相机、曝光、倾斜、模糊和标尺遮挡条件。
- 训练、调参和验收样本隔离；参考峰位由两名人员独立标注并复核。
- 保存原图、设备编号、采集条件、软件版本和失败原因，不删除失败样本。

## 清单格式

UTF-8 CSV：`image,negative_px,center_px,positive_px`。图像路径相对 CSV 所在目录。

```powershell
python scripts/benchmark_measurement.py validation/manifest.csv `
  --output output/measurement-benchmark.json `
  --max-rmse-px 1.0 --max-failure-rate 0.05
```

阈值由光驰设备规格、人工读数基线和教师需求共同确定，上述数值仅演示命令格式。报告同时记录 MAE、RMSE、最大误差、失败率、中位耗时及 P95 耗时。

## 教学试点

真实试点还应记录教师处理时间、学生完成率、干预后复测结果、部署时间和人工介入率。演示数据只能验证软件流程，不能作为客户效果证据。

真实聚合工作区通过本地命令导入，接口不会接受匿名上传：

```powershell
python scripts/import_teacher_workspace.py data/live_workspace.json
```

导入前会执行完整模式校验，并要求 `dataSource` 为 `live`；数据库更新使用事务和版本检查。原始学生明细应留在学校受控系统中，本项目只导入教学所需的最小聚合信息。

## 物理模型验收

- 每组记录频率、密度、液深、几何量、温度和所用条纹级次，不允许只保存最终 σ。
- 计算使用 $\omega^2=(gk+\sigma k^3/\rho)\tanh(kd)$；未测液深而采用深水近似时，报告必须给出适用性说明。
- 保存系统输出的重力贡献比例；任何使 $\omega^2/\tanh(kd)-gk\le0$ 的数据均标记为非物理输入并回查原始测量，不得静默输出负值或取绝对值。
- 用已知表面张力标准液和独立方法做交叉验证，按不同温度、液深、频率和设备分层报告偏差与不确定度。
