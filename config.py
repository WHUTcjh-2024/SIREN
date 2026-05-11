"""
全局配置文件 (v10 — SIREN + PINNs + OCR主刻度 + 亚像素标尺处理)
核心改进:
  - SIREN + PINNs 高精度定位中央条纹、正负一级条纹 (4位小数)
  - OCR只检测10cm/20cm/30cm主刻度
  - 亚像素处理10cm-30cm刻度尺区域
  - 结合条纹像素位置与刻度尺数据计算 delta_x1, delta_x2
  - 水平线截取刻度尺推算 H0
"""

SIREN_CONFIG = {
    'input_dim': 1,
    'hidden_dim': 256,
    'num_layers': 4,
    'freq_0': 30.0
}

TRAINING_CONFIG = {
    'learning_rate': 1e-4,
    'weight_decay': 1e-6,
    'epochs': 500,
    'early_stopping_patience': 80,
    'early_stopping_min_delta': 1e-6,
    'pinn_weight': 0.01,
    'symmetry_weight': 0.005
}

NEWTON_CONFIG = {
    'max_iterations': 100,
    'tolerance': 1e-10,
    'step_clamp': 0.15,
    'n_scan': 5000
}

SUBPIXEL_CONFIG = {
    'ruler_upscale_factor': 5.0,
    'tick_search_window': 15,
    'clahe_clip_limit': 3.0,
    'clahe_tile_size': (8, 8)
}

EXPERIMENTAL_PARAMS = {
    'wavelength': 632.8,
    'distance_to_screen': 1000.0
}

CALIBRATION_CONFIG = {
    'ruler_position': 'right',
    'ocr_language': 'en',
    'min_ocr_confidence': 0.3,
    'target_marks_cm': [10, 20, 30],
    'max_tick_match_dist_ratio': 0.05
}

DEEPSEEK_CONFIG = {
    'api_key': 'sk-93317589d9af46ab82647b105f8da27a',
    'base_url': 'https://api.deepseek.com',
    'model': 'deepseek-v4-pro',
    'system_prompt': (
        '你是一位专业的物理实验助手，擅长激光衍射实验的教学辅导。'
        '你能够回答关于单缝衍射、圆孔衍射、光栅衍射等实验原理，'
        '帮助学生理解衍射条纹的分布规律、如何测量条纹间距、'
        '以及 AI（如 SIREN 神经网络和 PINNs 物理信息神经网络）如何在本系统中实现高精度自动测量。'
        '请用通俗易懂的语言回答，适合没有 AI 背景的物理专业学生理解。'
    ),
    'max_tokens': 1024,
    'temperature': 0.7
}
