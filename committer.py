import os
import random
import subprocess
from datetime import date, datetime, timedelta

# ── 日期映射配置 ───────────────────────────────────────────────────────────────
# arxiv 于 1991 年 8 月上线，早期论文的提交日期远早于 GitHub 诞生（2008）。
# 为了让 git commit 时间戳落在合理范围内，将所有论文日期线性映射到
# [COMMIT_START, 今天]，保留相对时间顺序，同时不会写入未来。
ARXIV_START = date(1991, 8, 1)   # arxiv 最早论文的参考基准
COMMIT_START = date(2009, 1, 3)  # commit 时间戳的最早允许日期


def map_commit_date(date_str: str) -> str:
    """
    将论文的原始提交日期映射到 [COMMIT_START, 今天] 范围内。

    - 2009-01-03 之后的论文：日期保持不变
    - 2009-01-03 之前的论文：按比例线性向前平移
    - 未来日期（理论上不应出现）：强制截断到今天
    """
    today = date.today()
    d = date.fromisoformat(date_str)
    d = min(d, today)  # 安全兜底：永不写入未来

    if d >= COMMIT_START:
        return d.isoformat()

    # 线性映射：[ARXIV_START, today] → [COMMIT_START, today]
    total_original = (today - ARXIV_START).days
    total_new = (today - COMMIT_START).days
    ratio = (d - ARXIV_START).days / total_original
    mapped = COMMIT_START + timedelta(days=int(ratio * total_new))
    return min(mapped, today).isoformat()


def random_timestamp(date_str: str) -> str:
    """
    在给定日期的 08:00–23:59 之间随机生成一个时间戳。
    模拟自然的阅读节奏，让 GitHub 贡献图看起来更真实。
    """
    base = datetime.strptime(date_str, "%Y-%m-%d")
    offset = timedelta(seconds=random.randint(8 * 3600, 23 * 3600 + 59 * 60))
    return (base + offset).strftime("%Y-%m-%dT%H:%M:%S")


def _run(cmd: list[str], env: dict = None) -> None:
    subprocess.run(cmd, env=env, check=True)


def commit_paper(filepath: str, title: str, date_str: str) -> None:
    """
    为单篇论文创建一个 git commit。
    commit 时间戳经过 map_commit_date() 映射后随机分布在当天内。
    通过 GIT_AUTHOR_DATE / GIT_COMMITTER_DATE 环境变量注入自定义时间。
    """
    mapped = map_commit_date(date_str)
    ts = random_timestamp(mapped)
    env = {**os.environ, "GIT_AUTHOR_DATE": ts, "GIT_COMMITTER_DATE": ts}
    _run(["git", "add", filepath])
    _run(["git", "commit", "-m", f"Add: {title}"], env=env)


def commit_index(filepath: str, date_str: str, n: int) -> None:
    """为当日 index.md 创建 commit，在所有单篇 commit 之后调用。"""
    mapped = map_commit_date(date_str)
    ts = random_timestamp(mapped)
    env = {**os.environ, "GIT_AUTHOR_DATE": ts, "GIT_COMMITTER_DATE": ts}
    _run(["git", "add", filepath])
    _run(["git", "commit", "-m", f"Daily: {date_str} — {n} papers"], env=env)


def push() -> None:
    """推送到远端，失败时打印提示但不终止程序（本地 commit 已保留）。"""
    try:
        _run(["git", "push"])
    except subprocess.CalledProcessError as e:
        print(f"[push failed] {e}\nLocal commits are intact, push manually.")
