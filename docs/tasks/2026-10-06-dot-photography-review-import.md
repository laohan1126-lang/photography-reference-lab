# Dot 摄影参考图导入待筛入口 — 2026-10-06

## 用户意图与边界（实施前）

用户原话：“把那个dot找到的图片，把它给我导到这个参考库里面去。然后把它分类什么的分好。”在确认目的地后，用户选择“独立待筛入口（推荐）”。

- 来源为用户 Google Drive 中的“摄影参考专案_待GPT二筛”。先读说明指出主候选 238 幅、240 份图片（两份为兼容副本），另外 8 幅已有反馈讨论、12 幅边界讨论；P256 仅历史留存，不提交给 AI。仅主候选作为本次待筛导入；讨论及历史留存不改动。
- 独立待筛入口不代表用户已喜欢，不建立角色身份，不自动写 K/I/M/X、全局审美收藏、资料卡或人工验收。Dot 的逐图文字保留来源与“助手判断”身份，不能当作本次逐图视觉核验。
- 原文件字节、Drive 文件与公开出处、署名、使用限制、编号和兼容副本关系必须保留。不得公开传播或生成/改图。不得覆盖现有用户数据或审美笔记。
- 下载与导入可断点续做；重跑按稳定编号及哈希核对，报告成功、重复、失败与未完成项。新图片不得提交 Git。

## 可观察验收

1. 待筛入口单独列出 Dot 主候选，默认待筛，能打开本地图片、检索编号/主题/来源，并看到明确的来源与限制。
2. 238 幅作品与 240 文件的对应关系可核验；兼容副本不增加作品数。P256 和讨论图不进入主候选。
3. 对现有库做写前备份和只读基线；导入后核对数量、字节哈希、已有项目/收藏数据未被改写。重复执行不覆盖已有人工决定。
4. 相关 API、迁移、导入幂等和 UI 验证有实际结果；失败或阻断项逐项记录。

## 结果与验证（实施后追加）

已将 Google Drive 主候选 238 幅 / 240 文件下载到私有 `.local/dot-import-20261006` 并逐文件核对大小、解码、尺寸和 SHA-256；240 个 SHA 均不同，审计无异常。P256、反馈讨论和边界讨论均未导入。预演与隔离库全量导入成功后，给日用库做 SQLite 备份，再导入 238 条独立 `study_candidates` 和 240 个 Asset；全部初始为 `pending`。Dot 文字匹配出的主题仅作为带“未视觉复核”标记的检索提示，未创建 Inspiration 或角色 Reference。

日用库导入前后对照：schema 3→4，项目 23、Reference 891、Inspiration 23、任务 64、笔记 0 均不变；旧项目/引用/收藏/任务/笔记/Asset 行内容未改变。Asset 891→1131，238 条待筛记录的主图及兼容图 SHA 集合与 240 条审计清单完全一致。SQLite `integrity_check=ok`；导入前已有的 72 条外键错误仍为 72 条，本任务未改动这些旧记录。备份位于私有批次的 `backups/64ff9c072092/library-before-dot.sqlite3`。

新增 v4 迁移、独立候选 API、修订冲突与幂等导入、AVIF 原字节保存、清理保护，以及侧栏待筛浏览/人工状态/笔记。隔离库迁移、重导和人工编辑保护回归通过。规定核心回归：`python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_dot_study_import.py`，结果 **119 passed, 1 warning**。`node --check web/app.js` 和 `git diff --check` 通过。真实 HTTP 临时服务与 Chromium 实测：候选总数 238、P285 单项检索、图片预览加载、无 JS 错误；服务已停止。

完整 Chromium 组件回归 `tests/test_ui_components.py tests/test_collection_ui.py`：**19 passed, 1 warning**。真实 HTTP/浏览器回归 `tests/test_browser.py tests/test_live_system_regression.py`：**7 passed, 1 warning**。最后收紧了兼容副本来源 ID 的冲突检查，针对性回归 **3 passed, 1 warning**；`python -m compileall -q ref_lab tools tests` 通过。最终再次只读核对日用库：schema 4、完整性 ok、既存外键错误仍为 72、旧行差异空；导入预演再次核对 238/240。

在日用库上重复执行完整导入，结果 `created=0, existing=238, failed=0`。再比对既有行及计数，仍无差异，事件数也保持 2974；这验证了实际批次重跑不会重建候选或覆盖现有数据。人工状态保护另由 revision/重导回归证明，日用库没有替用户做人工选择。

仍未逐张视觉审定 238 幅，主题提示和 Dot 判断不能作为用户的正向审美分类。用户需在待筛入口逐图决定优先/普通/跳过。日用启动器记录存在无进程的旧 PID，本轮没有删除或覆盖；浏览器实测使用同仓库的临时本地端口。下次回归从已导入的私有批次重跑预演和幂等检查，再验证人工选择未被覆盖、图片仍可打开。
