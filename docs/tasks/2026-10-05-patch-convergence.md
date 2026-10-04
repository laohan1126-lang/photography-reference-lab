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
- 新版未改代码基线回归运行中，回执存.local/convergence-evidence/baseline-core.xml。

- 未修改c7244ab的Windows非浏览器全范围基线：227 passed / 1 failed / 1 skipped，102.93s。失败test_real_process_is_stopped_on_cancel：取消后子进程仍写入must-not-exist；跳过仅因外部审美manifest缺失。没有把该失败计为通过。
- 日常四个提交整合仅web/app.js锁定函数冲突，保留新版LibraryDiscovery.reset及免密状态guard。
