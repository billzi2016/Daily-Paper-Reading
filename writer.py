import os
from config import COMMIT_DIR


# ── 路径计算 ──────────────────────────────────────────────────────────────────
# 目录结构：commit/YYYY/YYYY-MM-DD/<arxiv_id>.md
# 多加一层年份目录，避免 commit/ 下超过 GitHub 1000 条目的显示限制

def _year_dir(date: str) -> str:
    """返回年份目录路径，如 commit/2024/"""
    return os.path.join(COMMIT_DIR, date[:4])


def _paper_path(arxiv_id: str, date: str) -> str:
    # 旧格式 arxiv ID（如 math/9304216）会在 date 目录下创建子目录，属预期行为
    return os.path.join(_year_dir(date), date, f"{arxiv_id}.md")


def _index_path(date: str) -> str:
    return os.path.join(_year_dir(date), date, "index.md")


# ── 写入函数 ──────────────────────────────────────────────────────────────────

def save_paper(paper: dict, analysis: str, date: str) -> str:
    """
    将单篇论文分析写入 Markdown 文件。
    如果文件已存在则直接返回路径（幂等），不重复写入也不重新 commit。
    返回文件路径供 committer 使用。
    """
    path = _paper_path(paper["id"], date)
    if os.path.exists(path):
        return path

    os.makedirs(os.path.dirname(path), exist_ok=True)

    url = f"https://arxiv.org/abs/{paper['id']}"
    content = (
        f"# {paper['title']}\n\n"
        f"> {url} | {paper['categories']} | {paper['first_date']}\n\n"
        f"## 技术分析\n\n"
        f"{analysis if analysis else '_分析失败_'}\n\n"
        f"## Abstract\n\n"
        f"{paper['abstract']}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def save_index(papers: list[dict], date: str) -> str:
    """
    生成当日论文汇总索引 index.md。
    使用英文，不翻译标题，避免浪费 token。
    """
    path = _index_path(date)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    rows = "\n".join(
        f"| {i+1} | {p['title']} | {p['categories']} | [arxiv](https://arxiv.org/abs/{p['id']}) |"
        for i, p in enumerate(papers)
    )
    content = (
        f"# {date} Daily Papers — {len(papers)} papers\n\n"
        f"| # | Title | Categories | Link |\n"
        f"|---|-------|------------|------|\n"
        f"{rows}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
