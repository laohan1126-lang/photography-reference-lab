# Codex → AGY Headless 摄影研究试点

## 原始意图与边界（2026-10-10）

用户要求：“本轮必须实际调用 `agy`，不能只描述理论架构。”验证“是否真的可以只操作 Codex，就完成 Antigravity 与 Codex 的整条研究接力”。仅研究一条真实专业人像/Cosplay 拍摄视频，保留至少两个有价值的现场调整节点，再让 AGY 基于 Codex 独立核验的底稿表达中文教程，由 Codex 验收。

使用分支 `codex/agy-headless-video-pilot-20261010`、独立 worktree。基线为远端 `codex/evidence-photography-atlas` 的 `b3b28868cf4b1f8a2956a293313fe969daaf5381`。保留正常工作区现有修改，不改正式 UI/课程/能力地图，不开发门禁框架，不使用其历史 PASS。不开 Antigravity IDE，不用其他 Agent 冒充 AGY，不改全局权限/代理/凭据，不跳过权限，不合并或部署。

## 可观察验收

1. 实际检查 AGY 路径/版本/help，执行小探测及真实网页读取；保留进程退出码、status、conversation_id、工具事件、stderr 和可用 usage。
2. AGY 找 2–3 个候选；Codex 独立核实来源、获取实际媒体、打开关键帧、对齐对白和时间码。未知条件保持未知。
3. AGY 写作只使用核实底稿；Codex 逐项检查重要事实，最多两轮局部返工。最终样板要可自学、能执行、有取舍说明。
4. `docs/research/agy-headless-video-pilot-20261010/` 交付 EVIDENCE.md、LESSON.md、RUN_REPORT.md。媒体、截图、完整工具日志保留 worktree 的 Git 忽略 `.local/`。
5. 如实判定 FULL/PARTIAL/BLOCKED；通过 canonical Publisher 提交/推送本次四份文档并核验远端 SHA，Git/Notion 独立报告。

## 执行结果

实验结果：**PARTIAL**。实际调用 7 次 AGY Headless（另执行版本/help），其中 6 次退出 0/SUCCESS、4 次返回实质文本；首次直连探测静默后终止，两次网页读取权限拒绝均仍返回 SUCCESS 空正文。主研究 conversation 成功恢复完成搜索、教学初稿与两轮局部修订；11 次 search_web 确实完成，AGY 未观看视频。

Codex 独立纠正候选来源，最终从同一 B&H 系列替代发现 Jerry Ghionis 真实影棚示范。打开 23 份截图，教学采用两个时间码节点及四张私人过程帧。完整英文自动字幕已读，但未人工原音听校；原视频离线下载 403。因此完成真实教学样板与主控交接实验，未宣称完整媒体归档/对白核验通过。

已交付 EVIDENCE.md、LESSON.md、RUN_REPORT.md；3 项明确事实错误及其他夸大表达已处理，最终仍保留证据边界。未修改产品代码、课程或能力树，未开 Antigravity IDE，未修改全局配置或绕过权限；媒体、截图、日志与临时工具均在忽略目录。

已实际运行 `.venv/Scripts/python.exe -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py`：70 passed、1 dependency deprecation warning；`node --check web/app.js`：exit 0。复用现有 venv 的本地忽略 junction，未安装依赖。这些检查验证仓库回归，不证明摄影事实或真人学习效果。正式 seal/finish 与远端 SHA 结果以 canonical Publisher 回执和本轮最终交付为准，不在提交前预填成功。

复核方式：阅读 EVIDENCE 的来源与节点；从本机 LESSON 的四张图片对照相邻帧，回到原片 06:22–06:35、14:24–15:30 核对口令。若继续研究，只补原媒体保存与原音听校，不能重用本次自动字幕作为人工对白校验。
