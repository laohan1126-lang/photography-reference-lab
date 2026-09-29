# 旧执行器兼容边界

`ref_lab/collector.py` 和 `providers.py` 的旧本机 CDP collector、独立 API analyzer 未删除，以免破坏已有脚本。它们不是 v0.3 的默认产品路径，正常界面不显示 API 是否 configured、不引导配置独立付费分析。启动网站不会调用这些执行器。

正常使用请看 README 与 WORKER_PROTOCOL：任务包 → 本地 Agent → BrowserSkill / 图片分析 → 导入草稿。没有独立 API 密钥也能建项目、收藏、筛选、制卡交接、导入结果、用户确认和离线导出。

旧 analyzer 必须由维护者明确调用并承担外部传图与独立费用边界；不使用网页订阅额度。本轮没有调用它，保留的模拟测试只验证兼容、失败和检查点逻辑，不代表真实模型准确率。旧 collector 的模板关键词不等于自然语言理解，也不保证平台会允许抓取。

Notion Markdown/CSV ZIP 导入继续可用，独立摄影笔记可无项目保存。在线 Notion 摘要同步仍仅在用户指定并授权目标后使用；Git tasks 是意图与验收的基准，不把未授权同步假报完成。

## Windows / WSL 运行边界

Windows 是当前日常主运行环境：FastAPI、collection adapter、BrowserSkill CLI 与 Edge 在同一 Windows 运行时中。仓库启动器必须从当前 checkout 启动自己的 Windows venv，不接受仓库外 regression 目录或临时 worktree 作为正式依赖。

WSL/Linux 保留为开发、CI 和兼容路径。它可以运行 Web/CLI，也可以在需要时探测挂载到 `/mnt/c/Users/*/.local/bin/bsk.exe` 的 BrowserSkill，但这不是默认日常部署。跨环境兼容不等于共享活动数据库：Windows 与 WSL 应使用独立 `LAB_DATA_DIR`，迁移通过 backup/restore 完成。

旧的 WSL `run_server.sh` 若存在于用户机器上，属于本机历史配置，不是仓库发布物。Windows Golden Path 通过后应停止依赖它。

