# GitHub 推送指南

> 本地部分已配置完成。下面是从「配公钥」到「第一次推送」的完整步骤。

## ✅ 状态：已全部配置完成并推送成功

- SSH 连接已验证（`ssh -T git@github.com` 返回 `Hi owen0278!`）
- 远端仓库：https://github.com/owen0278/fde-learning-plan
- 远端地址：`git@github.com:owen0278/fde-learning-plan.git`，默认分支 `main`，已设置 upstream
- 首次推送已完成，共 136 个文件 / 2 个提交

下面内容保留作为日后排查参考。

## 已完成的配置

| 项目 | 值 |
| --- | --- |
| 提交用户名 | `owen0278` |
| 提交邮箱 | `027788@163.com` |
| SSH 密钥 | `~/.ssh/id_ed25519`（已生成） |
| 首次提交作者 | 已从占位值修正为 `owen0278` |

> **最后确认一件事**：GitHub 的绿墙是按「提交邮箱」匹配账号的。
> 所以你在 GitHub → Settings → Emails 里的主邮箱，必须也是 `027788@163.com`，且状态为已验证。
> 如果不一致：要么去 GitHub 把 163 邮箱设为 Primary，要么执行下面两条命令改成你 GitHub 的主邮箱。
>
> ```
> git config --global user.email "你的GitHub主邮箱"
> git commit --amend --reset-author --no-edit
> ```
>
> 趁现在只有 1 个提交，改起来是零成本的。

---

## 第一步：把公钥加到 GitHub

复制下面这一整行（从 `ssh-ed25519` 开始到结尾）：

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPR2glZoPUQ3TnXl0HBVPAfdcaIKk0jKZlwHuBF7cDXx 027788@163.com
```

然后：

1. 打开 <https://github.com/settings/ssh/new>
2. Title 随便填，比如 `工作电脑`
3. Key type 保持 `Authentication Key`
4. Key 框里粘贴上面那一行 → **Add SSH key**

## 第二步：验证连接

在终端里执行：

```
ssh -T git@github.com
```

第一次会问 `Are you sure you want to continue connecting?`，输入 `yes`。
看到 `Hi owen0278! You've successfully authenticated...` 就成功了。

> 如果一直超时：国内直连 GitHub 的 22 端口经常不通。告诉我，我给你配代理或改走 443 端口的方案。

## 第三步：在 GitHub 上建空仓库

打开 <https://github.com/new>

- **Repository name**：建议 `fde-learning-plan`
- **Description**：建议 `从中软国际 Java/前端背景转型 FDE 的 16 周学习计划与项目产出`
- 选 **Public**（必须公开，面试官才看得到；绿墙也才有用）
- **全部勾选框都不要勾**：不要 Add README、不要 .gitignore、不要 license

点 Create repository。

## 第四步：推送

页面上会显示你的仓库地址，形如 `git@github.com:owen0278/fde-learning-plan.git`。

在本目录下执行：

```
git remote add origin git@github.com:owen0278/fde-learning-plan.git
git branch -M main
git push -u origin main
```

> 记不住也没关系，把仓库地址发我，我来推。

## 之后的日常流程

每天学完，在本目录执行两条：

```
git add .
git commit -m "docs: 完成 D008 任务卡复盘"
```

攒个三五天推一次就行：

```
git push
```

### commit 信息规范

绿墙看的是「有没有提交」，但面试官点进去看的是「提交信息专不专业」。按这套写：

| 前缀 | 用于 |
| --- | --- |
| `feat:` | 新增功能模块 |
| `fix:` | 修 bug |
| `refactor:` | 重构，功能不变 |
| `test:` | 补测试 |
| `docs:` | 文档、笔记、README |
| `chore:` | 环境配置、依赖升级 |

示例：

```
feat: 实现基于 pgvector 的混合检索
fix: 修复 chunk 重叠导致的重复引用
docs: D023 复盘，补充 LLM 采样参数笔记
```

## 隐私红线

这个仓库是公开的。任何时候都**不要**提交：

- 公司项目的源码、配置、数据库结构
- 客户名称、合同、工单等真实业务数据
- API Key（`deeplive_sk_xxx` 这类一旦推上去会被扫描机器人秒刷）

第三点最容易中招。正确做法是把 key 放进 `.env`，并在 `.gitignore` 里加上 `.env`（我已经加好了）。
如果不小心推上去了：立刻到对应平台作废该 key，历史记录里的删不掉。
