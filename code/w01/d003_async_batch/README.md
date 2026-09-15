# D003 实战 · 并发批量调用 LLM（限流 / 超时 / 重试）

> 对应：`weeks/W01-Python现代工程化/D003-0916-异步与并发.md`
> 目录：`code/w01/d003_async_batch/`
> 预计 70 min

---

## 场景

客户丢给你 1,000 条工单文本，要批量生成摘要。
串行调用：每条 0.5 秒 → **8 分 20 秒**。
并发 10 路：理论 **50 秒**。

但现实会打脸：

- 并发一上来就撞上游 **限流**（RPM / TPM），HTTP 429
- 个别请求**超时**卡住，拖死整批
- 网络抖动导致随机失败，需要重试
- 有些失败**重试一万次也没用**（prompt 为空、鉴权失败）

**FDE 视角**：批量任务的成败不在于"跑起来"，
而在于**结束后能说清：成功几条、失败几条、每条为什么失败、失败的是该重试还是该放弃**。
客户问"为什么这 37 条没结果"时，你要能立刻给出答案。

---

## 核心设计（先想清楚再写）

**1. 用自定义异常区分「该重试」和「该放弃」**

这是 D002 学的自定义异常的第一个真实用途：

| 异常 | 含义 | 处理 |
| --- | --- | --- |
| `RetryableError` | 超时 / 429 / 5xx | 退避后重试，最多 N 次 |
| `FatalError` | prompt 为空 / 鉴权失败 / 参数错误 | 立即放弃，重试无意义 |

**不区分这两类，你的重试逻辑就是在浪费钱和时间。**

**2. 单个任务的失败不能炸掉整批**

`asyncio.gather` 默认一个协程抛异常，其余结果全部丢失。
正确做法：在**单个任务内部**消化异常，把失败变成数据（返回 `BatchItem` 对象）。

**3. 限流用 `asyncio.Semaphore`**

不是 sleep 硬等，而是发牌：**同时最多 N 个请求在飞**。

**4. 超时用 `asyncio.wait_for`**

没有超时的并发代码是定时炸弹 —— 一个卡住的请求会永久占用一个并发位。

---

## 你的任务

### L1 跟着做（40 min）

打开 `starter.py`，实现三个东西：

1. `RetryableError` / `FatalError` 两个异常（继承同一个基类 `LLMError`）
2. `summarize_one(...)` —— 单个调用，内含：限流 → 超时 → 重试（指数退避）
3. `batch_summarize(...)` —— 并发调度，返回 `list[BatchItem]`

**关键约束**：

- 重试只对 `RetryableError` 生效；`FatalError` 一次就放弃
- 退避要有**抖动**（jitter），否则所有失败请求会同时重试，形成新的尖峰
- `BatchItem` 要记录 `attempts`（实际尝试次数），这是你事后分析的数据

跑起来看效果：

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run python d003_async_batch/solution.py
```

你会看到串行 vs 并发的耗时对比，以及成功 / 失败统计。

### L2 自己改（20 min）

1. **加个 `max_failures` 熔断**：失败数超过阈值就整批中止，别硬扛。
   提示：用 `asyncio.Event()` 作为停止信号，每个任务开始前检查。
2. **统计并打印 P95 延迟**（不要只看平均值）。
   提示：收集每次成功调用的耗时，`sorted(durations)[int(len * 0.95)]`

> 平均值是给老板看的，P95 是给自己看的。FDE 排查性能问题时只看分位数。

### L3 挑战（选做，30 min）

1. 把重试改成**只对幂等请求重试**（GET 可以，POST 创建订单不行）。
   思考：LLM 摘要请求是幂等的吗？扣费请求呢？
2. 用 `asyncio.as_completed` 改写，实现**流式产出** —— 谁先完成谁先输出，
   而不是等整批结束。（这就是 LLM 流式回答的底层思路）

---

## 一个重要的习惯

`solution.py` 里的 `fake_call_llm` 是**假的 LLM** —— 随机延迟 + 随机失败。

**为什么不用真 API：**

- 学习阶段调真 API 要花钱，还会被限流干扰你的练习
- 真实 API 的失败是**不可复现**的，你没法验证重试逻辑到底对不对
- 注入式设计（函数接受 `caller` 参数）让你能用确定性的假函数写测试

这个 `caller` 参数就是**依赖注入**的雏形 —— D004 学 FastAPI 时，`Depends` 干的是同一件事。

---

## 验收标准

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest d003_async_batch -q
uv run ruff check d003_async_batch
```

**自检问题**：

1. `Semaphore` 是在 `summarize_one` 内部获取，还是在 `batch_summarize` 里获取？为什么？
2. 没有 `wait_for` 会怎样？举一个具体场景。
3. 为什么退避要加随机抖动？
4. `FatalError` 如果也重试，会发生什么？
5. `gather(return_exceptions=True)` 和"在任务内部消化异常"这两种做法，哪个更适合批量任务？为什么？

---

## 今日英语

`concurrent` `asynchronous` `coroutine` `await` `semaphore` `throttle`
`backoff` `jitter` `retry` `timeout` `idempotent` `throughput` `latency`
