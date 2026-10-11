# 规则、课程阅读与 Git 调用边界修正

## 用户意图（编辑前记录）

用户要求执行 `codex-policy-refactor-loop.md`，以 `AGENTS.core.proposed.md` 作为全局人工维护区候选，与当前实际规则合并；“不直接覆盖整份文件”。目标是修掉摄影课程审计表式写法与重复免责，按影响选择验证并复用有效证据，从实际失败命令持久修复 Git 环境。“不要新增一套 Hook、测试平台或环境包装器，不给摄影库新增 Golden Path”。

保留既有工作、事务基线、限定路径发布、managed blocks、仅 ROOT 发布、Git/Notion 独立结果。主 Agent 修根因，真实 AGY 对相关正文润色一次，独立审查者核对归属、真实页面及遗漏路径，不重做整套测试。

## 方案与边界

沿用 FastAPI / 静态阅读器 / 既有课程生成器与 canonical Publisher。源工作区 `D:/AI PROJECTS/photography-reference-lab` 有其他任务的工作文件和暂存项；从已发布课程 `e6c0eb6f7238443f5cb89ea443997b104bc8888c` 建立干净工作树，先建任务分支，再建立真实 turn 的编辑前事务。源工作区只同步本轮规则文件，不改它的课程、索引、HEAD 或分支。

改动范围：全局人工正文与两个 managed block 的适用规则；项目 AGENTS / 验证文档 / Publisher 检查配置；共享案例展示及其原有回归；动作导演 COURSE.json、MODULE.md 与生成包；简短 Git 恢复说明。详细来源审计、原始润色稿与历史发布记录保留，不修改摄影能力分类、个人状态、图片、数据库或日用服务。

## 可观察验收与所选验证

- 全局候选合并后仍保留 managed markers 与事务/路径/权限约束；无 profile 新进程核对路径、内容与配置。
- `tests/test_tutorial_evidence_display.py`：共享案例展示的归属、完整原话认证、缺失项和 XSS 边界；更新的是用户可见契约，不削弱认证。
- `tools/build_action_directing.py --check`：真实 COURSE.json 与运行包一致；`node --check web/learning-gateways.js`：改动脚本语法。
- `tests/test_action_directing_acceptance.py`：现有桌面/390px真实阅读、展开、旧课程、零写请求与学习文件字节不变；ROOT 和审查者另看实际页面与来源入口。
- 涉及共享案例函数，扩大到原课程案例展示的既有 focused UI 检查；不运行无依赖的采集/图库数据库回归。另只读追踪共享状态路径，记录会触发扩大验证的调用方。
- Publisher 项目配置取消无条件 finish 重跑；非空实际 manifest 证据与 seal 内容绑定仍是门槛。证据内容、依赖、环境未变则复用，出现相关修改才重跑。
- 用记录中的实际 Git 命令、新无 profile 进程、Publisher `git_ops.run` 的真实运行环境和本轮真实 push / 远端 SHA 检查环境边界。

## 结果

### 规则、正文和实际入口

实际 CODEX_HOME 未设置，Codex 默认读取 `C:/Users/Dell/.codex/AGENTS.md`；全局及适用祖先没有 `AGENTS.override.md`。人工正文采用附件候选的正向约定，保留两个 managed markers。Publisher managed block 的维护源 `C:/Users/Dell/.codex/local-marketplace/plugins/finish-task-publisher/global_rules.md` 与源/安装 skill 同步修改；`sync_install.py::inject_rules` 仍保留人工区。codebase-memory 只有安装的单文件程序，没有可见可编辑模板，且当前 Codex 没有对应 MCP；保留标记并将偏好限定为实际可用且适合问题时使用，不运行会删除历史索引的安装器。

源工作区的 `AGENTS.md`、`.codex/finish-task-publisher.json` 和 `docs/CODEX_REGRESSION.md` 已同步本轮规则。项目 `checks: []` 去掉无条件收尾回归；`system.validate_manifest` 和 `lifecycle.validate_completion` 仍要求非空真实证据、需求对应关系与 seal 内容绑定。新 `pwsh -NoProfile → codex debug prompt-input` 实际生成的模型输入包含更新的全局/项目规则，没有旧 `Default regression` 指令；原始输出和摘要在本工作树 `.local/policy-refactor/`。

共享 `caseEvidenceHTML` 现在连续呈现观察、有来源的作者说明、本课分析和现场试拍。缺原话不生成空栏；未核验的实际文字只留在默认折叠的来源记录，完整认证规则与转义保留。Jerry 的镜像示范和手臂间隙归回 Jerry / Westcott；Adler 段只解释她的说明和抽查画面。必要的不可见承重脚、服装限制、非单变量样本和图像权利条件保留。历史 FACTS/SOURCES/SOURCE_AUDIT 与润色记录未重写。

示例对照：旧段在案例下逐行写“实际可见”“原话认证”“解释边界”“本课迁移建议”，其中原话栏写“没有逐音核验对应现场对白。下文中文指导句是本课程设计，不是摄影师对白翻译”。新版先描述“一手在肩部附近，一手在腰侧；两肘弯曲，手臂与躯干间有局部空隙”，再解释 Jerry / Westcott 正文的方法，并给出本课试拍建议；仍说明长裙覆盖腿脚、不推断承重脚，核验信息折叠到出处。

`agy --mode plan --output-format json --print-timeout 40s --print <仅回复就绪、不调用工具的提示>` 实际探测在 55 秒进程超时内未获得模型结果；没有派发正文润色，也没有声称 AGY 完成本次。ROOT 完成润色；独立审查者沿冻结 CF-01～13 标准核对 FACTS/SOURCES、原始截图和证据输入哈希，未平行重跑测试。

实际试读入口：`http://127.0.0.1:18774/learning?course=action-directing-module`，由现有 `tools/preview_learning.py` 从本任务工作树提供。源工作区的日用服务和其他未交付工作不切换。

### 验证与复用

最终 focused 命令：`.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_tutorial_evidence_display.py tests/test_action_directing_acceptance.py tests/test_learning_gateways_ui.py::test_original_case_photos_and_source_summaries_render_inside_each_gateway --basetemp .local/policy-refactor/pytest-final --junitxml .local/policy-refactor/focused.xml`，实际 **91 passed**。覆盖共享认证/缺失项/XSS、桌面和 390px 阅读与来源、老课程案例、零写请求和学习文件字节不变。正文模板改变后旧测试先出现 8 个固定审计栏断言失败，随后 1 个畸形说明断言失败；将它们改成真实阅读与保守归属契约后通过，未削弱原话认证。

8 个实际输入哈希在独立审查及 ROOT 收尾完整性检查时与当前内容一致，复用此证据。没有执行与本次无依赖的图库、采集、导入或全套数据库回归。`tools/build_action_directing.py --check` 实际 PASS（digest `822f97f1b7e058bbd2f66fe8fae010e6ea13f1e624667b4a079daa0222938e7f`）；`node --check web/learning-gateways.js` 和 `git diff --check` 实际退出 0。

共享状态的只读影响分析：`web/learning-gateways.js` 保存 stage/answers/revealed/last_section 时携带 `expected_revision`；`ref_lab/learning_state.py::put_skill`、`put_gateway` 以及日志/照片写入共用同一文件、全局 revision 和 `state_lock`。`_expected` 检查冲突，`_write_state` 通过临时文件 `os.replace` 原子替换。如果修改这些边界，应扩大到 `tests/test_learning_state.py`、`tests/test_learning_gateways_state.py` 以及过期技能/草稿冲突 UI 路径，而不能只验证阅读器。本轮没有修改或写入这条数据路径。

### Git 持久修复与发布边界

保留本轮真实失败记录：Publisher 新进程的 `ls-remote` 返回 128 / connection reset。用户纠正代理为当前桌面 iKuuu 后，核对系统代理 `127.0.0.1:12002` 与 Core 真实 loopback listener；临时 GitHub 专用配置测试成功，才持久写入 `C:/Users/Dell/.gitconfig` 的 `http.https://github.com.proxy`。新无 profile PowerShell 和新 Publisher Python（实际 `git_ops.run`，没有临时 `-c` 或代理环境变量）均读取该配置并成功查询真实 SHA。Clash 没有被写入 Git 配置；没有新增 Hook、平台、环境包装器、开机项或网络改造。恢复说明见 `docs/GIT_ENVIRONMENT.md`。

任务分支 `codex/policy-course-git-refactor-20261011`，编辑前 baseline 在 canonical transaction `d6a9cbd39dab705f75a3a63c577d4d83`；只由 ROOT seal/finish 具体拥有路径。最终 commit、远端 SHA 与 Notion 分别以该 transaction receipt 为准；不能由预检成功推断发布成功。ROOT 收尾前与编辑前 snapshot 实际比较通过：源 HEAD `fc6290cc4978529fdd9f58ed6cea02bab736de8a` 和 index fingerprint 未变；只有已声明的三份源规则文件改变，其内容与本工作树一致，其余文件完整保留。managed block 与维护模板完全匹配，源/安装 skill 匹配，项目发布配置只改变 checks，Git 全局配置只新增 GitHub 专用代理键。

独立审查者补审确认共享状态扩大条件、真实失败归因、iKuuu listener、GitHub 专用持久配置、新进程远端读取和源工作区保全检查通过；没有重跑全套。ROOT 用现有 `validate_manifest` 验证候选接受，并实际确认空 verification 被拒绝。限定发布预检确认 11 个精确路径、原 index 未改、原 Git/Notion 授权与目标保留、automatic checks 为 0；真正 push / 远端 SHA 与 Notion 仍由随后 canonical receipt 记录。
