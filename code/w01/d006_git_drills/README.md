# D006 实战 · Git 抢救训练（在沙箱里练，绝不碰真实仓库）

> 对应：`weeks/W01-Python现代工程化/D006-0919-Git工程化.md`
> 目录：`code/w01/d006_git_drills/`
> 预计 60 min

---

## 为什么 Git 要专门练"抢救"

日常操作（`add` / `commit` / `push`）你已经在用，不需要练。
真正卡住人的是**出事之后**：

- 提交信息打错字，还已经 push 了
- 代码提交到 `main` 了，本来应该在功能分支
- 本地 5 个「改一下」「再改一下」「真的好了」这种垃圾提交，怎么合并成 1 个
- 刚 `reset --hard` 完发现删多了
- 改了一半要切分支，不想提交又不想丢

**这些操作的共同特点：平时不练，出事时手忙脚乱，一慌就下错命令，造成二次伤害。**

所以今天在**临时沙箱仓库**里把它们全踩一遍。
沙箱删了重来零成本，你真实的学习仓库一根毛都不会少。

---

## 第 0 步：生成沙箱

```powershell
cd C:\Users\zhaojianhong\WorkBuddy\2026-09-14-09-53-42\fde-plan\code\w01
uv run python d006_git_drills/setup_sandbox.py
```

脚本会在**系统临时目录**里建一个练习仓库（不在 fde-plan 里，不会污染你的提交历史），
并造好一段"很脏"的提交历史。跑完会打印沙箱路径和当前状态。

> 每次想重来，删掉沙箱目录再跑一次脚本即可。

---

## 五个场景（按顺序做，每个都要真的敲）

### 场景 1 · 提交信息写错了（10 min）

刚提交完发现信息打错字。

```bash
git commit --amend -m "正确的信息"
```

**限制**：只能改**最后一个**提交，且**已经 push 的不要 amend**（会改写历史，坑队友）。

> ⚠️ amend 之后如果已 push，下次 push 需要 `--force-with-lease`。
> 这个参数比 `--force` 安全：它会检查远端有没有别人的新提交，有就拒绝。

### 场景 2 · 5 个垃圾提交合并成 1 个（15 min，今天的重点）

沙箱里有一串「fix」「fix again」「真的好了」这类提交。合并它们：

```bash
git log --oneline -6          # 先看清要合并哪几个
git rebase -i HEAD~5
```

编辑器里把第 2~5 行的 `pick` 改成 `s`（squash），保存退出，
然后编辑合并后的提交信息。

**必会**：

| 指令 | 作用 |
| --- | --- |
| `pick` | 保留这个提交 |
| `squash` / `s` | 合并到上一个提交，保留信息 |
| `fixup` / `f` | 合并到上一个提交，**丢弃**这条信息 |
| `drop` / `d` | 删掉这个提交 |
| `reword` / `r` | 只改提交信息 |

> **为什么这个必须会**：你的 GitHub 绿墙质量取决于提交历史。
> 面试官点开你的仓库，看到的是「update」「update2」「fix」还是
> 「feat: add retry with exponential backoff」，印象分差一个量级。

### 场景 3 · 提交错分支了（10 min）

代码提交到了 `main`，本来该在 `feature/x` 上。

```bash
git branch feature/x          # 从当前位置开分支，main 的提交也带过去
git reset --hard HEAD~1       # main 退回一步
git checkout feature/x        # 切过去，代码还在
```

**关键点**：`git branch` 只是创建一个指向当前提交的指针 —— 不复制代码。
所以先开分支再回退 main，代码就"转移"过去了。

### 场景 4 · 删多了，用 reflog 找回（10 min）

模拟灾难：

```bash
git reset --hard HEAD~3       # 假装误删了 3 个提交
git log --oneline             # 看起来真没了
git reflog                    # 救命稻草
```

`reflog` 记录了**HEAD 的每一次移动**。找到 reset 之前那个提交的哈希，然后：

```bash
git reset --hard <那个哈希>
git log --oneline             # 回来了
```

> **reflog 是 Git 的安全网，但有时限**（默认 90 天）。
> 出事第一时间查 reflog，别乱操作覆盖了记录。

### 场景 5 · 改了一半要切分支（10 min）

```bash
echo "半成品" >> file.txt
git stash                     # 暂存工作区
git status                    # 干净了
git checkout other-branch     # 随便切
git checkout -                # 切回来
git stash pop                 # 取回改动
```

常用变体：

| 命令 | 用途 |
| --- | --- |
| `git stash` | 暂存 |
| `git stash list` | 看暂存了哪些 |
| `git stash pop` | 取回最近一次并删除 |
| `git stash apply` | 取回但保留备份（可多次应用） |
| `git stash -u` | **连未跟踪文件一起暂存**（默认不存新文件，这个坑很常见） |

---

## 验收标准

五个场景全部**亲手敲过一遍**，且能不看文档回答：

1. `--amend` 和 `rebase -i` 的区别？什么时候只能用前者？
2. `reset --hard` vs `reset --soft` vs `reset --mixed`，改动分别去哪了？
3. `reflog` 记录的是什么？默认保留多久？
4. `git stash` 默认不暂存什么类型的文件？怎么让它一起暂存？
5. 已经 push 到远端的提交，想改写应该用什么参数？为什么不用 `--force`？

**加分项**：把 `git log --oneline --graph --all` 设成别名 `git lg`，用一辈子。

```bash
git config --global alias.lg "log --oneline --graph --all --decorate"
```

---

## 一个必须遵守的纪律

**今天所有操作只在沙箱里做。**

`fde-plan` 是你真实的学习仓库，里面已经有提交、有远端、绿墙在涨。
不要拿它练 `reset --hard` 和 `rebase -i` —— 等你熟练了再说，
而且要练也是先 `git branch backup` 留条后路。

---

## 今日英语

`amend` `squash` `rebase` `reflog` `stash` `cherry-pick` `detached`
`upstream` `fast-forward` `conflict` `discard` `restore` `HEAD`
