import requests
from config import OLLAMA_MODEL, OLLAMA_BASE_URL

# ── 系统提示词 ────────────────────────────────────────────────────────────────
# 作为 system prompt 传给模型，与用户输入分离，不占用 user token 空间。
# 模型上下文窗口 32k（input + thinking + output 共用），prompt 必须极简：
# 指令放 system，user 侧只传 title + abstract，给 output 留足空间。
#
# think 设为 "low"（而非 false）：实测 false 反而产生更多 thinking token（~145 vs ~36）。
# 有效值：high / medium / low / max / true / false
SYSTEM_PROMPT = (
    "你是一位擅长科普写作的AI研究员，专注于机器学习与人工智能领域。"
    "用户会给你一篇论文的标题和摘要，你需要用流畅、有温度的中文进行深度解读。"
    "读者是有一定技术基础的工程师或研究生，不需要解释最基本的概念，但需要讲清楚论文的独特之处。\n\n"
    "解读按以下顺序展开，自然衔接，不要输出编号或标题：\n"
    "先交代这个问题的背景和现有方法的局限，让读者理解为什么需要这篇论文；"
    "再讲作者的核心思路和技术方法，把原理说透，不要只说'提出了一种新方法'；"
    "然后聊实验结果，用具体数字说明效果；"
    "最后谈这项工作对领域的意义，以及可能带来的影响。"
    "结尾另起一行输出关键词，格式：关键词：xxx、xxx、xxx\n\n"
    "风格要求：像在给朋友讲一个有趣的技术故事，叙述连贯，有逻辑，不堆砌要点。"
    "技术术语保留英文，首次出现时用括号给出中文解释。"
    "不要在输出中提及字数、格式要求、或重复用户给你的指令。"
)


def analyze_paper(title: str, abstract: str) -> str:
    """
    调用本地 ollama 生成论文中文技术分析。

    prompt 极简：只拼接 title + abstract，不加任何包裹，
    节省 token 给模型输出（32k 上下文共用）。
    失败时返回空字符串，由调用方决定如何处理。
    """
    prompt = "Title: " + title + "\n\nAbstract: " + abstract
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt,
                "think": "low",   # 降低 thinking token 消耗，不能完全关闭
                "stream": False,
            },
            timeout=300,  # 120b 模型单次生成最长约 5 分钟
        )
        resp.raise_for_status()
        # thinking 字段是模型内部推理，直接丢弃；response 是最终输出
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"  [analyzer error] {e}")
        return ""
