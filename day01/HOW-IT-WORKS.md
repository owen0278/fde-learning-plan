# day01 工程是怎么跑起来的

本文用 `day01/hello-fde` 这一个只有 2 行代码的项目，把 Python 工程的运行机制讲透。
所有结论都在本机实测过，不是推测。

---

## 一、工程里到底有什么

去掉 `.venv` 之后，全部文件只有这些：

```
day01/hello-fde/
├── .python-version      一行：3.12
├── pyproject.toml       项目身份证
├── uv.lock              依赖精确版本锁
├── README.md
└── src/
    └── hello_fde/
        └── __init__.py  你的全部业务代码（2 行）
```

**代码 2 行，配置文件 4 个。** 这是 Python 工程和 Java 工程最大的思维差异 ——
Java 靠 `javac` + `java` 就够了，Python 需要「环境 + 依赖 + 入口」三套约定配合。

### 与 Java 的对照表

| Python | Java 对照 | 作用 |
| --- | --- | --- |
| `pyproject.toml` | `pom.xml` | 项目名、版本、依赖、入口声明 |
| `uv` | Maven / Gradle | 解析依赖、建环境、跑任务 |
| `.venv/` | 本地依赖隔离（更像前端 `node_modules`） | 每个项目一套独立包 |
| `uv.lock` | 依赖树锁定 | 保证别人装出来的版本和你完全一样 |
| `src/hello_fde/` | `src/main/java/com/xxx/` | 源码根目录 |
| `[project.scripts]` | shade 插件的 `mainClass` | 声明程序入口 |
| `__pycache__/*.pyc` | 编译后的 `.class` | 字节码缓存，不用管 |

---

## 二、pyproject.toml 逐段解释

```toml
[project]
name = "hello-fde"              # 项目名，也是包名来源
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"      # 最低 Python 版本要求
dependencies = []               # 运行时依赖（空 = 目前不依赖任何第三方库）

[project.scripts]
hello-fde = "hello_fde:main"    # 冒号左=模块名，右=函数名

[build-system]
requires = ["uv_build>=0.12.13,<0.13.0"]
build-backend = "uv_build"      # uv 自己的轻量构建后端

[dependency-groups]
dev = [
    "ruff>=0.16.7",             # 只在开发时需要，不会打进生产
]
```

**最关键的是 `[project.scripts]` 那两行。** 它声明：
把 `hello_fde` 模块里的 `main` 函数，包装成一个叫 `hello-fde` 的命令行命令。

`uv sync` 时，uv 会在 `.venv/Scripts/` 下生成一个 `hello-fde.exe`（47KB 启动器）。

---

## 三、完整执行链路：`uv run hello-fde` 背后发生了什么

### 第 1 步：你敲命令

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\day01\hello-fde
uv run hello-fde
```

`uv run` 的含义是：**在这个项目的虚拟环境里执行后面的命令**。
它会自动向上找 `pyproject.toml` 和 `.venv`。

> 这就是为什么**不需要先 `activate`**。
> 传统方式要先 `.venv\Scripts\activate` 激活环境，`uv run` 把这一步省了。
> 这是 uv 相比 pip + venv 最实用的改进之一。

### 第 2 步：uv 定位虚拟环境

`.venv/pyvenv.cfg` 记录了环境的来源：

```
home = C:\Users\zhaojianhong\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none
implementation = CPython
uv = 0.12.13
version_info = 3.12
include-system-site-packages = false
```

注意 `include-system-site-packages = false` ——
**这个环境看不见系统装的包**，只认识自己 `.venv` 里的。
这是避免"我机器上能跑，别人机器上跑不了"的核心设计。

### 第 3 步：执行入口脚本

uv 在 `.venv/Scripts/` 里找到 `hello-fde.exe`，运行它。
这个 exe 只做一件事：启动本环境的 Python，然后执行
`from hello_fde import main; main()`。

### 第 4 步：解释器启动时加载 .pth（最关键的机制）

Python 解释器启动时会**自动扫描 `site-packages` 目录下所有 `.pth` 文件**，
把里面写的每一行路径追加到 `sys.path`。

本机 `.venv/Lib/site-packages/hello_fde.pth` 的内容只有一行：

```
C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\day01\hello-fde\src
```

**这就是「可编辑安装」（editable install）的全部秘密。**
它不复制代码，只留一张"去哪儿找代码"的纸条。

传统 `pip install .` 会把代码**复制**进 site-packages，你改源码不生效，每次都要重装。
可编辑安装只放一个 `.pth` 指向源码目录，**改完立刻生效**，这才是开发时该用的方式。

### 第 5 步：import 并执行

解释器在 `sys.path` 里找 `hello_fde`：

```
src/hello_fde/__init__.py   ← 命中
```

这个文件的内容：

```python
def main() -> None:
    print("Hello from hello-fde!")
```

`import` 时整个文件被**执行一遍**（所以 `main` 函数被定义出来），
然后入口脚本调用 `main()`，打印出结果。

> Python 没有 Java 那种"必须有个 public static void main 的类"的强制要求。
> 约定是写一个 `main()` 函数，再在配置里指过去。

---

## 四、三种运行方式对比（含一个必踩的坑）

| 命令 | 结果 | 原因 |
| --- | --- | --- |
| `uv run hello-fde` | ✅ 正常输出 | 走入口脚本，路径已由 `.pth` 配好 |
| `uv run python main.py` | ❌ `No such file` | **uv 0.12 起改用 src 布局，根目录没有 main.py** |
| `uv run python -m hello_fde` | ❌ `No module named hello_fde.__main__` | `-m` 要求包里有 `__main__.py`，本项目没有 |

第三条值得展开：`python -m 包名` 找的是 `__main__.py`，
而 console script 找的是 `pyproject.toml` 里指定的 `main` 函数。
**两者是不同的入口约定**，不要混用。

想让 `python -m hello_fde` 也能跑，加一个文件即可：

```python
# src/hello_fde/__main__.py
from hello_fde import main

main()
```

---

## 五、动手验证（每条都可以直接粘到 PowerShell）

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\day01\hello-fde
```

**实验 1：看 sys.path 里到底有什么**

```powershell
uv run python -c "import sys; [print(i, p) for i,p in enumerate(sys.path)]"
```

最后一项应该就是 `...\hello-fde\src`。这就是 `.pth` 的功劳。

**实验 2：看模块被解析到哪个文件**

```powershell
uv run python -c "import hello_fde; print(hello_fde.__file__)"
```

输出 `...\hello-fde\src\hello_fde\__init__.py`。

**实验 3：证明代码没被复制**

```powershell
uv run python -c "import hello_fde; print(hello_fde.__file__.startswith('C:\\Users\\zhaojianhong\\WorkBuddy'))"
```

输出 `True` —— 说明用的是**你源码目录里的文件**，不是 site-packages 里的副本。
你可以试着改 `__init__.py` 里的文字，不重装直接再跑，立刻生效。

**实验 4：看入口脚本的依赖来源**

```powershell
cat .venv\Lib\site-packages\hello_fde.pth
```

只有一行路径。整个"安装"就是这么简单。

---

## 六、四个必须建立的认知

**1. `.venv` 不进 git，但 `uv.lock` 必须进。**
`.venv` 是本地产物（几十 MB，且含机器相关绝对路径），
`uv.lock` 记录了每个依赖的精确版本和哈希，别人 `uv sync` 才能装出一模一样的环境。
本仓库 `.gitignore` 已配好：`.venv` 忽略、`uv.lock` 入库。

**2. `uv run` 不等于激活环境。**
它只影响这一条命令。想连续敲多条，才需要 `activate`：
```powershell
.venv\Scripts\Activate.ps1
```

**3. 换机器要重跑 `uv sync`。**
`.venv` 不进 git，所以新机器 clone 下来没有环境，必须重建。
这也是为什么 `05-多机同步指南.md` 里第一步就是 `uv sync`。

**4. 代码不要放在项目根目录。**
用 `src/` 布局的理由：如果代码在根目录，你在项目根跑 python 时，
当前目录会自动进 `sys.path`，**测试会 import 到散装文件而不是安装后的包**，
掩盖真实的路径问题。src 布局强制你走"安装后"的路径，问题会提前暴露。

---

## 七、和 W01 实战项目的关系

`code/w01/` 那个 `mini-llm-gateway` 用的是同一套机制，只是多了内容：

| day01/hello-fde | code/w01 |
| --- | --- |
| 单个包 `hello_fde` | 多个子目录 `d002_message_models` 等 |
| `dependencies = []` | 有 pydantic、fastapi、pytest、httpx |
| 一个入口 `hello-fde` | 靠 `uv run pytest` / `uv run uvicorn` 运行 |
| 2 行代码 | 每天一个可运行模块 + 验收测试 |

`code/w01/pyproject.toml` 里同样有 `[project.scripts]`，
也走 src 布局，也靠 `.pth` 把源码挂进 `sys.path` —— **机制完全一致**。

搞懂 day01，后面 15 周的项目结构你都能看懂。

---

## 八、速查：出问题时先查这三处

| 症状 | 排查点 |
| --- | --- |
| `No such file or directory` | 布局变了，确认代码在 `src/` 还是根目录（`uv --version` ≥ 0.12 用 src） |
| `ModuleNotFoundError` | `.pth` 没生成 → 重跑 `uv sync` |
| 改了代码不生效 | 装成了非 editable → 重跑 `uv sync`，检查 `.pth` 是否存在 |
| `command not found: hello-fde` | 命令名看 `pyproject.toml` 的 `[project.scripts]`，不是包名 |
