# D007 实战 · CI 流水线 + W01 阶段复盘

> 对应：`weeks/W01-Python现代工程化/D007-0920-CI+阶段复盘.md`
> 目录：`code/w01/d007_ci/`
> 预计 60 min（CI 40 + 复盘 20）

---

## 场景

前面六天你写的代码，**只有你自己跑过**。

这是个人项目和工程项目的分水岭。加一条 CI，意味着：

- 每次 push，自动跑 lint + 测试
- 你搞坏东西，**10 秒内收到 GitHub 的红色邮件**，而不是三天后自己发现
- 仓库首页出现那个绿色 ✅ —— **面试官点进你的仓库第一眼看到的就是它**

**FDE 视角**：CI 不是"大厂才搞的形式主义"。
你交付给客户的东西，客户那边也会有流水线。你连自己项目的 CI 都没搭过，
到了客户现场根本没法跟对方的 DevOps 对话。

---

## 你的任务

### 第一部分：GitHub Actions（25 min）

CI 配置文件我已经写好了：**`fde-plan/.github/workflows/ci.yml`**

先**读一遍**这个文件，搞清每个 step 在干什么（不要直接抄自己不理解的配置）：

| step | 作用 |
| --- | --- |
| `actions/checkout@v4` | 把代码拉到 runner 上 |
| `astral-sh/setup-uv@v5` | 装 uv（GitHub 官方认证 action） |
| `uv python install 3.12` | 装 Python |
| `uv sync` | 按 `uv.lock` 装依赖（**锁定版本，保证可复现**） |
| `uv run ruff check .` | 静态检查 |
| `uv run pytest -q` | 跑测试 |

**然后做两件事**：

1. 推一次提交，去仓库的 **Actions** 标签页看流水线跑起来
2. **故意写一个失败的测试**，推上去，看 CI 变红 —— 你要亲眼见过红灯，
   才知道那个红邮件意味着什么

> 这一步很多人跳过，但它才是 CI 的全部意义：**见过红灯，你才会真的看绿灯**。

### 第二部分：pre-commit（15 min）

CI 是"事后检查"，pre-commit 是"提交前拦截"。
**能在本地拦住的，不要等到 CI。**

配置已写好：`code/w01/.pre-commit-config.yaml`

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv add --dev pre-commit
uv run pre-commit install
uv run pre-commit run --all-files
```

装完之后，你每次 `git commit` 都会自动跑 ruff。
代码有问题，**提交直接失败**，根本脏不了仓库。

**验证方式**：故意写一行超长代码，然后 `git commit` —— 应该被拦下。

### 第三部分：W01 阶段复盘（20 min，必须做）

打开 `fde-plan/02-进度追踪.md`，回答这五个问题。**写下来，不要只在脑子里过。**

**1. 门槛有没有过？**
W01 的过关门槛是"能独立从零搭一个带测试、带类型检查、带 CI 的 Python 项目"。
你做到了吗？具体哪一条没做到？

**2. 这七天哪一天最卡？为什么？**
是语法不熟、还是工程习惯没建立、还是英语读得慢？
定位准确才能对症下药 —— 说"都挺卡的"等于没复盘。

**3. 代码量统计**
```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan
git log --oneline --since="2026-09-14" | Measure-Object -Line
```
低于 7 个提交（平均每天 1 个）说明投入不够，W02 要加量。

**4. 你的 mini-llm-gateway 能跑吗？**
不看文档，从头启动一次：
```powershell
cd code/w01
uv run uvicorn d004_fastapi_gateway.main:app
```
打开 <http://127.0.0.1:8000/docs> 试两个接口。
如果卡住了，说明前面的知识没真正变成你的。

**5. W02 要调整什么？**
时间分配、难度、还是学习顺序？写具体的一条，不要写"继续加油"。

---

## 验收标准

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run pytest -q          # 全部通过
uv run ruff check .       # 零 error
```

外加：

- [ ] GitHub Actions 页面能看到一次**绿色**运行记录
- [ ] 你**见过一次红色**运行记录（故意弄坏的）
- [ ] `pre-commit install` 已装，且被它拦过一次提交
- [ ] `02-进度追踪.md` 里写完了五道复盘题

**自检问题**：

1. 为什么 `uv sync` 比 `pip install -r requirements.txt` 更可靠？
   （提示：`uv.lock`）
2. CI 里为什么要缓存依赖？不缓存会怎样？
3. pre-commit 和 CI 的检查项应该完全一样吗？各自的侧重点是什么？
4. 如果 CI 在你本地通过但线上失败，第一个该怀疑什么？
   （提示：环境差异 —— Python 版本、系统依赖、时区）

---

## 今日英语

`pipeline` `workflow` `runner` `job` `step` `artifact` `cache`
`trigger` `lint` `hook` `green` `red` `flaky test` `reproducible`
