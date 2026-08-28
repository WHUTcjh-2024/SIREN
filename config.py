"""Runtime configuration for the RAG assistant.

The measurement pipeline is configured in `modules/high_precision.py`.  Keep
this file focused on assistant settings so there is a single visible SIREN
implementation in the codebase.
"""

import os

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
