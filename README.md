# PSM Teaching Site · 朱曦策的贡献仓库

> 这是 [realwindjpn/psm-teaching-site](https://github.com/realwindjpn/psm-teaching-site) 的个人 fork。
> 这里的 **`refactor/frontend-design`** 分支承载了我（朱曦策 / @zhuxice-ctrl）对该项目本次的全部前端重构贡献。
> 下面所有内容围绕这次贡献展开。

---

## 本次贡献：`refactor/frontend-design` 分支

原项目是 **Flask + SQLite + AGNES AI** 的少儿 AI 教学站（服务端渲染、Jinja2 模板、CSS 187 行、原生 JS），是面向中小学生的 AI 启蒙课平台。

我在这个 fork 里做了一次完整的前端重构：**把整套界面从 SSR 替换成一个纯前端单页应用「奶油乐园」**，把原来 9 个 Jinja 模板对应的真实功能 1:1 映射过来，并加入了 8 处交互动效。

**详细文档**（按下面这一篇读就够了）：
- 📘 分支专用 README：[`FRONTEND_REDESIGN.md`](https://github.com/zhuxice-ctrl/teaching/blob/refactor/frontend-design/FRONTEND_REDESIGN.md)
- 📁 分支源码目录：[`frontend-redesign/`](https://github.com/zhuxice-ctrl/teaching/tree/refactor/frontend-design/frontend-redesign)
- 🌿 分支根目录：[`refactor/frontend-design`](https://github.com/zhuxice-ctrl/teaching/tree/refactor/frontend-design)

### 关键贡献一图速览

| 维度 | 数据 |
| --- | --- |
| 新增/改动文件 | `frontend-redesign/` 下 ~10 个源文件 + 7 张截图 + `FRONTEND_REDESIGN.md`（10 节） |
| 新增主题 | 3 套（星夜探索 / 奶油乐园 / 像素工坊），定版保留 1 套启用、2 套留仓可单行切回 |
| 新增交互特效 | 8 处（错位入场 / 3D 倾斜 / 按钮磁吸 / 点击爆星 / 提交彩屑 / 进度条 mascot / 额度抖动 / 审核印章） |
| 设计 token | 完整 CSS 变量层（颜色 9 档 / 圆角 3 档 / 阴影 3 档 / 字体 4 档） |
| 响应式断点 | 从 1 个（640px）扩到 3 个（1024 / 720 / ≤480），含 `safe-area-inset-*` 适配 |
| 数据层 | `localStorage` 模拟 + 种子数据（演示直过、登录不校验） |
| 截图 | 7 张 PNG（1200px max-width，~2MB）全部入仓，与源码同分支同步 |
| commit | `609a8715` 定版 + `2bac50a1` 文档与 FX bug 修复，作者 `zhuxice-ctrl` |
| 协作仓同步 | 同源内容已推 `realwindjpn/psm-teaching-site` 同一分支（[`e55690de`](https://github.com/realwindjpn/psm-teaching-site/commit/e55690ded86016756fec5fa22033aed2d55f739e)），作者挂 `zhuxice-ctrl` |

### 效果预览（7 张截图，全部入仓）

以下截图来自 `refactor/frontend-design` 分支的 `frontend-redesign/docs/screenshots/`，与源码完全同步。

**身份选择**（chooser，演示直过）

![身份选择](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/01-chooser.png)

**课时页 L2「和 AI 聊聊天」**

![课时页](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/02-lesson.png)

**AI 进度条 + 🦄 mascot**

![AI 进度条](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/03-lesson-ai-progress.png)

**班级展示墙**（3D 倾斜 + glare 跟手）

![展示墙](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/04-gallery.png)

**L10 作品集**（精选主图 + 副图布局）

![L10](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/05-l10.png)

**教师后台**

![教师后台](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/06-dashboard.png)

**作品审核 · 印章砸下**（FX #8）

![审核印章](https://raw.githubusercontent.com/zhuxice-ctrl/teaching/refactor/frontend-design/frontend-redesign/docs/screenshots/07-submissions-stamp.png)

### 设计语言：奶油乐园

定版主题为「奶油乐园」，是从三套设计探索中由用户选定的唯一主题：

- **背景**：奶油纸纹（双 radial gradient）
- **表面**：大圆角贴纸（`--radius: 24px` / `--radius-lg: 32px`）
- **阴影**：硬阴影（`0 6px 0 #e8b96a` 式，不模糊）+ 一层柔和投影
- **主色**：珊瑚红 `#ff6b6b` + 薄荷 `#4ecdc4` + 暖黄 `#ffd166`
- **字体**：display `Fraunces` + body `Nunito` + 手写点缀 `Caveat`
- **风格**：贴纸、印章、手写体、入场弹跳、点击爆星

完整 token 见 `theme-creamy.css` 顶部。改主题 = 改 token，不动组件。

### 8 处交互特效

全部在 `app.js` 的 `FX` 模块内，`prefers-reduced-motion` 时统一降级为 noop：

1. 入场错位弹跳（选择卡 / 活动卡 / 作品卡 / 审核卡）
2. 3D 倾斜 + glare 高光（chooser 大卡 / 展示墙作品卡）
3. 按钮磁吸（5 个主按钮，最大 4px）
4. 点击爆星（主按钮指针位置炸 10 颗星）
5. 提交彩屑（学生提交成功时 36 片）
6. 进度条 mascot（文字条 🦄 / 画图条 🎨）
7. 额度用尽抖动
8. 审核印章（教师点通过/驳回时从天而降的绿色/红色印章）

### 与原 Flask 后端的对接报告

每个前端 view ↔ 原路由/模板/参数映射，以及「接后端替换清单」写在 [`FRONTEND_REDESIGN.md` §7](https://github.com/zhuxice-ctrl/teaching/blob/refactor/frontend-design/FRONTEND_REDESIGN.md)。接手二次开发先看那一节。

---

## 怎么跑起来

克隆后切到重构分支，起一个静态服务即可（不需要 Python 后端、不需要数据库）：

```bash
git clone https://github.com/zhuxice-ctrl/teaching
cd teaching
git checkout refactor/frontend-design
cd frontend-redesign
python3 -m http.server 8000
# 浏览器打开 http://localhost:8000
```

登录页是**演示直过**——点击「老师进入」/「学生进入」即跳，不校验。数据存浏览器 `localStorage`，清存储可重置。

---

## 与上游协作仓的关系

| 角色 | 仓库 | 分支 | 说明 |
| --- | --- | --- | --- |
| 上游原仓 | [`realwindjpn/psm-teaching-site`](https://github.com/realwindjpn/psm-teaching-site) | `refactor/frontend-design` | 同样内容（commit `e55690de`），作者挂 `zhuxice-ctrl` |
| 本人 fork | [`zhuxice-ctrl/teaching`](https://github.com/zhuxice-ctrl/teaching) | `refactor/frontend-design` | fork 镜像（commit `2bac50a1`） |
| 本仓 `main` | [`zhuxice-ctrl/teaching`](https://github.com/zhuxice-ctrl/teaching) | `main` | 上游原版的 sanitized snapshot，未做改动 |

**目前不合并到 `main`**——这是我与上游原作者协商后的安排，分支就停在这里。要合、要二次开发、或要拆出来单独发布，由我和原作者后续决定。

---

## 关于作者

朱曦策 · `@zhuxice-ctrl` · 研发 / IT

本次贡献是「AI 先锋未来人才大赛」过程中的实际工程产出，从架构解读 → 设计探索（3 套主题）→ 视觉定版（奶油乐园）→ 8 处交互特效 → 演示直过 → 入仓与文档交接，端到端完成。详细交接说明见 [`FRONTEND_REDESIGN.md`](https://github.com/zhuxice-ctrl/teaching/blob/refactor/frontend-design/FRONTEND_REDESIGN.md)。
