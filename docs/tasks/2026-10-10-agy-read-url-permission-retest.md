# AGY 网页读取权限：最小修复与真实复测

## 原始意图与边界

用户要求针对上次 `codex/agy-headless-video-pilot-20261010` 的网页读取拒绝，进行“最小、可回滚的真实修复与复测”。只补指定域名的 `read_url` Allow，备份原配置，保留原有设置；遇到更高优先级 Ask 或明确 Deny 不覆盖。禁止 `--dangerously-skip-permissions`，不改代理、凭据、IDE、其他权限或摄影主数据，不开发 Agent 框架。

先要求新的 Headless 会话通过 `read_url_content` 读取 `https://www.antigravity.google/docs/cli/headless/`，保存 stream-json、工具结果、denied_actions、stderr、退出码和正文。只有真实正文与未拒绝工具同时成立才算成功；成功后才添加 B&H 的具体域名规则并读取公开摄影教程。YouTube 播放/下载单独记录，不借网页权限推断。

## 检查与验收

- 实际 Windows 当前 `agy.EXE --version` 是 **1.3.3**，不同于上轮记录的 1.3.2；不安装、更新或降级 CLI。
- 实际用户配置为 `C:/Users/Dell/.gemini/antigravity-cli/settings.json`。初始 Allow 仅 `read_url(youtube.com)`；Ask、Deny 均为空。
- 在原试验干净 worktree 与原任务分支记录结果，保留主工作区未提交改动。配置备份、全文和原始日志留在 `.local/agy-readurl-retest/`，不进 Git。
- 阅读上轮任务、运行报告、实际拒绝事件及 Publisher 回执后再修改。保留历史 PARTIAL 与拒绝证据；本轮只修配置权限边界。
- 比较原配置和最终配置：只允许增加 `read_url(antigravity.google)` 和条件成立后增加 `read_url(bhphotovideo.com)`。其他 JSON 值必须完全相同，并保留原文格式。
- 实际双站读取与可复现命令、回滚办法、局限写入 `docs/research/agy-headless-video-pilot-20261010/READ_URL_RETEST.md`。仅提交本任务记录与该报告。

## 执行结果

已备份配置原字节，按顺序补入两个指定域名 Allow；完整 JSON 比较确认其余设置值相同，Ask/Deny 未新增。首次会话后观察到仅格式变化，原始配置格式不再逐字相同；原始字节备份保持可回滚，受保护回滚 dry-run PASS，未实际回滚。

官方页 `read_url_content` DONE，取得并检查 215205 字节抓取文件及可见正文；新会话退出 0，stderr 空，denied_actions 未出现。官方域名权限修复 VERIFIED。

B&H 授权后新会话不再 soft-deny，但工具 ERROR HTTP 403，没有正文，不能算网页读取成功。配置保护检查中止后曾误启动一次未授权 B&H 会话，exit 0/SUCCESS 空正文且 denied_actions 非空，全部失败证据保留。详见 READ_URL_RETEST.md。

当前实际 AGY 是 1.3.3；没有验证旧 1.3.2 的本轮行为。YouTube 播放/下载未运行，未新增相应权限。保留历史试点 PARTIAL、主工作区改动及摄影数据；不绕过 403。AGY 自定义 hook 的引号错误仍出现，兼容性 FAIL，未修它。

本轮满足最小配置修复与真实复测/如实报告的执行要求；B&H 正文访问仍受阻，不宣称两站读取均成功。配置要求的仓库 checks、commit/push/Notion 状态由正式 Publisher 实际回执另行报告。


## 正式记录交付路径

主项目实际检查：`.venv/Scripts/python.exe -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py` 得到 **70 passed，1 依赖弃用 warning**；`node --check web/app.js`、`git diff --check` 均 exit 0。这些是项目兼容检查，不证明 B&H 读取或 YouTube 视频能力。

真实 AGY 复测与私人证据保留在原试验 worktree。该 worktree canonical finish 实际记录 Git/Notion SKIPPED，原因 TASK_DELIVERY_NOT_AUTHORIZED；其本地 SUCCESS 回执不代表发布。未改写该回执或扩大授权。两份正式文档转交已配置授权的主项目目录，在现有任务分支 codex/evidence-photography-atlas 通过本轮最初编辑前已启动的 root 事务交付；仅新增这两个文档，保留主项目预先存在的所有未提交改动。未合并旧试验分支或重捕先前改动的基线。最终实际 checks、Git/Notion 与远端 SHA 以 root canonical receipt 为准。
