# Astra复验：R1—R7限定收口

日期：2026-10-24。基线：`1568e9634f6067d866618ecbfd764b7ba88b3dda`。
状态：技术验收PASS；Git交付以本事务回执及`.local/a2/final-delivery.json`为准。分支：`codex/astra-r1r7-final-20261024`。

## 用户授权与边界

用户要求：“你审查一下吧，然后如果还有没做到的，你就派一个6.1sol子代理去做吧”。沿用本轮R1—R7范围，禁止扩大功能、联网搜图、真实图片模型调用及两轮30张。ROOT独立复验、集成和发布；一个GPT-6.1 Sol子代理执行限定修复。

编辑前Publisher事务：`01a16df8-7185-7f11-b6a6-74aedd5fac0c`；先建任务分支再start/contract。实际项目配置Git-only，不写Notion。

## 独立发现与验收标准

- R1运行版本已独立确认1568e963/b75146d4，日用数据目录正确。
- 已复跑67项针对性检查：首次62通过/5个cp950解码失败；按项目UTF-8约定重跑5项全部通过，属于测试环境而非业务修复。
- R2仍不完整：真实隔离HTTP `/search/continue` 对旧Goal返回409，却已经提交目标/预算/恢复代数和事件；加搜还改写source/run goal.json。证据`.local/a2/continue-repro.json`。
- R7性能脚本仍遍历整个.local并删除现有项目缓存测冷启动，未证明对照历史集合为固定真实图片且不污染日用缓存；F脚本只有空候选的artifacts准备。需用受控数据和非空真实入口补足证据。

冻结验收：
1. 旧/损坏/跨项目Goal在任何续跑和阶段准备写入之前被拒绝；数据库表、原Goal/baseline/回执字节均不变；有效绑定Goal保持加搜和补足功能。
2. R3—R6关键边界及同项目排重/跨项目复用保持，不改阈值。
3. 同一真实候选SHA、固定可追溯历史集合、独立冷/暖缓存的性能结果；非空隔离HTTP恢复；旧成果可按历史规则查看。不遍历杂乱.local或改日用缓存。
4. 相关回归通过；旧原件、人工选择和历史证据保护；最终日用版本一致与任务分支远端SHA核验。

## 实现简报与归属

现有栈FastAPI/SQLite/Python。复用goal_baseline与服务事务边界；应在extend_search/replenish_search及stage artifact准备发生副作用前验证，不追加一套任务系统。
Sol工作树：`.local/worktrees/astra-r1r7-final-20261024/sol`。允许编辑共享预检相关service/collection_stages/collection_history/api及直接相关测试；ROOT负责本任务记录与CURRENT。所有证据放.local，子代理不提交、不发布、不修改日用数据或服务。

## 检查点

- ROOT完成初审和失败复现；父事务与合同已建立，等待Sol限定补丁和补足验收证据。原R1—R7交付记录保留，不覆盖其原始结论。
- 已派唯一子代理Sagan（`01a16dff-fa05-7673-a237-2bb247395007`），原生session证据provider=openai、model=gpt-6.1-sol、effort=high；使用可写default角色和隔离工作树。ROOT并行实测R3两张均覆盖、新项目范围/缓存均0；旧35/33成果页HTTP200且按历史规则展示。
- R4补充同一完整性边界反例：refs.data损坏JSON被静默continue，导致有有效引用和完整原件的项目返回空范围；已交同一Sol限定修复。证据`.local/a2/root-scope-audit.json`。

## 最终实现与独立复验

- Sol仅修改`service.py`、`collection_stages.py`、`collection_history.py`及新增`test_goal_continue_preflight.py`。共享只读预检在extend/replenish和artifact准备发生任何副作用前校验源/运行Goal、项目与版本绑定、基线SHA和目标；旧或损坏状态明确409，合法续跑能力保留。损坏/非对象引用JSON及无效SHA改为完整性阻断。
- 实际模型全程为openai/gpt-6.1-sol/high；一次平台capacity错误后仅恢复同一代理一次，没有换模型。最终补丁SHA逐项核对后由ROOT集成，见`.local/a2/integration.json`。
- Sol修前回归34失败/6通过；修后相关组67、92、51通过，不能把重叠用例简单相加。最终新增测试曾有一次任务包临时目录替换WinError5，单项重试通过；首次R7脚本Path序列化失败及日志保留。精确命令、环境、各文件哈希见工作树`.local/handoff.json`。
- ROOT在集成后的正式任务分支独立运行：`.venv/Scripts/python.exe -B -X utf8 -m pytest -q --tb=short -p no:cacheprovider --basetemp=.local/a2final tests/test_goal_continue_preflight.py --junitxml=.local/a2/root-tests.xml`，42 passed。`git diff --check`通过。新测试覆盖HTTP与直接服务/阶段入口、数据库所有表和文件/目录不变、合法非空目标恢复及非法引用元数据。
- 受控R7证据`.local/s7-tufnkrmi/`：固定4份现存真实原件，项目范围2份，ROOT核对清单、源/快照/候选SHA全部一致；旧/新、冷/暖各3次独立进程测量。同项目转码候选仍拒绝，跨项目同字节成为复用。冷缓存准备中位数0.638/0.419秒，暖缓存0.229/0.231秒，仅代表4/2样本；不外推全库倍率。旧缓存与日用项目缓存不参与测量。
- 真实loopback TCP/Uvicorn非空恢复：已有1份原件/received/receipt在重新创建应用后，经补足和加搜均HTTP200并保留字节与计数；6个无效Goal请求均HTTP409且数据库所有表和相关文件不变。浏览器/图片模型仅为明确的离线适配器边界，未联网采集，不能作为真实平台端到端证据。
- ROOT再次确认旧35/33成果页HTTP200并保持历史规则说明；新项目视觉范围及缓存条目均0，南小鸟遗漏的2张已覆盖。真实库21张表内容指纹、两轮18个关键文件均保持不变，见`.local/a2/prepublication-acceptance.json`。
- 正常启动器重启前核实无活跃采集/审核进程（旧b807/45448为死亡PID）；48444→37108，修复实施摘要`58877c3b…`与正式工作树一致，数据目录正确。提交后只需正常启动器再次同步提交标签并记录`final-delivery.json`，不重跑无关回归。

## 交付边界

仅ROOT按已建立事务发布任务分支；项目实际`delivery.notion=false`，本轮不写Notion。不合并main、不清理历史、不新增搜图或图片审核模型调用、不跑两轮30张。真实平台联网采集及全库性能仍UNVERIFIED；本轮限定修复已通过本地验收。
