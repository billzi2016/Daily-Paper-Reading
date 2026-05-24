# Daily Paper Reading

每日自动筛选 arxiv CS AI/LLM 相关论文，用本地大模型生成中文技术分析，每篇单独 git commit，push 到 GitHub 染绿贡献图。

做到100%全自动arxiv论文舆情监控(需要kaggle api)

## 依赖

- Python 3.11+
- [ollama](https://ollama.com) 本地运行，模型 `gpt-oss:120b`
- arxiv 全量快照 `arxiv-metadata-oai-snapshot.json`（放项目根目录，已 gitignore）

## 用法

```bash
# 安装依赖
pip install -e .

# 今天的论文（分析 + commit + push）
python main.py

# 指定日期
python main.py --date 2024-01-15

# 只看筛选结果，不跑模型
python main.py --dry-run

# 本地调试，不 push
python main.py --no-push --limit 5
```

## 输出结构

```
commit/
└── YYYY-MM-DD/
    ├── index.md          # 当日论文列表
    └── <arxiv_id>.md     # 单篇中文技术分析
```

## 筛选逻辑

- 分类：`cs.AI / cs.LG / cs.CL / cs.CV / cs.NE / cs.IR / cs.RO / cs.HC / cs.MM`
- 关键词：title 含 LLM / transformer / diffusion 等命中越多越优先
- Survey：2020 年之后提交的跳过
- `important.txt`：landmark 论文首次运行时强制纳入，之后跳过

## GitHub 染绿原理

每篇论文 = 1 次 git commit，时间戳随机分布在当天 08:00–23:59，论文越多格子越绿。
