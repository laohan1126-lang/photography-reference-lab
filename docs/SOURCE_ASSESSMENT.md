# 搜索来源评估 · 2026-09-27

这是**匿名公开页面探测 + 官方文档审阅**，不是用户登录态 BrowserSkill 搜图质量测试。没有下载新的真实候选包，不能声称九个来源均已接通；每轮 Agent 必须重新判断。当次探测遇限制后未重试、未绕行。

| 来源与一手入口 | 当次可观察结果 | 产品取舍 |
|---|---|---|
| [小红书](https://www.xiaohongshu.com/explore) | 匿名入口重定向到 login | 保持重要来源；本机正常登录后评估角色/版本正片。登录不可用就报告，不让网站维护专用爬虫。 |
| [Pinterest](https://www.pinterest.com/) | 探测返回 403 | 保持重要动作/审美发现来源；真实 Pin 质量与原作者追溯待登录浏览器验证。403 不等于网站对用户不可用。 |
| [Cosplayers Archive](https://www.cosp.jp/photo_search.aspx) | 公开页呈现照片关键词、作品与角色入口 | 日文角色搜索值得按需尝试；未验证作者原图下载与会员限制。不要把场地/器材分区混入人物搜索。 |
| [Curecos](https://curecos.com/) / WorldCosplay 线索 | 此探测工具无法访问 | 保留为可选线索，不假设旧 WorldCosplay 链接仍可用，不投入固定适配器。 |
| [X](https://x.com/) | 403 | 按实际授权会话尝试原作者/角色标签；未验证搜索产出。 |
| [Instagram](https://www.instagram.com/) | 429，停止 | 适合按原作者线索评估；本轮未验证，不重试消耗账号安全余量。 |
| [微博](https://weibo.com/) | 探测工具报告访问受限 | 中文原帖线索按本机正常浏览条件评估，未验证搜索产出。 |
| [FilmGrab](https://film-grab.com/) | 公开页面可读，呈现影片目录/画面入口 | 纳入审美扩展选项；电影截图不自动成为可执行摆姿，更不代表用户有传播授权。 |
| [ShotDeck](https://shotdeck.com/) | 官方产品入口可读 | 仅已有合法访问权限时使用；没有登录/订阅搜索与下载测试，不新增购买要求。 |

选择优先级来自用户用途与当次可操作证据，不是经过量化比较的“全网最好”排名。搜索优先权、登录成功、图片相关性、来源可追溯、原图可取得、下载授权是不同维度。Agent 可以停用低产来源，也可以添加实际更合适的来源，但须写真实 query_log、source_checks、gaps。

## BrowserSkill 对接结论

[腾讯官方仓库说明](https://github.com/Tencent/BrowserSkill)：本地 CLI / daemon + Chrome/Edge 扩展 + Agent 技能，使用已登录配置，在可见 Agent Window 执行；支持本地模式文件操作，远程模式当前不支持上传/下载。`bsk doctor` 是连接检查，不是 Agent 已发现技能或搜图已成功的证据。

因此默认架构是“网站保存任务和结果 → 本地 Codex / Antigravity 读任务 → BrowserSkill 正常浏览并取得独立文件 → 导入包”，不是新增网站内自动爬虫。没有运行用户的 BrowserSkill 会话，没有登录网站；此实现验证了任务包完整性、导入状态和安全边界，不把未完成的平台测试写成通过。
