---
description: 提交 Staged Changes 中的代码，并在推送前同步远程 main
---

# 提交 Staged Changes 的代码
提交当前已暂存的代码变更，并按以下固定流程执行。

## Git 提交规范
使用约定式格式：`<type>(<scope>): <主题>`，其中 `type = feat|fix|docs|style|refactor|test|chore|perf`。主题最多 50 字，使用祈使语气。简单改动仅需一行提交信息；复杂改动添加正文说明改动内容和原因，每行最多 72 字。

## 强制执行流程
1. 仅基于当前 `Staged Changes` 生成提交信息并完成本地提交。
2. 本地提交成功后执行 `git fetch origin main`。
3. 将 `origin/main` 合并到当前分支。
4. 如果合并成功且无冲突，执行 `git push`。
5. 如果存在冲突，立即停止，禁止继续推送，并输出：
   - 冲突文件列表；
   - 建议使用 `git status` 查看冲突；
   - 手动解决后执行 `git add <文件>`；
   - 再执行 `git commit` 完成合并，然后重新推送。

## 失败处理
- 当前目录不是 Git 仓库时直接停止。
- 无法获取 `origin/main` 时直接停止。
- 不要自动 `stash`、跳过同步或使用强制推送。
