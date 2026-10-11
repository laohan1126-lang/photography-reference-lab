# 独立 Verifier 验收报告

日期：2026-10-11。最终结论：**PASS，冻结 F01-F13 的最小单案例范围，2/2 定向返工已审**。此结论不覆盖 ROOT 另一路手机滚动回归失败；项目整体仍 PARTIALLY VERIFIED。

## 独立性与标准

新 Codex reviewer 子代理使用 fresh context，没有继承 ROOT 对话。在 `codex/orchestration-verifier-20261011` 独立 worktree 只收到目标、约束、既有产品、候选文件和原始来源材料；未读 AGY/CC 提示词、进程日志、自评或实现方案。Verifier 只改自己的测试夹具和报告，没有修产品、发布或写主人数据。

实现前冻结 13 项行为标准与原 22 案例/32 来源投影；最终原 SHA256 保持 `85c5edf9a3bae453302ac790ec33e64771ea7f2d405c6cff45da9e247ad2e495`。候选到达后仅绑定真实字段与 DOM 选择器，没有降低断言、替换内容或删失败测试。完整独立原记录保存在 gitignored `.local/orchestration-verifier/.local/verifier-report.md`，最终哈希 `5a806a6b84b50d74dd1302dcfaef80a33211e1857ddbef9401e792e5ae10b153`；私有夹具不是默认 CI 依赖。

| 标准 | 最终实际证据 |
| --- | --- |
| F01 专业真实来源 | 独立读取 [Nikon 教程原页](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/composing-photographs)，标题/作者 Diane Berkenfeld 对应 |
| F02 实际画面 | 实开交付截图及真实加载照片，A 限定可见像素，不推 EXIF/因果 |
| F03 原话与转述 | 七词 B 片段精确对应第一组前图图注，语言/日期/来源/定位齐全；旧摘要保留中文转述身份 |
| F04 定位/时间 | 网页图注定位可复查；未选视频，时间码 N/A，未冒充看视频 |
| F05 专业解释 | C 明确项目分析，来源依据和未知因果边界可读 |
| F06 项目建议 | D 是条件性漫展迁移建议，不是作者原话或主人接受 |
| F07 四层显示 | 实际 HTTP Chromium 1440×1000 与 390×844 可读 A-D，无横向溢出 |
| F08 旧内容兼容 | 22 cases / 32 sources 投影与能力树/来源映射/教程目录哈希保持，旧案例显示/保存回归通过 |
| F09 人工写状态 | 阅读、导航、解析、关闭重开、刷新无写请求，saved state/revision 完整相等；原显式 save/迟到/冲突通过 |
| F10 恶意输入 | 真实浏览器合成负例无攻击 DOM、脚本执行或非法 href；只证明安全边界 |
| F11 坏证据 | malformed/missing-text/unsafe-both 等真实回归，最终拒绝或未核验，不崩溃/假核验 |
| F12 媒体失败/真实加载 | 人为中断图片仍保留栏目/定位；另行真实媒体请求 HTTP 200、natural 650×981、错误提示隐藏 |
| F13 验收归属 | 工程/来源证据与审美、教学成效及发布分开报告 |

## 真实失败和定向返工

| 阶段 | 实际结果 | 处理 |
| --- | --- | --- |
| 基线准备 | 缺 CSRF 的 Verifier 夹具失败，修正后 5 passed / 3 candidate deselected | 测试接线，不当作产品问题或 CC 返工 |
| 初始候选 | helper 未接主 validator；verification 数组/对象 3 项 TypeError；研究/UI 缺成果 | REVISE 归实现；缺源材料 BLOCKED，0/2 |
| 返工一 | 主 validator 接入与类型守卫已实证修复；全套 16 passed / 4 failed | REVISE，1/2 |
| 四项失败 | 空文本仍 verified；两个非法 URL 清空后错误匹配；两个视口缺 A-D 标记 | 前两为真实 F11 缺陷，后两为低优先的冻结显示不匹配 |
| 最后候选 | 原四项失败复现全部 PASS，全套 20 passed | PASS，2/2；标准哈希未变 |

第一次返工合成 subset 为 10 passed / 2 failed；独立旧显式 save/late-save/conflict 为 5 passed。曾有 Verifier 夹具缩进导致 collection syntax error，纠正后实际执行，未归责产品。

## 最终实际命令

工作目录为独立 worktree，使用根项目既有 Python；无安装依赖。

```powershell
D:/AI PROJECTS/photography-reference-lab/.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_tutorial_evidence_verifier.py --basetemp=.local/verifier-final-all
```

**20 passed，80.80s**。另加 `-q -s ... -k real_sample_live --basetemp=.local/verifier-final-live-media` 的独立真实媒体检查 **2 passed，15.45s**；`tests/test_learning_gateways_ui.py tests/test_learning_course_ui.py -k 'each_gateway_full_path or late_save or conflict or course_direct' --basetemp=.local/verifier-final-legacy` 为 **7 passed / 12 deselected，52.84s**。这些计数不能相加冒充全仓测试数量。

build --check、node --check reader、git diff --check PASS，研究版本 `818fd303907c5921f0f791b0efcb83d832b0c33d7bf12a48e9cec65c5cb8c436`。Pytest 一项既有 Starlette/httpx dependency warning。

最终核对产品 SHA256：

| 文件 | SHA256 |
| --- | --- |
| web/learning-gateways.js | a7bfd97016da568fd0b98755c8ae8b065225668542c30897364c942c68d007cc |
| web/learning-gateways.css | 5ac593550abec7dc3122f2f97bd2fb5d37137cbb29705a88f250ba9d999fad8c |
| tools/validate_learning_gateways.py | dc0d3273cc07d4d8621019f1347a9510cb678749be8c6892f38cb46594dfee77 |
| GATEWAYS.json | a907a4524f6cfe470a54410da4e63359af31567a49abc1110f110f44aef06cfa |
| web/learning-atlas.json | 6590254fc4bc23f55b2c78c09029755618b1fcd3a0eb9e53f4460290312a85b1 |

两视口均实际从注册的原 CDN URL 取得 HTTP 200 图片，natural 650×981，无 requestfailed/pageerror；实开源像素和 reader 截图后核对 A-D、来源和定位。来源 copyright/review 未被提升，截图不等于相机原始字节或 EXIF。

## 结论边界

独立 PASS 只证明上述冻结范围；不能覆盖 ROOT 的旧手机关闭重开 scrollTop 失败，不以另一套绿灯抹掉失败记录。AGY 自主浏览权限问题、用户审美/教学成效/实拍提升、未来外站可用性、离线再分发授权、日用服务升级、WSL/CI 与 Git/Notion 发布均不是此 Verifier 的已证结论。

ROOT 后续只读受控对照（不是修改本 Verifier）：新候选与未修改 `805c289` 均在图片从 0 高度加载后产生约 517 像素 scroll anchoring；close/reopen 均正确保存并恢复变化后的 top。既有图片占位/旧测试采样竞态仍待另项修复，完整 ROOT suite 仍记录 114 PASS / 1 FAIL，不改为全绿。对照原记录在 `.local/orchestration-validation/scroll-controlled-probe/events.json`。

原失败没有加载事件记录，不能精确断言其变化发生于关闭前或重开后；不能将受控探针成功写成原断言 PASS。
