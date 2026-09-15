# D004 实战 · 把 LLM 能力包成 HTTP API

> 对应：`weeks/W01-Python现代工程化/D004-0917-FastAPI入门.md`
> 目录：`code/w01/d004_fastapi_gateway/`
> 预计 70 min

---

## 场景

前面两天你已经有了数据模型（D002）和并发引擎（D003）。
但客户的系统不会 import 你的 Python 包 —— **他们要的是一个 HTTP 接口**。

今天把它们包成一个服务：

```
POST /v1/chat    单条对话
POST /v1/batch   批量处理（用上 D003 的并发引擎）
GET  /health     健康检查（客户运维要用来做探活）
GET  /docs       Swagger 文档（自动生成，零成本）
```

**FDE 视角**：这是你交付给客户的最小可用形态。
一个能跑的 API + 自动生成的文档，比一百页 Word 文档有说服力得多。
客户的技术负责人打开 `/docs` 就能自己试，沟通成本立刻降一个数量级。

---

## 为什么今天必须搞懂依赖注入

`Depends` 是 FastAPI 的灵魂，也是大部分人学完还是不会用的东西。

**它解决什么问题：**

你的路由函数需要一些"外部资源" —— LLM 客户端、数据库连接、配置、当前登录用户。
如果直接写在函数里，测试时你就**没法替换它们**：

```python
# 坏：测试时怎么办？真的去调 API 花钱？
async def chat(req: ChatRequest):
    client = OpenAIClient(api_key=os.environ["KEY"])
    return await client.chat(req)
```

```python
# 好：测试时替换 get_caller 即可，零成本零网络
async def chat(req: ChatRequest, caller: Caller = Depends(get_caller)):
    return await caller(req)
```

**D003 里那个 `caller` 参数，本质上就是手动版的依赖注入。**
今天你会看到框架怎么把它自动化 —— 顺便理解为什么当时要那么设计。

---

## 你的任务

### L1 跟着做（40 min）

打开 `starter.py`，实现一个 FastAPI 应用：

| 路由 | 要点 |
| --- | --- |
| `POST /v1/chat` | 入参用 D002 的 `ChatRequest`，返回 `ChatResponse` |
| `POST /v1/batch` | 入参 `list[str]`，调用 D003 的 `batch_summarize` |
| `GET /health` | 返回 `{"status": "ok"}` |
| `GET /docs` | **免费赠送**，不用写 |

**错误处理映射**（这是重点，FDE 天天写这个）：

| 内部异常 | HTTP 状态码 | 原因 |
| --- | --- | --- |
| `FatalError` | **400** | 客户传参有问题，是他改 |
| `RetryableError`（重试后仍失败） | **504** | 上游挂了，是我们的问题 |
| 未知异常 | **500** | 兜底，别泄露内部细节给客户端 |

**资源生命周期用 `lifespan`**：启动时创建信号量/连接池，关闭时销毁。
不要把资源创建写在路由函数里 —— 那样每个请求都重建一次。

启动看效果：

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run uvicorn d004_fastapi_gateway.main:app --reload
```

浏览器打开 <http://127.0.0.1:8000/docs> —— **你会看到 D002 写的那些 pydantic 模型
自动变成了交互式文档**。这就是 D002 花 40 分钟建模的回报：字段、类型、校验规则、
示例值全部自动生成，一个字都不用写。

### L2 自己改（20 min）

1. **加限流中间件**：单个 IP 每分钟最多 60 次，超出返回 429。
   提示：用字典记录 `{ip: [时间戳列表]}`，在依赖项里实现。
2. **加 `X-Request-ID` 响应头**：每个响应带一个唯一 ID，打印到日志。
   > 这个习惯会救你的命。客户说"刚才那个请求失败了"，
   > 有 request-id 你就能从日志里把它精确捞出来，没有就只能靠猜时间。

### L3 挑战（选做，30 min）

1. 用 `lifespan` 在启动时**预热**一个 httpx.AsyncClient 连接池，
   并验证它在关闭时被正确 `aclose()`。
2. 实现**流式响应**（`StreamingResponse`），逐 token 返回。
   提示：写一个 async generator `yield` 每个 chunk。
   > 这是 D003 学的生成器 + D004 的 HTTP 结合点，也是 ChatGPT 打字机效果的底层原理。

---

## 验收标准

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest d004_fastapi_gateway -q
uv run ruff check d004_fastapi_gateway
```

**自检问题**：

1. `Depends` 传递的函数，什么时候被调用？每个请求一次，还是启动时一次？
2. `lifespan` 里 `yield` 之前和之后的代码，分别在什么时候执行？
3. 为什么 `FatalError` 映射成 400 而 `RetryableError` 映射成 504？
   如果反过来（400 表示上游挂了），客户会怎么理解？
4. 路由函数的返回值类型注解（`-> ChatResponse`）有什么用？去掉会怎样？
5. 自动生成的 OpenAPI 文档，数据源是什么？为什么 D002 把模型写规范了，文档就自动好看？

---

## 今日英语

`endpoint` `route` `payload` `dependency` `inject` `lifespan`
`middleware` `status code` `upstream` `downstream` `schema` `stream`
