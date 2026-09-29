# Nightly Project Consolidation — 2026-09-29

## Intent recorded before editing
The owner asks for evidence-first consolidation, not more features: inspect current code/history/tests, distinguish VERIFIED / FAILED / UNVERIFIED, make only narrow justified repairs, and leave 1–3 high-value next actions. Preserve user data and local uncommitted work. No main merge, deployment, paid API, new product scope, or broad refactor.

Target: `laohan1126-lang/photography-reference-lab`, `codex/reference-library-rebuild`.
Audit snapshot: `2b1e843be901aa193d8d0828a8366e4b88f477ae`.
Window: `a930cfdfec01013ac0d52d6bd7744febb96fb29c` (last commit before 2026-09-28 UTC) through snapshot; GitHub comparison reports 51 commits. Snapshot authored 2026-09-28 17:51:41 UTC / 2026-09-29 01:51:41 UTC+08. File dates are not UTC timestamps.

## Observable acceptance criteria
1. One-click collection must not bypass the configured command/receipt ownership by opportunistically detecting BrowserSkill. No adapter means visibly blocked, with task-package recovery.
2. `PYTEST_CURRENT_TEST` must not change production dispatch.
3. Cover BrowserSkill present/absent, pytest marker present/absent, and configured/missing adapter. Existing transport tests cover actual subprocess/import behavior.
4. CI must include existing collection-status browser regressions.
5. Preserve manual BrowserSkill + Agent task packages and historical explicit helpers; do not invent a provider or claim live visual acceptance.
6. Verify changed code, record exact scope, and refresh target HEAD before integration. No force push.

## Findings and bounded changes
**FAILED at snapshot, reproduced:** the exact dispatcher extracted from the fetched source selected the unfiltered BrowserSkill helper when `PYTEST_CURRENT_TEST` was absent, even with `LAB_COLLECTION_COMMAND` configured. With the pytest marker present it selected the adapter. A four-case isolated routing probe produced 2 passed / 2 failed. The complete source copy was checked against Git blob `c6aa17767d2073e2e41d410826f2b1d557b90add` before modification.

The default dispatcher now always delegates to `run_collection_attempt`; the transport remains responsible for configuration, attempt ownership, validated result imports and truthful blocked states. BrowserSkill remains available through a configured adapter or explicit Agent task-package workflow. This removes an undocumented automatic DOM-scraper bypass; it does not remove BrowserSkill support or rewrite old helper functions. The same source-extracted routing probe then produced 4 passed / 0 failed; changed Python files compiled. These probes prove routing only, not application/browser/visual quality.

Added 8 dispatch regression cases using actual application fixtures, and included both those cases and `tests/test_collection_ui.py` in CI. Full new CI results are recorded below; the earlier checkpoint did not claim them passed before inspection.

## Existing runtime evidence
Snapshot has successful GitHub Actions runs, including PR run `36461151099`. Its workflow omitted `tests/test_collection_ui.py`, and production dispatch bypassed the tested path. Therefore green CI did not prove live acquisition correctness.

## Environment boundary
GitHub connector can read/write repository metadata and text. The isolated container could not resolve github.com, so clone failed; this is not an application test failure. No access to the owner's Windows worktree, live service, database, BrowserSkill session, or uncommitted changes. No private data changed. Source-extracted probes are not full-suite runs. Live specific-skin cosplay hit rate, local upgrade/restart and UI acceptance remain UNVERIFIED.

## Other audit leads — do not silently expand tonight's scope
- README/architecture retain obsolete statements that screening sessions, quality/ranking and versioned profiles are not implemented. Source modules and API handlers now exist; implementation existence is not product acceptance. This checkpoint supersedes those historical status statements, not the documented safety or data contracts.
- `makeTransferable()` says downgrade moves into the inspiration library, but `make_transferable_candidate()` only updates project-reference flags/lane. Unlike `archive_reference_to_inspiration()`, it does not save a global inspiration or detach project use. This is a concrete code/UI discrepancy, not yet application-runtime reproduced in this checkpoint.
- Historical `collect_via_bsk()` still uses cumulative imported IDs for success and catches individual import errors. It is no longer the automatic entry point; do not re-enable it without current-attempt/filter/cancellation tests.
- The latest I/archive action has an API test, but I was removed from the existing filmstrip shortcut loop. Do not interpret K/M/X coverage as coverage of the new I UI path.

## Post-change verification — VERIFIED, bounded scope
Tested code commit: `3e5d93d27260f4f0d1d1ee97889d73336eac1583`.
GitHub Actions run: https://github.com/laohan1126-lang/photography-reference-lab/actions/runs/36465247028

| Runtime / evidence | Observed result | Job ID |
| --- | --- | --- |
| Core, Python 3.11 | 148 passed, 4 warnings, 24.27 s; node syntax check and compileall passed | 109073576694 |
| Core, Python 3.13 | 148 passed, 4 warnings, 24.54 s; node syntax check and compileall passed | 109073576625 |
| Browser, Python 3.12 + Chromium | 23 passed, 1 warning, 147.81 s | 109073576235 |

All three job conclusions were independently read as success; decoded logs were inspected. These are the configured regression suites, not a claim that every imaginable path or every repository test was run. The two core rows repeat the same 148 cases on different runtimes; do not advertise them as 296 distinct cases.

Downloaded and inspected `synthetic-browser-evidence`, artifact ID `10989018225`: https://github.com/laohan1126-lang/photography-reference-lab/actions/runs/36465247028/artifacts/10989018225
Archive SHA-256: `40063c3cdf1f84c0c02ef3918680b217fd5b4024d0a3b45b0ebea3c0b7ae3127` matched the upload log. Its `commit.txt` matches the tested SHA. JUnit reports 23 tests, 0 failures, 0 errors, 0 skipped. The artifact includes synthetic desktop/mobile/blocked-state screenshots and historical migration/HTTP reports; no real search photographs or user database are included. The new five collection-UI cases appear in JUnit, including blocked HTTP 200, failed/cancelled/running responses, and a late result not overwriting another dialog.

Warnings concern existing test-client/Pillow deprecations; they did not fail the suites. Do not upgrade dependencies solely to remove warning text during this consolidation.

The application change is only `collector.py` (+7/-21). Other changed files are the new dispatch test, two CI command inclusions, and this handoff. No database migration, UI rewrite or source-provider expansion was made tonight.

## Integration receipt
The target branch was re-read at `2b1e843...`, and comparison confirmed the tested commit was one commit ahead with no divergence. After all three CI jobs succeeded, `codex/reference-library-rebuild` was fast-forwarded to `3e5d93...` with `force=false`; GitHub returned success. This final handoff update is documentation-only on top of that tested code. `main` was not updated or merged. The audit branch `codex/nightly-20260929-2b1e843` retains the tested code checkpoint. No claim is made that the owner's local service already runs this version.

---

# NIGHTLY HANDOFF

## Today
本轮已提交变更主要包括：候选身份/预检/排序与筛选会话；本地采集适配器、严格搜索与负面过滤修正；项目归档、跨项目复制/转移和沟通板；Windows 启停脚本及回归测试。比较范围有 51 条提交，文件列表为新增或修改，没有整文件删除。

此前“导入 30 张”的记录已经在采集任务文档中降格为传输证据，不能证明 30 张都是指定皮肤真人 COS 正片。今晚发现并复现了测试环境与真实环境入口分流，使严格适配器可能被旧 DOM 抓图绕开的回归。

## Current State
在隔离测试环境，库管理、导入、任务执行器和现有浏览器回归通过；采集入口分流已修复并进入开发分支。真实“按完整要求搜到可用照片”的用户 Golden Path 仍未完成本机验收，不能宣布项目已成熟或搜索质量已通过。

## Verified
- VERIFIED：原入口分流缺陷有运行复现；修复后的同一探针 4/4 通过，新增应用夹具回归纳入核心套件并通过。
- VERIFIED：指定代码提交的核心回归在两种 Python 上各 148 passed；浏览器 23 passed；语法/编译检查通过；CI 产物 SHA 与 JUnit 核对一致。
- VERIFIED：既有普通 I 归档 API 回归随核心套件运行，检查全局收藏、移出项目、回收入口和恢复；不把它等同于两个 UI 入口都已验收。
- FAILED（原快照，已修复）：安装 BrowserSkill 时，真实入口能绕过配置的适配器，而 pytest 路径不会。
- UNVERIFIED：本机工作区是否有未提交内容、服务实际版本、原数据库升级/重启、外站访问、真实角色/皮肤命中率与人工审美验收。

## Open Issues
1. 真实受约束采集尚缺当前版本证据；元数据规则不是视觉模型，不能用搜索词或图片数量冒充身份/照片正确性。
2. 普通 I 与已过滤候选“降级为通用灵感”的代码效果和 UI 文案不一致，后者没有同样的全局归档动作；尚需真实服务/浏览器回归复现。
3. 历史文档状态过时、旧 BrowserSkill helper 尚在，属于已记录技术债；不为清理外观扩大今晚范围。

## Changes Made Tonight
实际改动 4 个文件：`ref_lab/collector.py`、`tests/test_collection_dispatch.py`、`.github/workflows/regression.yml`、本文件。只修入口、补测试覆盖并留交接；没有重构、新增产品功能或改用户数据。代码提交和完整验证见上文；最终补充只修改文档。

## Tomorrow
### 1. 本机部署核对并完成一轮真实受约束搜索
价值：直接验证当前最重要的用途，而不是继续增加功能。
执行：先保护未提交工作、确认并备份实际 LAB_DATA_DIR；在正确分支/虚拟环境拉取并启动。以“王昭君·长夜焕生，仅真人 COS 正片，保留用户完整自由要求”为样本，确认实际走配置适配器。保存 job ID、完整要求、独立原图/来源、回执及纳入/排除理由，由人逐图判定角色、版本和照片类别。
完成标准：有可供用户实际选择的合格候选，或明确记录外站/结果不足导致的 BLOCKED；后者不等于搜图目标完成。错角色、错皮肤、游戏/插画不得标成已视觉核验；不得凑数。人工筛选后刷新/重启，选择仍保存。
适合：普通 Agent 做部署与证据采集；遇到跨层故障再用强 Agent；图片正确性和喜好需人工最终判断。

### 2. 收敛两个“通用灵感”入口
价值：防止用户以为已收藏、实际只改变项目引用属性。
执行：用隔离数据库和浏览器分别走普通 I、已过滤候选降级；断言全局库、项目成员、keep 计数、资产复用、恢复行为及 UI 文案。先复现，再按现有“入审美库、不占角色位”的要求做最小修复，不能顺带改审美学习系统。
完成标准：界面承诺与持久状态一致；重复操作不复制图片文件；其他项目引用与人工判断不受损；新增针对性回归及相关现有测试通过。
适合：普通 Agent；只有现有产品规则无法消除歧义时才交人工决定。

## Start Here
接手仓库 `laohan1126-lang/photography-reference-lab`，继续 `codex/reference-library-rebuild`。先 `git status --short`、`git fetch origin` 并核对分支/HEAD；工作区干净且可快进时才拉取，禁止 reset/clean/覆盖他人改动。先读 AGENTS.md 和本文件，不需要重查全部 51 条提交。代码基线 `3e5d93d27260f4f0d1d1ee97889d73336eac1583` 已有 run `36465247028` 的 148×2 核心及 23 浏览器通过证据，其后夜间交接提交仅改文档。禁止恢复 PYTEST_CURRENT_TEST 业务分流或自动 BrowserSkill DOM 后备；保留显式 BrowserSkill + Agent 任务包。先做 Tomorrow 1，再处理 Tomorrow 2；不要把真实搜图尚未验收误解为要继续设计新系统。

## Project Status
**CONVERGING — B. 收敛 / 打磨，尚未基本成熟。**
已有功能足够进入真实使用验收；现在不值得继续扩大排序/偏好系统、替换架构、美化界面或机械增加测试数量。下一轮 Pro 长任务只在出现可复现的跨 UI/worker/持久化故障、数据完整性风险、普通 Agent 无法定位的筛选失效，或用户明确提出新的高价值需求时投入。两项验收收敛后暂停无目的 polishing，按实际使用问题再开任务。

---

## 2026-09-29 收敛与验收记录 (Execution Receipt)

### 1. 真实受约束搜索验收 (VERIFIED)
- 本机环境：WSL Ubuntu-26.04，Python 3.14 venv。
- 启动配置：`LAB_COLLECTION_COMMAND` 明确配置指向 `tools/collect_adapter.py`，经由 `/api/capabilities` 确认 `collection_adapter_configured: True`。
- 测试输入：项目 `legacy-changye-huansheng`，要求：“只找王昭君长夜焕生这个皮肤的真人 COS 正片；不要游戏截图、皮肤特效、官方插画、立绘、CG、壁纸、商品图、人台服装展示”。
- 执行任务：Job ID `bd9bd219507848c7b8836390a0d4dfb2`，调用 `/api/jobs/{id}/run-antigravity`。
- 实际观察结果：
  - 适配器针对用户指令提取 7 组带负向词的搜索 queries（`-游戏截图 -插画 -立绘 -壁纸...`）。
  - 在 Bing 扫描到 119 条元数据记录，全部被负向词规则严格过滤（识别为非真人 COS / 游戏特效 / 插画）。
  - 执行器诚实返回 `status: blocked`，`summary: "严格检索没有得到满足硬条件的候选；宁可少图，不用插画/游戏图凑数。"`，导入 0 张伪造图片。
  - 未发生任何通过假成功、插画冒充或绕过逻辑的情况。

### 2. 两个“通用灵感”入口收敛 (VERIFIED)
- 问题根因：普通快捷键 `I` / 按钮（`/api/references/{id}/archive-inspiration`）会调用 `keep_inspiration` 保存到全局 `inspirations` 表，并写入 `detached_at` 将其移出项目活跃队列（不占位）；而预检拦截候选上的“降级为通用灵感”（`/api/references/{id}/make-transferable`）此前仅修改了 `lane="inspiration"`，未调用 `keep_inspiration()`，未设置 `detached_at`，导致依然滞留在项目候选流中。
- 修复与收敛：
  - `ref_lab/service.py:make_transferable_candidate()`：调用 `keep_inspiration()` 保存到全局审美库；写入 `detached_at=now()`、`detached_reason="archived_to_inspiration"`；重置 `decision="pending"`（若原为 keep）；移出当前项目活跃列表与过滤流；支持在 `view_recycle`（回收站）查看与恢复。
  - `web/app.js:makeTransferable()`：传递当前项目索引以便平滑重新对齐视图，通知文案统一为“已降级归档至审美库，不占用角色参考位”。
  - 核心回归测试扩展：
    - `tests/test_personal_library.py` 新增 `test_make_transferable_candidate_archives_to_inspiration_and_detaches_from_project`。
    - `tests/test_candidate_pipeline.py` 增强 `make-transferable` 后全局灵感库存在性、主流/过滤流移除及回收站可见性的断言。
- 运行验证：
  - 核心回归：149 passed（原 148 + 新增 1），耗时 25.55s。
  - 浏览器/UI 组件回归：23 passed（11 + 5 + 5 + 2），耗时 ~120s。
  - 语法/编译：`node --check web/app.js` 及 `python -m compileall ref_lab tools` 均通过。

