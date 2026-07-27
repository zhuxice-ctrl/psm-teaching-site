# PSM Teaching Site

> **⚠️ 你在 `refactor/frontend-design` 分支上** —— 本分支是**前端重构 · 奶油乐园定版**：
> 在原 Flask 工程之外新增了一套纯前端单页实现（`frontend-redesign/`），原后端代码原样保留。
> **接手二次开发请先读 [`FRONTEND_REDESIGN.md`](FRONTEND_REDESIGN.md)**（背景 / 文件地图 / 设计系统 / 后端映射 / 开发入口 / 已知边界）。
> 线上预览：https://larkcommunity.feishu.cn/page/NTtMmlUtLdmLfMaYqk6cXLzNnhe

---

PSM 少儿 AI / Python 教学站点。

## Scope

This repository is a sanitized source snapshot. It excludes production database files, uploads, generated output, logs, venv, backups, and all secret-bearing files.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt  # if present
python run.py
```
