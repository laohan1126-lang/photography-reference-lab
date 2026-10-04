# 新版本地回归与规则收敛 — 2026-10-05

## 用户意图

用户希望找到此前 GPT 在 GitHub 上大改的新版本，拉到本地跑回归，然后修改前轮审查发现的补丁。修复原则：连续特判、fallback、否定规则暴露抽象问题时替换旧模型，不继续外围包补丁。

## 来源与边界

- GitHub PR #5：codex/library-discovery-optimization-20261002，已核验 c7244ab49fc99d73b94fe70cc5d75619411018f6。
- 独立任务分支：codex/patch-convergence-20261004；日常分支 ffe9ecb 保持原位。
- 先验证未修改的新版，再在任务分支整合共同祖先83c422a之后的四个日常修复，保留新版图库与手机免密/网络兼容能力。
- 复用已有 Windows Python 依赖；所有测试使用隔离临时数据。不读写日常数据库，不启停日常服务，不迁移资料库，不调用付费模型，不合并main或自动部署。
- 本轮处理已复现的运行时身份、配置作用域、归档身份、分析结果、预检证据、采集目标/完成语义和判断上下文失效问题。保留人工选择、原图、来源、revision与验收门槛。

## 设计与验收

FastAPI/SQLite/Pillow与无构建Web继续沿用。新增图库模块及导航保持；复用现有配置、/api/runtime、用例与任务协议，删除重复保存和启发式伪视觉结论。改动限于上述根因涉及的代码、回归及说明。

验收：新版基线回归；每个根因新增或更新真实失败回归；联合后端/Windows脚本检查；Chromium组件、HTTP/Cookie、图库、历史导入与离线流程；两份JS语法及git diff --check。测试成功不等于真实审美或日常部署成功。执行命令、失败及限制追加在下方。

## 执行记录

- 已成功fetch新版，独立worktree加载ref_lab确认为本目录；已安装NumPy2.5.3无需安装新依赖。
- 新版未改代码基线回执存.local/convergence-evidence/baseline-core.xml，最终结果见下一条。

- 未修改c7244ab的Windows非浏览器全范围基线：227 passed / 1 failed / 1 skipped，102.93s。失败test_real_process_is_stopped_on_cancel：取消后子进程仍写入must-not-exist；跳过仅因外部审美manifest缺失。没有把该失败计为通过。
- 日常四个提交整合仅web/app.js锁定函数冲突，保留新版LibraryDiscovery.reset及免密状态guard。

## 根因收敛与当前检查点

- 草稿资格由 service.apply_analysis 统一决定；删除 worker 再次 save_card 的兜底。五类不合格结果均已先复现失败，再验证没有草稿复活或冒充人工产出。
- Windows 采集复用已有原生 Job Object supervisor，在任何 adapter 代码执行前拥有本轮进程树；删掉不再调用的 taskkill 依赖。取消、超时、退出后后代与无结果等实际子进程回归通过，未承诺服务硬崩溃自动恢复。
- 预检只报告解码、尺寸、哈希与诊断测量。删掉标题/色块/皮肤比例和低边缘能量产生的身份、人数、动作与模态断言；新的 producer 为 deterministic_preflight，视觉判断为 unknown/uncertain。
- 默认本地适配器仍是严格 COS 搜索器：角色/服装硬约束来自 project_snapshot，自由 notes 只作检索语境，不再用子串猜布尔条件。不限角色、非 COS、细致构图要求继续交给 Agent/manual 任务包；这轮不虚构自然语言理解能力。
- requested preferred_sources 顺序与来源受阻证据独立保留。未查询/受阻来源分别保留 source_checks/gaps；正常查询零命中不是来源故障。preferred_sources 仅是优先级，有本轮候选且至少一个实际来源 usable 即可 completed，所有来源不可用、无来源或零候选仍 blocked。数量是软目标，不足数量只保留 gaps，不作为硬配额。执行预算仍最多40张，但缺口按原请求数量报告。
- UI 删除重复的 raw 预检事实面板，复用有证据来源标记的统一展示。派生 JPG 导出失败保留已提交的人工选择，并显示 archive_error，不能再固定 toast 已自动归位。

已执行主工作树检查：root worker/runner 46 passed；删旧 taskkill 校验后的 runner 30 passed；浏览器六模块 30 passed（365.71s）；新增免密手机 HTTP 流程 1 passed（5.90s）；node --check web/app.js 与 git diff --check 通过。采集 subagent 的提交经审阅整合为 d39072d；64 passed/1 deselected 是其针对性结果，未运行项等待 state 的只读历史投影整合，不当作主分支已通过。

真实手机公网隧道、当前日用库切换、登录态 BrowserSkill 搜图及 Antigravity 实际逐图分析尚未执行。网页免密测试与合成图回归不能证明这些外部链路或视觉准确率。

运行时提交审阅后整合为 afaf3dc。删除任意 Python/端口占用者认领与停止规则，唯一 PID 记录保存本轮进程创建时间、实际服务 PID、源码/库身份及启动 Git SHA。官方 launcher 保留就绪结果；备用 Python daemon 仅委托它。其独立分支实测 78 passed（含 Windows PowerShell 5.1 与 pwsh 7 真实隔离启动/复用/拒绝/停止），主分支联合结果以末尾验收为准。旧 PID 记录缺少身份字段时新版本拒绝管理；升级日用实例必须先用原启动器停止，不能删除记录后硬认领。启动 SHA 不证明未提交源码编辑被冻结，修改代码应重启。


## 证据、状态与归档收敛

- identity_digest 绑定角色、作品、服装、拍摄要求和显式身份修订。项目输入变更让旧预检、图像判断、卡片上下文失效，保留 K/I/M/X 人工选择与原始历史；器材变更只影响卡片。旧已确认记录须有完整的既有验收指纹和卡片上下文证明，不能默认绑定到当前角色。
- 删除启动时改写旧启发式预检及截断历史的修复逻辑。API 只投影 known-untrusted/stale 为未核验，数据库原记录不改；列表过滤、图库和排序同步遵守证据边界。
- 共享预检投影同时核对生产者、当前引用图片 SHA 和项目输入；实际 replace API 的旧图片历史回归先失败，再修正。历史接口使用同一 SQLite 读取快照，不能将旧资产记录继续标作有效。
- 角色已确认 JPG 是所有有效项目引用的派生投影，按稳定引用/资产身份命名，并只清理本系统明确拥有的命名空间。删除旧1000条上限、标题子串寻址和单项目清理共享目录的规则；CAS与来源原图不改。
- 状态事务提交后统一触发归档投影，失败保留已提交选择，返回实际 archive_error；UI 明确显示失败。错误详情暂存在当前 Library 实例内存，重启后仍通过实际文件存在性判断归档，不声称持久化错误日志。
- 二次复核纠正了本轮自身的错误假设：早先 blocked=bool(gaps) 将软数量目标硬化。已直接删除该规则，未增加缺量特判。相应1/60完成、来源受阻与零有效图回归已通过。

这些针对性结果不替代以下联合验收。共享归档使用 SQLite 写锁串行生成以保证快照一致；高并发大库投影性能未做基准，本轮不引入队列或缓存框架。


## 联合验收过程与复核纠错

- 首次联合全量核心：302 passed / 1 failed / 1 skipped，190.90s；回执 integration-core-first.xml。失败并非图片被自动选中，而是纯 pending 导入触发了空角色已确认目录。删除提前 mkdir，由实际 JPEG 导出创建父目录；只有已有目录才执行原有严格扫描，避免 glob 吞掉权限错误。runner/state 两组先验证45 passed，最终结果见下方。
- 六模块浏览器：32 passed，305.27s；回执 final-browser.xml。随后归档修正的手机免密和失败提示两项重验2 passed，9.51s；browser-archive-final.xml。
- 原协议同时指出 preferred_sources 是规划优先级，不要求机械全部查询。二次复核再次发现此前 all(source_checks) 把优先级变成硬门槛，已删除错误 all-of 规则；源受阻的事实始终独立保留。40张执行预算不能在文案里称达到60张原请求目标。
- 这些纠错直接替换完成/副作用规则，没有用新的必选来源配置或每来源兼容分支掩盖旧抽象。


## 可复跑命令

在本工作树运行以下 PowerShell 命令，Python 复用日用仓库已安装的虚拟环境。无需安装依赖，数据仅为测试临时目录；运行时测试只启动自身隔离实例。每次 core 与 browser 应分别使用新的 basetemp。

```powershell
Set-Location 'D:\AI PROJECTS\photography-reference-lab-convergence-20261004'
$env:PYTHONPATH=(Get-Location).Path
$env:PYTHONDONTWRITEBYTECODE='1'
$taskPython='D:\AI PROJECTS\photography-reference-lab\.venv\Scripts\python.exe'
$taskTemp=Join-Path $env:TEMP ('ref-lab-core-'+[guid]::NewGuid().ToString('N'))
& $taskPython -B -X utf8 -m pytest -q tests --ignore=tests/test_browser.py --ignore=tests/test_live_system_regression.py --ignore=tests/test_ui_components.py --ignore=tests/test_collection_ui.py --ignore=tests/test_library_browser_ui.py --ignore=tests/test_library_browser_http.py -p no:cacheprovider --basetemp $taskTemp --junitxml=.local/convergence-evidence/final-core.xml
$taskTemp=Join-Path $env:TEMP ('ref-lab-browser-'+[guid]::NewGuid().ToString('N'))
$env:LAB_TEST_ARTIFACTS=Join-Path (Get-Location).Path '.local/convergence-evidence/browser-artifacts'
& $taskPython -B -X utf8 -m pytest -q tests/test_ui_components.py tests/test_collection_ui.py tests/test_library_browser_ui.py tests/test_library_browser_http.py tests/test_browser.py tests/test_live_system_regression.py -p no:cacheprovider --basetemp $taskTemp --junitxml=.local/convergence-evidence/final-browser.xml
node --check web/app.js
node --check web/library-browser.js
git diff --check
```

测试过程包含替身 Agent 与合成图，不能视为真实 BrowserSkill 搜索/Antigravity 视觉核验通过。当前工作树不带日用 .local/config.json，不应直接作为日用库升级启动。启用新版本须另做受控切换和真实手机公网 Golden Path；这轮仅本地分支验证，不会将旧日用 PID 记录删除后接管。


## 最终本地验收

状态：PARTIALLY_VERIFIED。本地实现和自动回归通过，外部真实链路未验证，不是日用部署或发布回执。

- 最终核心全范围：306 passed / 1 skipped，131.94s，无失败；final-core.xml。跳过项仅 test_aesthetic_benchmark 的外部真实 manifest 缺失，不能宣称审美准确率通过。
- 浏览器六模块：32 passed，305.27s；final-browser.xml。真实 Chromium 包含本地 HTTP/Cookie 与免密390px手机视口、选择持久化、跨项目图库、历史导入和离线文件包；图片与Agent结果仍为测试合成/替身。
- 归档融合失败先记录302 passed / 1 failed / 1 skipped；修复后runner/state45 passed；浏览器手机免密与错误提示复验2 passed。最终核心已覆盖归档严格扫描版本，首次失败证据未覆盖删除。
- 两份 JS 的 node --check、92个 ref_lab/tools/tests Python 源文件内存 AST 解析、git diff --check 均通过。现有 Starlette/httpx 弃用警告仍在，不安装无关依赖掩盖它。
- 日用仓库 HEAD 仍为 ffe9ecb353d7ad424d7549543c50a4d90f791446、codex/data-safety-recovery-20260930，工作区干净。任务修改只在 codex/patch-convergence-20261004 及对应独立工作树。
- 未启动/替换日用实例、迁移日用数据、合并main、推送任务分支、写Notion或调用外部付费服务。仓库 AGENTS 禁止自动发布；本轮只保存本地提交与延后发布回执。

剩余限制：真实手机公网隧道、真实平台登录与 BrowserSkill 下载、当前 Antigravity 实际逐图分析、人类审美验收均未跑，因此不能据此承诺只打开 Antigravity 和资料库就已全链路可用。默认本地适配器仍只负责严格 COS 候选检索和文件检查，A/B/C开放式选择与视觉核验仍走 Agent/manual 协议。旧PID身份记录的受控停机升级、历史未知文件清理和高并发共享归档性能另需独立验收。
