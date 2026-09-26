# 旧执行器兼容边界

`ref_lab/collector.py` 和 `providers.py` 的旧本机 CDP collector、独立 API analyzer 未删除，以免破坏已有脚本。它们不是 v0.3 的默认产品路径，正常界面不显示 API 是否 configured、不引导配置独立付费分析。启动网站不会调用这些执行器。

正常使用请看 README 与 WORKER_PROTOCOL：任务包 → 本地 Agent → BrowserSkill / 图片分析 → 导入草稿。没有独立 API 密钥也能建项目、收藏、筛选、制卡交接、导入结果、用户确认和离线导出。

旧 analyzer 必须由维护者明确调用并承担外部传图与独立费用边界；不使用网页订阅额度。本轮没有调用它，保留的模拟测试只验证兼容、失败和检查点逻辑，不代表真实模型准确率。旧 collector 的模板关键词不等于自然语言理解，也不保证平台会允许抓取。

Notion Markdown/CSV ZIP 导入继续可用，独立摄影笔记可无项目保存。在线 Notion 摘要同步仍仅在用户指定并授权目标后使用；Git tasks 是意图与验收的基准，不把未授权同步假报完成。
