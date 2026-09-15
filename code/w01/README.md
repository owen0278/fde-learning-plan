# W01 实战代码 · mini-llm-gateway

> 这一周**不是六个零散练习**，是一个贯穿项目。
> 从数据模型 → 并发引擎 → HTTP 服务 → 测试 → 上 CI，
> 七天结束时你手上是一个**能跑、有测试、有文档、有流水线**的完整服务。

```
D002 建模      ChatRequest / ChatResponse / Message   ← 类型安全的数据边界
  ↓
D003 并发      限流 + 超时 + 指数退避重试            ← 批量处理引擎
  ↓
D004 API       FastAPI + 依赖注入 + 错误映射         ← 交付给客户的最小形态
  ↓
D005 测试      mock 上游，覆盖异常分支               ← 敢改代码的底气
  ↓
D006 Git       抢救训练（沙箱里练）                   ← 提交历史的质量
  ↓
D007 CI        GitHub Actions + pre-commit           ← 自动化质量门
```

**每一步都用到了上一步的产出** —— 这是刻意设计的。
孤立的小练习学完就忘，串起来的项目才会变成你的作品集。

---

## 怎么开始

### 1. 装依赖（只需一次）

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv sync
```

> 依赖关系写在 `pyproject.toml`，精确版本锁在 `uv.lock`。
> `.venv` 不进 git —— 每台机器各自重建，这是正确做法。

### 2. 每天的流程

```powershell
uv run python d002_message_models/solution.py   # 先看参考实现跑起来的效果
# 然后打开 starter.py 自己写
uv run pytest d002_message_models -q            # 对照答案后跑测试
uv run ruff check d002_message_models           # 静态检查
```

**顺序很重要**：先看 solution 跑起来的样子 → 自己写 starter → 卡住再看 solution 源码。
直接抄 solution 等于没练。

---

## 目录

| 目录 | 日 | 主题 | 文件 |
| --- | --- | --- | --- |
| `d002_message_models/` | 9/15 | Pydantic 建模 | `README.md` `starter.py` `solution.py` `test_*.py` |
| `d003_async_batch/` | 9/16 | 异步并发 + 重试 | 同上 |
| `d004_fastapi_gateway/` | 9/17 | FastAPI 服务 | `README.md` `starter.py` `main.py` `test_smoke.py` |
| `d005_testing/` | 9/18 | 测试与 mock | `README.md` `test_gateway_deep.py` |
| `d006_git_drills/` | 9/19 | Git 抢救训练 | `README.md` `setup_sandbox.py` |
| `d007_ci/` | 9/20 | CI + 复盘 | `README.md`（配置在 `.github/workflows/`） |

每个目录的 `README.md` 里有：场景 → 分层任务（L1 跟着做 / L2 自己改 / L3 挑战）→ 验收标准 → 自检问题。

---

## 一键跑全部测试

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest -q
```

目前 **57 项测试**（D002: 17 · D003: 10 · D004: 8 · D005: 22）。
你每加一个功能，就应该增加对应的测试 —— 这个数字应该只涨不跌。

---

## 三条纪律

**1. 不要在 `solution.py` 上改你的作业。**
它是参考答案。你要动的是 `starter.py`。改坏了 solution，后面几天就没得对了。

**2. API Key 绝不进代码。**
后面 W02 开始要接真实模型。一律用 `.env` 文件 + `os.environ`，
`.env` 已经在 `.gitignore` 里。**公开仓库有扫描机器人，key 泄露几分钟内就会被刷爆。**

**3. 每天至少一次 commit。**
绿墙按提交日期算，不按推送日期。commit 天天做，push 攒几天做一次即可。

---

## 关于路径

这个目录在 `C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01`。

已经是**纯英文路径**（之前踩过中文路径导致 venv 绝对路径失效的坑）。
后续几周会装带 C 扩展的库（向量库、OCR），路径里有中文会出诡异的编译错误 —— 现在避免了。
