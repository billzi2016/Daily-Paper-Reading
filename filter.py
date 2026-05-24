import glob
import json
import os
from collections import defaultdict
from email.utils import parsedate
from datetime import date

from config import (
    JSONL_PATH, DAILY_LIMIT, CS_AI_CATEGORIES,
    AI_KEYWORDS, SURVEY_KEYWORDS, SURVEY_CUTOFF_YEAR, COMMIT_DIR,
)


# ── important.txt ─────────────────────────────────────────────────────────────

def load_important(path: str = "important.txt") -> dict[str, str]:
    """Return {arxiv_id: title} from important.txt."""
    result = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 1)
                if len(parts) == 2:
                    result[parts[0].strip()] = parts[1].strip()
    except FileNotFoundError:
        pass
    return result


# ── helpers ───────────────────────────────────────────────────────────────────

def parse_first_date(paper: dict) -> str | None:
    """Extract YYYY-MM-DD from versions[0].created (RFC 2822 format)."""
    try:
        created = paper["versions"][0]["created"]
        t = parsedate(created)
        if t:
            return date(t[0], t[1], t[2]).isoformat()
    except (KeyError, IndexError, TypeError):
        pass
    return None


def is_survey(title: str, year: int) -> bool:
    """Skip surveys submitted after SURVEY_CUTOFF_YEAR."""
    if year <= SURVEY_CUTOFF_YEAR:
        return False
    tl = title.lower()
    return any(kw in tl for kw in SURVEY_KEYWORDS)


def keyword_score(title: str) -> int:
    """Count how many AI_KEYWORDS appear in the title — used for ranking."""
    tl = title.lower()
    return sum(1 for kw in AI_KEYWORDS if kw in tl)


def is_ai_related(paper: dict) -> bool:
    """True if paper hits any CS AI category or any keyword in title."""
    cats = set(paper.get("categories", "").split())
    if cats & CS_AI_CATEGORIES:
        return True
    return any(kw in paper.get("title", "").lower() for kw in AI_KEYWORDS)


# ── checkpoint helpers ────────────────────────────────────────────────────────
# commit/ directory structure is the checkpoint — no separate state file needed.

def _iter_paper_files():
    """
    Yield (date, arxiv_id) for every paper file in commit/.
    Handles both flat IDs (2401.00001.md) and old-style subdirs (math/9304216.md).
    """
    commit_prefix = COMMIT_DIR.rstrip(os.sep) + os.sep
    for path in glob.glob(os.path.join(COMMIT_DIR, "**", "*.md"), recursive=True):
        if os.path.basename(path) == "index.md":
            continue
        # Strip commit/ prefix
        # New layout: "YYYY/YYYY-MM-DD/[cat/]id.md"
        # Old layout: "YYYY-MM-DD/[cat/]id.md"
        rel = path[len(commit_prefix):]
        parts = rel.replace("\\", "/").split("/")
        # Detect layout by checking if parts[0] looks like a year (4 digits)
        if len(parts[0]) == 4 and parts[0].isdigit():
            day = parts[1]                              # YYYY-MM-DD
            arxiv_id = "/".join(parts[2:]).removesuffix(".md")
        else:
            day = parts[0]                              # YYYY-MM-DD (old layout)
            arxiv_id = "/".join(parts[1:]).removesuffix(".md")
        yield day, arxiv_id


def get_done_ids() -> set[str]:
    """Return arxiv IDs already written to commit/, including old-style subdir IDs."""
    return {arxiv_id for _, arxiv_id in _iter_paper_files()}


def count_done_per_date() -> dict[str, int]:
    """Return {date: number_of_papers_done} from existing commit/ files."""
    counts: dict[str, int] = defaultdict(int)
    for day, _ in _iter_paper_files():
        counts[day] += 1
    return dict(counts)



# ── core iterator ─────────────────────────────────────────────────────────────

def iter_papers(jsonl_path: str = JSONL_PATH):
    """
    Stream the 5GB JSONL line by line.
    Yields cleaned paper dicts that pass basic filters (cs.* category, not a
    post-2020 survey, has abstract). No date filter applied here.
    """
    important = load_important()

    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                paper = json.loads(line)
            except json.JSONDecodeError:
                continue

            arxiv_id = paper.get("id", "").strip()
            title = paper.get("title", "").replace("\n", " ").strip()
            abstract = paper.get("abstract", "").replace("\n", " ").strip()
            categories = paper.get("categories", "")

            if not abstract:
                continue

            # Must have at least one cs.* category
            if not any(c.startswith("cs.") for c in categories.split()):
                continue

            first_date = parse_first_date(paper)
            first_year = int(first_date[:4]) if first_date else 9999

            if is_survey(title, first_year):
                continue

            # important.txt papers always score 999
            score = 999 if arxiv_id in important else keyword_score(title)

            # Non-important papers must be AI-related
            if score == 0 and not is_ai_related(paper):
                continue

            yield {
                "id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "categories": categories,
                "first_date": first_date,
                "score": score,
            }


# ── multi-pass scan ───────────────────────────────────────────────────────────

def scan_important(done_ids: set[str], jsonl_path: str = JSONL_PATH) -> list[dict]:
    """
    Collect all unprocessed important papers in one pass.
    Important papers never compete with each other — all of them are returned,
    even if multiple share the same date.
    """
    results = []
    for paper in iter_papers(jsonl_path):
        if paper["score"] != 999:
            continue
        if paper["id"] in done_ids:
            continue
        results.append(paper)
    return results


def scan_pass(round_num: int, done_ids: set[str], done_per_date: dict[str, int],
              jsonl_path: str = JSONL_PATH) -> dict[str, dict]:
    """
    One full pass through JSONL for regular (non-important) papers.
    For each date that has fewer than round_num papers done, find the
    highest-scoring unprocessed regular paper.
    Returns {date: best_paper} — one paper per date at most.
    """
    best: dict[str, dict] = {}

    for paper in iter_papers(jsonl_path):
        # Important papers are handled separately by scan_important()
        if paper["score"] == 999:
            continue
        if paper["id"] in done_ids:
            continue
        day = paper["first_date"]
        if not day:
            continue
        if done_per_date.get(day, 0) >= round_num:
            continue
        if day not in best or paper["score"] > best[day]["score"]:
            best[day] = paper

    return best


# ── single-date filter (--date mode) ─────────────────────────────────────────

def filter_papers(target_date: str, jsonl_path: str = JSONL_PATH) -> list[dict]:
    """Used when --date is passed: return up to DAILY_LIMIT papers for one day."""
    done_ids = get_done_ids()
    results = []
    important_hits = []

    for paper in iter_papers(jsonl_path):
        if paper["score"] == 999:
            # Important papers: include only if not yet processed
            if paper["id"] not in done_ids:
                important_hits.append(paper)
            continue
        if paper["first_date"] != target_date:
            continue
        results.append(paper)

    results.sort(key=lambda p: -p["score"])
    return important_hits + results[:DAILY_LIMIT]
