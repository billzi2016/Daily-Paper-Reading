import argparse
import sys
from datetime import date

from config import DAILY_LIMIT
from filter import filter_papers, scan_pass, scan_important, get_done_ids, count_done_per_date
from analyzer import analyze_paper
from writer import save_paper, save_index
from committer import commit_paper, commit_index, push


def process_paper(paper: dict, commit_date: str) -> None:
    """
    处理单篇论文的完整流程：调用模型 → 写文件 → git commit。

    important 论文（score=999）归档到其原始提交日期目录，
    普通论文归档到当次扫描的目标日期。
    """
    print(f"  → {paper['id']} [{paper['score']}] {paper['title'][:65]}")
    analysis = analyze_paper(paper["title"], paper["abstract"])
    # important 论文按其原始日期归档，普通论文按扫描目标日期归档
    file_date = paper["first_date"] if paper["score"] == 999 else commit_date
    filepath = save_paper(paper, analysis, file_date)
    if filepath:
        commit_paper(filepath, paper["title"], file_date)


def run_multipass(no_push: bool) -> None:
    """
    多轮扫描全量 JSONL，将历史上所有 AI 论文按日期均匀摊开处理。

    流程：
      Pass 0  — important.txt 中的 landmark 论文，全部收录，不参与竞价
      Pass 1  — 全库扫描，每个日期取关键词得分最高的 1 篇
      Pass 2  — 再扫一遍，每个日期取第 2 高的
      ...
      Pass N  — 共 DAILY_LIMIT 轮

    断点续跑：commit/ 目录即检查点，程序随时可以 Ctrl+C，
    重启后自动从未处理的地方继续，不会重复处理已有文件。
    """
    # Pass 0：important 论文独立处理，不与普通论文竞争日期 slot
    done_ids = get_done_ids()
    print("\n=== Pass 0: important papers ===")
    important_papers = scan_important(done_ids)
    if important_papers:
        print(f"  {len(important_papers)} important papers to process.")
        for paper in important_papers:
            process_paper(paper, paper["first_date"])
    else:
        print("  All important papers already done.")

    # Pass 1..N：普通论文多轮竞价
    for round_num in range(1, DAILY_LIMIT + 1):
        # 每轮重新读取检查点，支持中断后从断点继续
        done_ids = get_done_ids()
        done_per_date = count_done_per_date()

        print(f"\n=== Pass {round_num}/{DAILY_LIMIT} — scanning JSONL... ===")
        best_per_date = scan_pass(round_num, done_ids, done_per_date)

        if not best_per_date:
            print(f"  Nothing left to process in pass {round_num}.")
            continue

        print(f"  {len(best_per_date)} dates have a paper to process.")
        for day in sorted(best_per_date.keys()):
            process_paper(best_per_date[day], day)

        print(f"  Pass {round_num} done.")

    print(f"\nTotal dates with papers: {len(count_done_per_date())}")

    if not no_push:
        print("Pushing to GitHub...")
        push()


def run_single_date(target_date: str, limit: int | None, dry_run: bool,
                    no_push: bool) -> None:
    """
    单日模式（--date）：只处理指定日期的论文。
    适合调试或补跑特定日期。
    """
    print(f"Date: {target_date}")
    print("Scanning...")
    papers = filter_papers(target_date)

    if limit:
        papers = papers[:limit]

    if not papers:
        print("No papers found.")
        sys.exit(0)

    print(f"Found {len(papers)} papers.")

    if dry_run:
        # 只打印筛选结果，不调用模型，不 commit
        for p in papers:
            print(f"  [{p['score']:>3}] {p['id']} {p['title'][:75]}")
        sys.exit(0)

    processed = []
    for i, paper in enumerate(papers, 1):
        print(f"[{i}/{len(papers)}]", end=" ")
        commit_date = paper["first_date"] if paper["score"] == 999 else target_date
        process_paper(paper, commit_date)
        processed.append(paper)

    index_path = save_index(processed, target_date)
    commit_index(index_path, target_date, len(processed))

    if not no_push:
        print("Pushing to GitHub...")
        push()

    print(f"Done. {len(processed)} papers committed.")


def main():
    parser = argparse.ArgumentParser(description="Daily arxiv CS AI/LLM paper reader")
    parser.add_argument(
        "--date", default=None,
        help="单日模式：指定 YYYY-MM-DD（默认：多轮扫描全量历史）"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="限制处理论文数量（调试用）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只筛选打印，不调用模型，不 commit"
    )
    parser.add_argument(
        "--no-push", action="store_true",
        help="处理完不 push（本地调试）"
    )
    args = parser.parse_args()

    if args.date:
        run_single_date(args.date, args.limit, args.dry_run, args.no_push)
    else:
        if args.dry_run:
            # 多轮模式下 dry-run：展示今天的候选论文
            run_single_date(date.today().isoformat(), args.limit, True, True)
        else:
            run_multipass(args.no_push)


if __name__ == "__main__":
    main()
