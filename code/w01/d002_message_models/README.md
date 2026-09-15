# D002 实战 · 用 Pydantic 建模 LLM 对话

> 对应：`weeks/W01-Python现代工程化/D002-0915-Python现代语法补课.md`
> 目录：`code/w01/d002_message_models/`
> 预计 60 min（跟着做 40 + 自己改 20）

---

## 场景

你在给 mini-llm-gateway 打地基。客户端（后面 D004 就是它）要往 LLM 发请求，
请求体长这样 —— 这是 OpenAI / DeepSeek / 通义千问**通用的数据形状**：

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "你是一个严谨的助手"},
    {"role": "user", "content": "今天北京天气怎么样"}
  ],
  "temperature": 0.7
}
```

**为什么不用裸 dict 凑合：**

| 用 dict | 用 pydantic model |
| --- | --- |
| `msg["contnet"]` 拼错，运行到一半才炸 | 属性名写错，IDE 立刻标红 |
| 客户传 `temperature="0.7"`（字符串），一路污染到 API 调用 | 入口就强制转成 float，或明确报错 |
| 函数签名看不出数据长什么样 | 看类型注解就知道 |
| 手写 `if "x" not in d: raise ...` | 声明式校验，几行搞定 |

**FDE 视角**：你交付给客户的东西，边界上必须能挡住脏数据。
客户那边的历史系统传过来的 JSON 永远比你预期的脏 —— 这是常态，不是意外。

---

## 你的任务

### L1 跟着做（40 min）—— 先别看 solution

打开 `starter.py`，里面有骨架和 TODO。
**先自己写 30 分钟，卡住了再看 `solution.py`。**

要实现的模型：

| 模型 | 字段 | 要点 |
| --- | --- | --- |
| `Role` | system / user / assistant / tool | 用 `str, Enum`，这样能直接当字符串用 |
| `ToolCall` | id, name, arguments | `arguments` 是 `dict[str, Any]`，默认空字典 |
| `Message` | role, content, name, tool_call_id, tool_calls | 见下面的业务规则 |
| `Usage` | prompt_tokens, completion_tokens | 加个 `total_tokens` 属性 |
| `Choice` | index, message, finish_reason | `finish_reason` 用 `Literal` 限定取值 |
| `ChatRequest` | model, messages, temperature, max_tokens, tools | temperature 要能收字符串 |
| `ChatResponse` | id, model, choices, usage | — |

**业务规则（这是重点，模型不是字段堆砌）：**

1. `role="tool"` 的消息**必须**带 `tool_call_id`（否则模型不知道这条结果对应哪个调用）
2. 其他角色的消息，`content` 和 `tool_calls` **至少有一个非空**（空消息发给 API 会报错）
3. `temperature` 必须在 `0.0 ~ 2.0`；**客户传字符串 `"0.7"` 时要能自动转成 0.7**（真实场景高频）
4. `messages` 不能是空列表

运行验证：

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run python d002_message_models/solution.py
```

### L2 自己改（20 min）—— 必须做

`solution.py` 只是及格线。在这基础上改：

1. **加一个 `ChatRequest.to_api_payload()` 方法**，返回发给上游 API 的 dict。
   要求：`None` 字段全部剔除（API 不接受 `"max_tokens": null`）。
   提示：`model_dump(exclude_none=True)`
2. **处理脏数据**：写一个 `parse_request(raw: dict) -> ChatRequest | str` 函数，
   解析成功返回对象，失败返回**人类可读的错误信息字符串**（不要直接抛异常给调用方）。
   提示：`except ValidationError as e: return str(e)`

> 第 2 题是 FDE 的真实日常：客户的脏数据你要么清洗掉，要么给出能直接回给对方的错误说明。
> 直接抛一堆栈栈信息给客户，是最差的做法。

### L3 挑战（选做，30 min）

1. 用 `dataclass` 再写一遍 `Message`，然后回答：
   **为什么这个场景该用 pydantic 而不是 dataclass？**（写进复盘，一句话说清）
   提示：dataclass **不会**在 `__init__` 时校验类型，`Message(role="user", content=123)` 照样能构造成功。
2. 给 `ChatRequest` 加个 `model_validator`，要求：
   如果 `tools` 非空，则 `messages` 里最后一条的 role 不能是 `assistant`。

---

## 验收标准

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest d002_message_models -q
uv run ruff check d002_message_models
```

两条都要过：`pytest` 全绿、`ruff` 零 error。

**自检问题**（答不上来就重做，不要往下走）：

1. `model_dump()` 和 `model_dump_json()` 返回的类型有什么区别？
2. `model_validate(dict)` 和 `Model(**dict)` 有什么不同？什么时候必须用前者？
3. `temperature="0.7"` 是怎么变成 `0.7` 的？用的哪个装饰器、什么 `mode`？
4. 为什么 `Role` 要继承 `str`？不继承会怎样？

---

## 今日英语（配合这个案例）

从你刚写的代码里挑 10 个词进生词本，优先这几个：
`model` `field` `validate` `serialize` `deserialize` `coerce` `constraint` `literal` `optional` `enum`
