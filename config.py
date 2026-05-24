# ── 路径配置 ──────────────────────────────────────────────────────────────────
JSONL_PATH = "arxiv-metadata-oai-snapshot.json"  # arxiv 全量快照，约 5GB，不进 git
COMMIT_DIR = "commit"                             # 论文分析输出目录，按 YYYY/YYYY-MM-DD/ 组织

# ── 模型配置 ──────────────────────────────────────────────────────────────────
OLLAMA_MODEL = "gpt-oss:120b"         # 本地 ollama 模型
OLLAMA_BASE_URL = "http://localhost:11434"

# ── 筛选配置 ──────────────────────────────────────────────────────────────────
# 每次扫描每个日期最多保留的论文数（也是多轮扫描的轮数）
DAILY_LIMIT = 100

# 超过此年份提交的 survey/review 类论文直接跳过
# 2020 年之后 survey 泛滥，质量参差不齐
SURVEY_CUTOFF_YEAR = 2020

# arxiv CS 下与 AI/ML 相关的分类白名单
CS_AI_CATEGORIES = {
    "cs.AI",  # 人工智能
    "cs.LG",  # 机器学习
    "cs.CL",  # 计算语言学 / NLP
    "cs.CV",  # 计算机视觉
    "cs.NE",  # 神经与进化计算
    "cs.IR",  # 信息检索
    "cs.RO",  # 机器人（含学习方法）
    "cs.HC",  # 人机交互（含 LLM 应用）
    "cs.MM",  # 多媒体（含多模态）
}

# 标题关键词白名单：命中越多，排名越高（竞价排名）
# 用于捕捉分类乱投但实际 AI 相关的论文
AI_KEYWORDS = [
    "large language model", "llm", "transformer", "gpt", "bert", "language model",
    "neural network", "deep learning", "diffusion model", "reinforcement learning",
    "foundation model", "fine-tun", "prompt", "in-context learning", "rag",
    "retrieval-augmented", "multimodal", "vision-language", "text generation",
    "instruction tun", "alignment", "rlhf", "attention mechanism",
]

# survey 判断关键词，与 SURVEY_CUTOFF_YEAR 配合使用
SURVEY_KEYWORDS = [
    "survey", "review", "overview", "systematic review", "literature review",
]
