import os

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

COMPETITION_CONFIG = {
    'system_name': '基于SIREN与PINNs的液体表面张力系数AI高精度测量系统',
    'system_name_short': 'SIREN-PINNs智能系统',
    'sidebar_title': 'SIREN-PINNs智能系统',
    'track_label': 'AI + 物理实验',
    'brand_line': 'SIREN · PINNs · 毛细波激光衍射',
    'project_title': '基于SIREN与PINNs的液体表面张力系数AI高精度测量系统',
    'project_subtitle': 'SIREN 神经隐式场 · PINNs 物理约束 · 亚像素条纹分析',
    'operator_label': os.environ.get('LAB_OPERATOR', '实验工作台'),
    'institution': os.environ.get('LAB_INSTITUTION', ''),
    'year': '2026',
    'innovation_points': [
        'SIREN 连续光强场亚像素寻峰',
        'PINNs 物理约束保证表面张力 σ 一致性',
        '人机协同：预习—采集—计算全流程可追溯',
    ],
    # 兼容旧模板字段
    'team_name': os.environ.get('LAB_OPERATOR', '实验工作台'),
    'school_name': os.environ.get('LAB_INSTITUTION', ''),
}

RAG_CONFIG = {
    'enabled': True,
    'knowledge_base_dir': 'knowledge_base',
    'top_k': 6,
    'max_chunk_chars': 1400,
    'min_score': 0.04,
    # 最高检索片段得分低于此阈值时，视为知识库未覆盖，改走 mimo 通识回答
    'coverage_min_score': 0.08,
    # 关键词回退检索（无 sklearn 时）至少命中次数
    'coverage_min_keyword_hits': 2,
}

# 智慧星对话后端（小米 mimo-v2.5，OpenAI 兼容协议）
ZHIXING_LLM_CONFIG = {
    'display_name': '智慧星',
    'api_key': os.environ.get(
        'MIMO_API_KEY',
        '',
    ),
    'base_url': os.environ.get(
        'MIMO_BASE_URL',
        'https://token-plan-cn.xiaomimimo.com/v1',
    ),
    'model': os.environ.get('MIMO_MODEL', 'mimo-v2.5'),
    'system_prompt_kb': (
        '你是智慧星，激光衍射测液体表面张力实验的辅导助手。'
        '【知识库优先】仅依据本次提供的检索片段作答，不得编造未出现的数值、文献或步骤。'
        '【篇幅铁律】回答长度必须与问题匹配：'
        '· 极短/模糊输入（如单个数字「1」、「嗯」「继续」）→ 结合对话历史猜测意图；'
        '  若仍不明，用 1–2 句话请学生说完整，**禁止**展开成教程。'
        '· 简单一问 → 2–5 句话直答要点，最多一个小标题。'
        '· 复杂原理/误差分析 → 可分段，但仍避免废话与重复。'
        '禁止套用固定四步模板；不要每段都写「传统方法 vs AI 方法」除非学生明确对比。'
        '可结合对话历史理解追问；新增事实仍须来自检索片段。'
        '公式用 LaTeX（$...$）；Markdown 轻量即可。'
    ),
    'system_prompt_general': (
        '你是智慧星，本实验辅导助手。本题未命中知识库，请结合对话历史通识作答。'
        '【篇幅铁律】简问简答：'
        '· 极短/模糊输入 → 结合上文简短回应或请澄清，**不超过 2 句话**。'
        '· 一般问题 → 3–6 句话。'
        '· 只有学生明确要求详解时才长答。'
        '勿编造本系统具体读数或文献；公式用 LaTeX（$...$）。'
    ),
    'max_tokens': 640,
    'temperature': 0.45,
    # 多轮对话：最多保留最近 N 轮（每轮 = 1 问 + 1 答），及总字符上限
    'max_history_turns': 12,
    'max_history_chars': 8000,
    'history_assistant_max_chars': 600,
}

ZHIXING_LLM_CONFIG['system_prompt'] = ZHIXING_LLM_CONFIG['system_prompt_kb']
