# AGY Chrome 接入修复与三 Agent 重复实跑

## 原始意图与边界（冻结）

用户要求：“把他修复吧 把agy流程正式跑通 然后你就可以沉淀skill以后彻底稳定3agent工作流”。本轮修复已定位的有限授权/浏览调用接入，实跑 AGY 研究、CC 实现、独立 Verifier 验收；只沉淀项目级 Skill，不全局安装。不能把两次成功推成所有网站、视频或长期无人值守都稳定。

ROOT 在首个编辑前启动并声明事务 `01a1293a-29b3-7582-8a42-cbd900f40ac9`，基线 `eb2874540e30ee3c79008b3a80de30e77199c6f2`。保留既有 dirty `web/app.js` 和无关临时/任务文件。唯一声明的外部修改路径为 `C:/Users/Dell/.gemini/antigravity-cli/settings.json`，修改前私人备份，精确规则差异与受保护回滚；不更换凭据、代理、供应商、浏览器设置或用户标签页。

## Blueprint

- 复用 Windows AGY 1.3.3、现有 CC/MiniMax 路由、BrowserSkill 0.3.2 与在线 Chrome 实例；不安装软件或新依赖。
- 增加薄的只读浏览桥接脚本：只允许绑定实例、新建 Agent Window、公开来源导航、文字/HTML观察、截图及可靠清理。限制来源/输出范围，拒绝借用标签页、交互表单和任意命令；用固定脚本命令授权，避免 `command(*)` 或 `command(bsk)`。
- CC 在独立 worktree 实现桥接和真实回归；AGY 在独立 worktree 自行调用、实看截图、输出研究材料。研究成功后 CC 接收材料，最小整合现有教程案例与精确原站媒体登记；沿用 A/B/C/D 渲染与原架构。
- ROOT 只整合声明文件、任务报告和 Skill 前检门槛；浏览器具体操作放领域运行说明，不放基础 Orchestration Skill。日用服务、数据库、学习状态、图库与既有阅读器缺陷不在改动范围。
- 独立 Verifier 标准先冻结：`.local/agy-flow-verifier-20261011/.local/verifier/criteria.json`；SHA256 `383add69bd140165b86d60909118fc26c6c1d128d9bd031fea0ae115c5ba5f21`，UTC `2026-10-11 04:35:56`。只发最终候选/原始证据，不发实现讨论。
- 每次外部进程保留 PID、UTC 起止、非敏感 argv、工作区、退出/超时、工具事件和原始失败。两个不同教程用新 AGY 会话实跑，不能用 ROOT 观察替代。最多两轮真实定向返工，不降低标准。

## 历史与修复边界

已读前两轮 Publisher 历史：默认 Ask 在 Headless 自动拒绝；此前域名授权后官方正文真实成功，B&H 仍 HTTP403。上一轮 ROOT 先要求命令读取项目，返工又禁止 shell，导致 AGY 从未进入已连接的 BrowserSkill Chrome 通路。保持有限授权、真实失败和独立验证；删除不了失败事实，不能用 CLI SUCCESS 或另一个 Agent 的浏览替代。

## 验收与实际结果

待实跑后追加：权限差异/回滚、两次 AGY 自主浏览、真实 CC 代码、独立 V01-V10、相关回归、Skill 发现检查和 Git/Notion 收据。原始日志、截图、全文与配置备份仅存 Git 忽略的 `.local`。

### 当前实跑结果

实际原因分为模型 API 入口、Headless 文件/命令权限、连接实例与网页能力。用户恢复自己已有的代理后，模型入口恢复；ROOT 没有改代理或凭据。有限文件规则补齐，Windows quoted-path 命令采用完整原始行后，AGY 预检与浏览实际执行，不靠 Chrome 登录推断授权。

最终只增加12条有限 allow（6固定命令、2域名、4读路径），备份原哈希与整份 JSON 对比、guarded rollback 预演 PASS；CLI 改排版的字节变化与语义保持分别报告。共享 daemon PID20332 保留，未借用户 tab、切 Edge、另起匿名浏览器或下载/改写原图。既有 dirty 字节保持，私有材料仍 gitignored。

AGY 实跑 Neil 与 Nikon 两个公开教程，各实际 capture、view PNG、write 材料；两个进程之间配置字节保持。截图取景不足没有补成正面事实；第三个新观察目标补 Neil 顶部人像，同一桥接、同一 Chrome，新增一条精确0滚动命令。全部 PID/UTC/实际工具与产物见 AGY_BROWSER_REPAIR.md，本文不把成功返回当验收。

CC 桥接初始候选真实失败，定向返工一修 schema/限制，独立 Verifier 再发现普通异常假成功与最终 URL 越界。返工二修共同失败边界，原失败回归保持，ROOT63 passed/2 skipped，独立65 passed/2 skipped及额外2 passed；不做第三轮桥接修订。

研究完成后另一个真实 CC 初始内容接入实际读取原 AGY 材料、修改 Python 精确媒体登记和案例/测试；达到turn上限exit1。ROOT整合补必填case-alt、修正背景/裁切文案、生成bundle。初build missing-alt FAIL和96 passed/1 failed文案不一致保留；没有删除/修改该失败断言，最后97 passed。新增1案例与1来源，原22案例/32来源完整保留，阅读器与学习状态API未改。

实际回归：默认六文件核心123 passed/1 warning（79.49s）；四文件课程/证据/状态97 passed/1 warning（8.34s）；HTTP/Chromium有限UI回归7 passed/9 deselected/1 warning（37.62s，图片fixture合成，仅结构兼容）；build --write/--check、node两个语法检查、diff --check PASS。误写不存在test_learning_media.py的首条focused命令未执行测试，已改为实际四文件命令，不记通过。

可运行窄回归：

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_agy_browser_bridge.py tests/test_learning_gateways.py tests/test_tutorial_evidence_display.py tests/test_learning_gateways_state.py tests/test_learning_course.py
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_learning_gateways_ui.py -k 'each_gateway_full_path or original_case_photos or endpoint_requires'
.venv/Scripts/python.exe -X utf8 tools/build_photography_atlas.py --check
node --check web/learning-gateways.js
```

Skill 发现复测显式/隐式读正文、负向不读；原显式评估器假阴性和审计修正均保留。只读规划不冒充无人干预执行。未全局安装，未来域名/视频/长期无人值守、单Agent对照、主人审美和教学效果、日用服务升级、WSL以及既有CC/AGY stop hooks全面兼容未核验。

### 独立最终验收

2026-10-11 05:41:46 UTC，独立 Verifier 给出冻结 V01–V10 PASS（本次工程范围）；标准 SHA `383add69bd140165b86d60909118fc26c6c1d128d9bd031fea0ae115c5ba5f21` 保持，原失败测试保持，最终 verdict SHA `4f634f735f8738c6bdb7dedd8b98eef77a6f7679805fb2ee3c0d37efff620acb`。独立核心回归92 passed/2 skipped，真实图片补证1 passed；reader原图HTTP200/900×599，A–D及来源呈现，图片失败仍有正文，前后学习状态一致且无写请求。详细独立结论见 `docs/research/orchestration-skill-validation/VERIFIER_REPORT.md`。

本次工程要求完成。原手机异步滚动问题、符号链接特权、私人登录内部、任意网站/视频/长期无人值守、主人审美及教学成效仍未核验，不作为当前PASS范围。真实CC内容进程turn上限及ROOT补齐分开记载；没有第三轮桥接修订。报告收敛后由ROOT在原immutable transaction中seal/finish精确owned paths；发布以该实际收据为准，不从工程验收预判Git/Notion成功。

最终单独的发现测试审计复现仅标题exit0假阳性，ROOT收紧shell/MCP完整正文判断；独立14项正负断言PASS，重审现有三份events仍true/true/false，原始false/true/false保留。没有新外部运行或Verifier标准变更，机器证据在 `.local/agy-flow/discovery-{strict-final,final-review}.json`，该审计与V01–V10范围分别记录。
