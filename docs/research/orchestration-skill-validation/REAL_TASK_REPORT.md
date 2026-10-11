# 首次真实复用：摄影教程研究与四层案例

日期：2026-10-11。**PARTIALLY VERIFIED**：基础发现和真实外部协作成立，最小样板通过独立冻结验收；AGY 自主浏览仍受权限阻断，ROOT 手机滚动回归触发既有图片占位/测试采样竞态。不是全自动研究能力或发布版本验收。

## 用户目标与实际接续

新的 Codex 会话仅收到“为摄影课程增加真实教程研究能力，需要找资料、改代码，并且独立验证”及通用只读规划约束；没有注入目标 Skill 或角色名称。它自行读项目 Skill、选择 AGY / CC / Verifier 分工。当前 ROOT 按该计划调用真实外部进程，负责材料整合与交付。这证明自动选择后的真实复用，未证明一个全新会话无人工或主控干预跑完全程。

基线 `805c289beaa2a75b75a8a888fbd1f190baa1dc27`。独立工作区：`.local/orchestration-agy` / `codex/orchestration-agy-20261011`；`.local/orchestration-cc` / `codex/orchestration-cc-20261011`；`.local/orchestration-verifier` / `codex/orchestration-verifier-20261011`。ROOT 在既有任务分支 `codex/evidence-photography-atlas` 整合，保留无关 dirty 字节；只有 ROOT 正式交付。

Verifier 为 fresh-context Codex reviewer，并非虚构的外部 CLI；实现启动前冻结 13 项行为标准，SHA256 `85c5edf9a3bae453302ac790ec33e64771ea7f2d405c6cff45da9e247ad2e495`。每次外部派发前与最终验收均核对原哈希，不接收 AGY/CC 提示词、日志或实现讨论。

## 真实进程（全部 UTC）

| 调用 | PID | 开始 | 结束 | exit |
| --- | ---: | --- | --- | ---: |
| agy-initial | 55564 | 2026-10-11T03:31:15.011760+00:00 | 2026-10-11T03:31:41.064294+00:00 | 0 |
| cc-initial | 46796 | 2026-10-11T03:31:15.271998+00:00 | 2026-10-11T03:33:02.922325+00:00 | 1 |
| agy-rework1 | 13444 | 2026-10-11T03:36:14.882272+00:00 | 2026-10-11T03:36:54.804861+00:00 | 0 |
| cc-rework1 | 52280 | 2026-10-11T03:36:14.880272+00:00 | 2026-10-11T03:37:55.466906+00:00 | 1 |
| agy-rework2 | 44928 | 2026-10-11T03:41:38.958207+00:00 | 2026-10-11T03:44:11.734072+00:00 | 0 |
| cc-rework2 | 10636 | 2026-10-11T03:48:26.273968+00:00 | 2026-10-11T03:50:16.481279+00:00 | 0 |

初始两次 Popen 均在任何等待前启动，真实重叠 **25.792296 秒**；第一轮修订研究与实现也实际并行。AGY 为原生 1.3.3 Headless，CC 为原生 Claude Code 2.1.220，沿用已验证 MiniMax 路由，没有切换供应商或凭据。CC 初始/返工一达到 24-turn 上限后非零退出，但确实修改了文件；最后一轮 40-turn 上限、exit 0。权限仍为限定 Read/Edit/Write/Glob/Grep，未给 CC shell。全部 6 次配置保护哈希保持，CLI SUCCESS 均没有直接当作验收。

私有 `.local/orchestration-validation/<调用>/` 保存 started/result JSON、脱敏 events 和 stderr；截图、全文观察与 Agent 原材料不进 Git。没有做费用账单或计费额度核验。

## AGY 研究与来源限制

初始命令工具被拒（`Get-ChildItem -Path .`），AGY 返回 SUCCESS 但空研究成果。返工一实际搜索后读取 `neilvn.com` 被权限拒绝，同样没有正文；保留拒绝，不绕工具访问该资源，不修权限、不强制重试。

第二轮 ROOT 使用正常 BrowserSkill Chrome Agent Window 读取另一公开来源 [Nikon《Composing Photographs》](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/composing-photographs)，核对 Diane Berkenfeld 作者与第一组前后图注，保存加载稳定的网页截图和可见文本后正常停止会话。原图公开 URL 来自真实页面 DOM，未猜 CDN、导出 Cookie、下载或改写原始字节。这是重新阅读现有来源注册项，不能称为发现了全新教程。

AGY 最后一轮实际 `view_file` 完成来源交接、PNG 和页面文本读取，实际写出 RESEARCH.json / RESEARCH.md；研究材料明确主控提供输入，未冒充自主浏览。初始/返工一仍 BLOCKED。原材料包含“反光水面”“顶部仅狭窄条带”和缺少独立支撑的视觉显著性因果线索；ROOT 实开截图后只采用保守可见描述和项目分析，未将这些推断升级为事实。没有第三轮 AGY 返工。

网页素材没有视频时间码；准确定位到第一组前图图注，B 仅保留七词原文片段、英文、实际核对日期。底部视口外、原始相机字节、EXIF、其他章节、视频、作者认可本项目建议与学习成效均未核验。独立 Verifier 再读原页并实开截图核对，详见其报告。

## CC 实现与真实返工

CC 实改可选 `case.evidence` 契约与显示：observation / quote / explanation / advice 四个独立对象。B 只有非空原文、本网关来源、有效且匹配的 HTTPS 案例页、原文定位、语言、真实公历日期和 `verbatim_checked` 全部满足才显示已核验；缺证据明确未核验，合成 fixture 不证明引文事实。

初始候选的 helper 未接入主 validator，畸形 verification 数组/对象抛 TypeError，UI 尚未交付；独立负例真实失败，返还 CC。返工一接入 validator、类型守卫、阅读器、样式与开发回归，但 Verifier 又复现空原话仍 verified、两非法 URL 归空后相等仍 verified，冻结 A-D 标记也缺失。第二轮 CC 收紧统一核验边界、真实日期与 UTF-8 测试输出；ROOT 最终整合补 A-D 标记并加入真实素材。不再调度第三轮。

开发测试历史：首跑 27 failed / 23 passed，其中 24 项被 Windows cp950 解码错误遮住，另有无效日期、unknown-layer 夹具构造及错误字符串匹配问题。最后 CC 原始开发候选 83 passed / 2 failed，两项均为夹具断言（误禁阅读器自身合法 blockquote 关闭、空 URL 被已拒绝但报错分类不同）。ROOT 修正夹具，保留负例，要求恰好一个合法 quote、恶意关闭标签保持转义、无攻击节点和非法链接；没有删除测试或调整 Verifier。

最终修改范围：`web/learning-gateways.js/.css`、`tools/validate_learning_gateways.py`、`tests/test_tutorial_evidence_display.py`、`GATEWAYS.json` 与生成的 `web/learning-atlas.json`。仅在现有 `attention-and-occlusion` / `marsh-before` 添加本次四层样板；不是新增大型课程、平台、数据库或领域 Skill。原 22 案例、32 来源声明、学习状态 API 与来源媒体策略保留。

## 当前验证与限制

- 独立冻结 F01-F13：20 passed；真实媒体/状态另 2 passed；旧显式保存、迟到响应、冲突与课程 7 passed。桌面/手机原图实际 HTTP 200，源像素和阅读截图实际打开；状态/revision 完整相等。
- ROOT 最终默认六文件核心回归：123 passed / 1 既有 Starlette/httpx 警告，80.65s。
- ROOT 最终开发与课程/状态单测：96 passed / 1 既有警告，7.80s，使用 `--basetemp=.local/orchestration-validation/final-focused`。这不代替浏览器验收。
- ROOT 课程+开发回归：114 passed / 1 failed，135.05s。失败是手机关闭重开 scrollTop 差 517；窄复测再次失败，未修改基线无控制同项一次 PASS。伴随一次 Windows WMI `0x8007000e` 资源异常，未将其直接当作根因。
- 后续只读受控单图加载对照：候选 pos 6820 → 到图 7338 → close 保存 7338 → reopen 7338；未修改 `805c289` pos 6153 → 到图 6670 → close 保存 6670 → reopen 6670。图片初始 0 高度、加载后浏览器 scroll anchoring 改 top；新增静态材料增高约 667/668，不是失败约 517 的来源。旧测试在采样 pos 后、Escape 前发生加载时误将更新的位置当恢复错误；同时既有媒体布局仍有真实异步变化。原事件在 `.local/orchestration-validation/scroll-controlled-probe/events.json`，不改产品/测试、不把 1 FAIL 改写为 PASS，留作后续窄修复。
- 原失败没有加载事件记录，不能断言那一次变化发生在关闭前还是重开后；受控对照证明同类竞态在未修改基线存在。
- build --check、两个 JS 语法检查、diff --check PASS；既有 web/app.js 与暗房任务文档字节哈希保持。

可运行回归：

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_tutorial_evidence_display.py tests/test_learning_course.py tests/test_learning_gateways.py tests/test_learning_gateways_state.py tests/test_learning_course_ui.py tests/test_learning_gateways_ui.py
.venv/Scripts/python.exe -X utf8 tools/build_photography_atlas.py --check
node --check web/learning-gateways.js
```

可运行阅读预览：`.venv/Scripts/python.exe tools/preview_learning.py --port 18767` → `/learning` → “从一个问题，换一种看法”的第一入口 → 第一组前图。预览不打开主人数据库；本轮没有更新日用服务。

## 成功标准与人工边界

自动选择、真实 AGY/CC、独立冻结 Verifier、自然发现开发问题、真实返工均有证据。AGY 自主网页研究不成立；样板通过主控提供正常浏览器输入完成。独立验收确实拦下了假核验与崩溃，但没有单 Agent 对照，不能作“更快/更便宜/统计上更可靠”的 A/B 结论。

仍需主控处理权限阻断与材料取舍；主人决定审美、教学价值和实拍迁移；新域名浏览授权配置不在基础 Skill 内。暂不全局安装，先重复发现边界和不同领域复用。正式 Git/Notion 状态在实际运行收据后独立报告，不由本文预先宣称。
