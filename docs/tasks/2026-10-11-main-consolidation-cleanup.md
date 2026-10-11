# 当前版本整合 main 与旧副本清理

## 用户原意与边界

“你以现在版本为基准，合并到 main，然后把 D:\AI PROJECTS 里面旧版本或者备份或者一些分支删掉，以后不得建在这里，只能建在 D:\AI PROJECTS\photography-reference-lab 主文件夹下。”

本次明确授权把主目录当前完整项目版本（包括此前未提交的项目成果）作为整合基准，并合并、正常推送 main；不是重新选取旧工作树内容来覆盖当前教材。私人图片、数据库、凭据、浏览器配置和临时测试目录不进入 Git。此前已暂存的项目命名整理成果也属于此当前版本，先备份原 index/patch，再按精确清单纳入；不 reset 或丢弃用户成果。

清理仅针对 D:\AI PROJECTS 顶层经核实属于本项目的旧工作树与备份，以及已停用的本地分支。其他项目、正常资料库及 C:\Users 下其他聊天的工作树不属于此次删除范围。旧分叉的独有文件和提交先归档到主仓库 `.local/backups/`，核对字节后再移除旧目录；不删除唯一原图或学习/筛选记录，不删除远端分支，不改写共享历史。

## 起点与完成标准

事务 `01a12b7e-1690-7992-94d3-f0c3d679eb7b` 在首个实施编辑前启动；原基线指纹 `62b8e4bb022e60809e364370bd73feeba1967c57e02ca2fe595965c9e7f65a0e` 保留。当前分支 `codex/course-field-architecture-20261011`，起点 `fc6290cc4978529fdd9f58ed6cea02bab736de8a`；main 与实际 fetch 的 origin/main 同为 `2068dc2e9f269af38a261a92af34f8779a08b980`，是当前版本祖先，相差 173 个提交，可正常快进。

- C1：当前版本按确切路径正常提交，main 保留全部既有历史并包含当前版本；推送后读取远端 SHA 核验。
- C2：删除前恢复归档和逐文件清单/hash 验证通过；授权旧目录移除、过期工作树登记及停用本地分支清理，日用运行路径仍在主目录。
- C3：项目规则和摄影编排工作流明确目录边界；两门课最终文件与已验收字节一致；Git、canonical Publisher 和 Notion 结果分别如实记录。

## 实施前保全与协议限制

已保存当前 79 个项目路径的字节、原 index、staged/worktree patch、所有 refs 和 `git bundle --all`，在 `.local/backups/consolidation-20261011-2305/`。凭据模式扫描通过；15 个不属于产品的未跟踪临时文件排除。完整归档不进入 Git。

读取前两轮 FAILED 发布回执及本机 canonical Publisher 实现：该工具只支持首次编辑后的新 owned delta，不支持显式接管编辑前 dirty 内容，`bind-existing` 只绑定已成功终结的任务。本次用户明确授权当前全版本整合，但这不代表 Publisher 新增了 adoption 能力。整合按用户明确授权执行独立、正常的 ROOT Git 命令，保留原 baseline/receipt；不修改工具、目标、权限或原事务来伪造自动发布成功。仍执行其 seal/finish 并单独保留实际结果，Notion 若因此受阻则保留待同步。

## 结果

当前版本已正常提交为 `1b6e665f1d94a3ef58fcad97b61d952f0732393e`，83 个精确路径（包括 rename 的旧名删除），父提交为原 HEAD。通过祖先检查和 compare-and-swap 快进 main，再正常 `git push origin main`；UTC `2026-10-11T15:22:09.474475+00:00` 读回远端 SHA 与该提交一致。此过程没有改写共享历史、force-push 或修改原 Publisher baseline。整合过程中保持当前工作区正文原字节，避免先切回旧 main 再检出造成换行重写。

12 个旧目录完整归档，普通文件总计 3,250,806,819 字节。归档解压读取逐文件 SHA256 与原文件相同，删除前又复核源目录完整文件集合/hash；7 个指向主 `.venv` 的 junction 单独记录目标，仅移除指针、不递归链接目标。随后以 PowerShell 7 原生 `Remove-Item -LiteralPath` 清理，目标每次均解析确认是授权顶层目录，主环境保留。实际移除路径：

```text
D:\AI PROJECTS\photography-reference-lab-agy-headless-20261010
D:\AI PROJECTS\photography-reference-lab-antigravity
D:\AI PROJECTS\photography-reference-lab-calibration-20261010
D:\AI PROJECTS\photography-reference-lab-cc-minimax-20261010
D:\AI PROJECTS\photography-reference-lab-gate-20261010
D:\AI PROJECTS\photography-reference-lab-multi-agy-20261010
D:\AI PROJECTS\photography-reference-lab-multi-cc-20261010
D:\AI PROJECTS\photography-reference-lab-multi-pilot-20261010
D:\AI PROJECTS\photography-reference-lab-multi-repair-20261011
D:\AI PROJECTS\photography-reference-lab-multi-verifier-20261010
D:\AI PROJECTS\photography-course-synthesis-20261010
D:\AI PROJECTS\_backup_codex-darkroom-20261007-203745
```

Git `worktree prune --expire now` 清除不存在目录的登记；对应 11 个本地分支逐一核对已备份的精确 HEAD、未被其他工作树使用后移除。9 个不在当前版本历史中的实验提交仍能从 bundle 恢复，没有硬塞进 main。远端分支和其他项目未删。完整清单与恢复映射为 `.local/backups/consolidation-20261011-2305/manifest-external.json`，原 index/patch 和 refs 位于同一归档；恢复一个旧实验时先在主仓库 `.local/worktrees/` 内新建隔离目录，从 bundle 取回相应 refs，并按 zip/manifest 恢复其文件；junction 指针记录单独保留。

目录约束已进入 AGENTS、README、当前项目编排 Skill 和回归入口。当前发现验收脚本 `.forge/codex-multi-agent-orchestration/run_discovery.py` 的用户案例目录从顶层改到主目录 `.local/validation/`，创建前核对解析后的边界。实际正反路径检查通过：仓库内目录创建成功，外部测试路径在创建前被拒绝；没有启动新的模型发现会话，历史 native 发现结果不冒充新路径的发现结果。

## 实际验证与限制

- 两门课六个最终 canonical 文件与原独立 LP-01–LP-05 PASS 候选 SHA256 相同；原 28 个过程/来源文件也保持。复用未变内容的手机/桌面阅读证据。
- `.venv/Scripts/python.exe -X utf8 tools/build_action_directing.py --check`、`tools/build_photography_atlas.py --check`：PASS。
- `.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_agy_browser_bridge.py`：63 passed，2 skipped（本环境无法创建测试用 symlink），1 原有依赖 warning，3.19 秒；没有删除或削弱这些测试。
- 三份实际 `node --check`（app.js、learning.js、learning-gateways.js）及验收脚本 Python 编译：PASS。实际路径约束正反例：PASS。
- 首次 `git diff --cached --check` 对原始 `AGY_POLISH_DIFF.md` 的嵌入统一 diff 空上下文行报 trailing whitespace；核对其原字节和单空格语义后原样保留，记录原 FAIL。其余 82 个 staged 路径的 scoped check：PASS。未通过改写原始证据消除检查结果。
- 独立 Reviewer 核对恢复快照、候删绝对路径、bundle 分支、junction 和删除脚本，通过后才执行；进程命令行未发现依赖旧目录，日用 Python 和只读预览使用主目录环境。未把合成测试当作实拍或审美认可。

收尾规则与本记录的最终提交、切换 main、远端 SHA 及 canonical Publisher 实际回执继续保存在本事务私有交付证据中；只按真实结果报告。Publisher 无 dirty adoption 能力，其失败不抹掉上述实际 Git 成功；Notion 如受其 Git 前置条件阻止则待同步，不改目的地。
