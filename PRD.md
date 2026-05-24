# PRD: Daily Paper Reading

## 背景

arxiv 全量快照（`arxiv-metadata-oai-snapshot.json`，~5GB JSONL），每行一篇论文。筛出当日 CS AI/LLM 相关论文，用本地大模型生成中文技术分析，每篇单独 git commit（随机时间戳），最终 push 到 GitHub 染绿贡献图。

---

## 文件结构（扁平）

```
Daily-Paper-Reading/
├── main.py
├── filter.py
├── analyzer.py
├── writer.py
├── committer.py
├── config.py
├── important.txt      # 硬编码必读论文（~100篇landmark）
├── PRD.md
├── .gitignore
└── commit/
    └── YYYY-MM-DD/
        ├── index.md
        └── <arxiv_id>.md
```

---

## 数据字段

| 字段 | 说明 |
|------|------|
| `id` | arxiv ID |
| `title` | 标题 |
| `abstract` | 摘要 |
| `categories` | 空格分隔分类 |
| `versions[0].created` | **首次提交日期**（用这个） |

---

## config.py

```python
JSONL_PATH = "arxiv-metadata-oai-snapshot.json"
COMMIT_DIR = "commit"
OLLAMA_MODEL = "gpt-oss:120b"
OLLAMA_BASE_URL = "http://localhost:11434"
DAILY_LIMIT = 100
SURVEY_CUTOFF_YEAR = 2020  # 2020年之后的survey一律跳过

CS_AI_CATEGORIES = {
    "cs.AI", "cs.LG", "cs.CL", "cs.CV",
    "cs.NE", "cs.IR", "cs.RO", "cs.HC", "cs.MM",
}

AI_KEYWORDS = [
    "large language model", "llm", "transformer", "gpt", "bert", "language model",
    "neural network", "deep learning", "diffusion model", "reinforcement learning",
    "foundation model", "fine-tun", "prompt", "in-context learning", "rag",
    "retrieval-augmented", "multimodal", "vision-language", "text generation",
    "instruction tun", "alignment", "rlhf", "attention mechanism",
]

SURVEY_KEYWORDS = ["survey", "review", "overview", "systematic review", "literature review"]
```

---

## filter.py

**步骤：**

1. 读取 `important.txt`，建立 `{arxiv_id: title}` 字典
2. 流式逐行读 JSONL（5GB，不能整体加载）
3. 解析 `versions[0].created`（格式如 `Mon, 2 Apr 2007 19:18:42 GMT`）提取 `YYYY-MM-DD`
4. **跳过条件**（任一满足则跳过）：
   - `categories` 中无任何 `cs.*`
   - title 小写含 `SURVEY_KEYWORDS` 任意项，且首提年 > 2020
5. **important.txt 命中**：无视日期，score=999，直接收录
6. **日期命中**：`first_date == target_date`，且满足：
   - `categories` 含 `CS_AI_CATEGORIES` 任意项，**或** title 含 `AI_KEYWORDS` 任意项
7. 计算 score = title 中命中 `AI_KEYWORDS` 的数量
8. 按 score 降序，取前 `DAILY_LIMIT` 篇

```python
def filter_papers(jsonl_path: str, target_date: str) -> list[dict]:
    """返回 list[dict]，每个 dict 含 id/title/abstract/categories/score/first_date"""
```

---

## analyzer.py

**模型**：`gpt-oss:120b`，`POST /api/generate`

**Think 设置**：`"think": "low"`（`false` 反而 thinking 更多，实测 low≈36 tokens vs false≈145 tokens；`"high"/"medium"/"low"/"max"/true/false` 是全部合法值）

**32k 上下文限制**：ollama 的 32k 是 input + thinking + output 共用，prompt 越长输出空间越少，所以 prompt 必须极简。

**Prompt（字符串拼接，不翻译英文内容）**：

```python
def build_prompt(title: str, abstract: str) -> str:
    return (
        "请给出中文技术分析：核心贡献（2-3点）、技术方法（100字内）、潜在影响（50字内）、关键词（3-5个）。\n\n"
        "Title: " + title + "\n\nAbstract: " + abstract
    )
```

返回值取 `d["response"]`，忽略 `d["thinking"]`。

**接口**：
```python
def analyze_paper(title: str, abstract: str) -> str:
    """调用 ollama，返回中文分析文本，失败返回空字符串"""
```

---

## writer.py

**单篇** `commit/YYYY-MM-DD/<arxiv_id>.md`：

```markdown
# {title}

> https://arxiv.org/abs/{id} | {categories} | {first_submitted}

## 技术分析

{model output}

## Abstract

{abstract}
```

**index.md** `commit/YYYY-MM-DD/index.md`：英文，无翻译，省 token。

```markdown
# {YYYY-MM-DD} Daily Papers — {N} papers

| # | Title | Categories | Link |
|---|-------|------------|------|
| 1 | {title} | cs.LG cs.CL | [arxiv](https://arxiv.org/abs/{id}) |
```

**接口**：
```python
def save_paper(paper: dict, analysis: str, date: str) -> str:
    """写单篇 md，返回文件路径；文件已存在则返回路径但跳过写入"""

def save_index(papers: list[dict], date: str) -> str:
    """写 index.md，返回文件路径"""
```

---

## committer.py

每篇写完立即 commit，时间戳伪造到目标日期内随机时刻，最终 push。

```python
def random_timestamp(date_str: str) -> str:
    """返回 date_str 当天 08:00–23:59 内随机 ISO 时间"""
    base = datetime.strptime(date_str, "%Y-%m-%d")
    offset = timedelta(seconds=random.randint(8*3600, 23*3600 + 59*60))
    return (base + offset).strftime("%Y-%m-%dT%H:%M:%S")

def commit_paper(filepath: str, title: str, date_str: str) -> None:
    ts = random_timestamp(date_str)
    env = {**os.environ, "GIT_AUTHOR_DATE": ts, "GIT_COMMITTER_DATE": ts}
    subprocess.run(["git", "add", filepath], check=True)
    subprocess.run(["git", "commit", "-m", f"Add: {title}"], env=env, check=True)

def push() -> None:
    subprocess.run(["git", "push"], check=True)
```

- 全部单篇完成后：commit index.md，消息 `Daily: {date} — {N} papers`
- 最后调用 `push()`（除非 `--no-push`）

---

## main.py 用法

```
python main.py                          # 今天
python main.py --date 2024-01-15        # 指定日期
python main.py --date 2024-01-15 --limit 10   # 调试
python main.py --dry-run                # 只统计，不跑模型不commit
python main.py --no-push                # 不push
```

---

## 边界处理

| 场景 | 处理 |
|------|------|
| 当日无论文 | 打印提示，退出 |
| ollama 未启动 | 报错提示 `ollama serve` |
| 单篇分析失败 | 写错误占位，仍 commit，继续 |
| 文件已存在 | 跳过（幂等） |
| push 失败 | 打印错误，本地 commit 保留 |

---

## 依赖

```
requests>=2.28.0
```
