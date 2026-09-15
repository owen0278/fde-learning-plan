# D005 实战 · 给网关写测试（不花一分钱，覆盖所有分支）

> 对应：`weeks/W01-Python现代工程化/D005-0918-测试与代码质量.md`
> 目录：`code/w01/d005_testing/`
> 预计 70 min

---

## 场景

D004 的网关能跑了。但你敢改它吗？

改一行限流逻辑，会不会把 `/v1/chat` 搞挂？上游超时的时候返回的是 504 还是 500？
**没有测试，你每次改动都是在赌。**

更现实的约束：**测试不能真调 LLM API**。

| 真 API 测试 | Mock 测试 |
| --- | --- |
| 花钱，跑一次几毛，跑一千次几百块 | 零成本 |
| 结果不固定（同一个 prompt 两次回答不同），断言没法写 | 结果确定，断言精确 |
| **异常分支根本测不了**（你怎么让上游稳定返回 503？） | 想让它失败就失败，想超时就超时 |
| 慢，几百毫秒起 | 毫秒级，能进 CI |

**FDE 视角**：你的测试里 90% 应该是 mock 测试，只有极少数"冒烟测试"打真实 API
（而且通常在生产环境跑，不在 CI 里）。这是行业惯例，不是偷懒。

---

## 分层：什么该测，什么不该测

| 层 | 测什么 | 怎么测 |
| --- | --- | --- |
| **单元层** | 单个函数、模型校验、重试逻辑 | 直接调用，注入假 caller |
| **集成层** | HTTP 路由、状态码、错误映射 | `TestClient` + `dependency_overrides` |
| **端到端** | 真实 API 连通性 | 只在手动冒烟时跑，不进 CI |

今天重点是**集成层** —— 因为 D004 的 `Depends` 设计，让这一层变得极其好写。
这就是昨天那 40 分钟学的依赖注入的回报。

---

## 你的任务

### L1 跟着做（40 min）

**先自己写**：在 `d005_testing/` 下新建 `test_gateway.py`，照着下面五类场景写。
写完再打开 `test_gateway_deep.py` 对照 —— 重点看**我测了哪些你漏掉的分支**。

一个 HTTP 接口至少要覆盖这五类：

| # | 场景 | 期望 |
| --- | --- | --- |
| 1 | 正常请求 | 200 + 正确结构 |
| 2 | 客户端参数错误 | **422**（pydantic 拦下）或 **400**（业务拦截） |
| 3 | 上游持续失败 | **504**，且重试了 N 次 |
| 4 | 上游瞬时失败后成功 | 200，且 `attempts > 1` |
| 5 | 批量部分失败 | 200，但 `failed > 0`，失败项有原因 |

**关键技巧：`app.dependency_overrides`**

```python
app.dependency_overrides[get_caller] = lambda: my_fake_caller
```

这一行就能把你真实的 LLM 调用换成任意假实现。
**这就是 FastAPI 依赖注入存在的最大理由。**

跑测试：

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest d005_testing -q
```

### L2 自己改（20 min）

1. **跑覆盖率，找出没测到的分支**：
   ```powershell
   uv run pytest d005_testing -q --cov=d004_fastapi_gateway --cov-report=term-missing
   ```
   看 `Missing` 列 —— 那些行号就是你没覆盖的逻辑。
   **挑 2 条补上**，把覆盖率提到 85% 以上。

2. **用 `@pytest.mark.parametrize` 压缩重复测试**：
   如果你写了三个几乎一样的测试函数（只是输入不同），合并成一个参数化测试。

> 覆盖率数字本身没意义，但**没被覆盖的分支有意义** —— 那是你不知道自己代码行为的地方。

### L3 挑战（选做，30 min）

1. 写一个 **conftest.py**，把 fake caller 做成可复用的 fixture，
   让测试函数不再重复写依赖覆盖的样板代码。
2. 测**并发安全性**：同时发 50 个请求，验证限流真的生效（没有超过 max_concurrency）。

---

## 验收标准

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest d005_testing -q
uv run ruff check d005_testing
```

**自检问题**：

1. 为什么测试里绝不调用真实 LLM API？说出至少两个理由。
2. `422` 和 `400` 在你的 API 里分别由谁产生？
3. `dependency_overrides` 为什么要在测试结束后 `clear()`？
4. 覆盖率 100% 能证明代码没有 bug 吗？举一个反例。
5. 如果你改了 `FatalError` → 400 的映射为 500，哪些测试会红？
   （如果答不上来，说明你的测试和实现耦合得太死或太松）

---

## 今日英语

`fixture` `mock` `stub` `patch` `assert` `coverage` `parametrize`
`regression` `flaky` `setup` `teardown` `suite` `branch`
