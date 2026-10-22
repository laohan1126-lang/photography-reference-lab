# 一键两轮最终核对：未通过，资源边界停止

## 结论

**NOT PASSED。** 同一冻结实现的两轮正常网页单次启动，按当前规则分别准入34、31张，正常停止/冷启动后保持。但最终新增反例证明C项仍存在普通横图裁成竖幅时的漏重，不能把这些数量及FP3范围内的无匹配报告当作完整Goal通过。

4个正式Job额度和1个诊断Job额度已全部使用。本次保留冻结实现、所有成果、失败、模型流、备份与人工决定，不新增任务、不加预算、不修改完成状态。后续若改排重实现，必须重新取得同一新版本完整两轮；本轮证据不能冒充修改后已通过。

## 正常网页实跑与时间

冻结实现：`83f7790893d2e33fbbac1eaeca80a3fb90d7035a`，digest `d5d5b402ed76f4b3a4daea8d6184aeb831bbc495e2d2cf60fbb6b35bf5146ca4`。两轮源码全部文件SHA及运行配置SHA相同。角色西木野真姬、search、目标30、其它表单字段空；2700秒/60次模型尝试/worker1/候选90/检索词24/详情96/单帖12，FP3、拼图3。冻结清单：`.local/one-click-audit-20261022/frozen-final-v4.json`。

| 项目 | 第一轮 formal3 | 第二轮 formal4 |
| --- | --- | --- |
| Job | `8f89d5eed46a4d03a190420a06413c84` | `76a41a7aeb7b42caa16e6c5f2786a242` |
| 日本时间开始 | 2026-10-22 14:39:22.892 | 2026-10-22 15:23:32.783 |
| 当前规则准入 | 34，均为原件 | 31，含2张有效子图 |
| 收到原件 | 44 | 39 |
| 冻结历史指纹 | 1602 | 1653，含前轮全部44原件+6有效子图 |
| 首个原件落盘，距点击 | 234.186秒 | 286.199秒 |
| 首张准入首次API观察 | 387.848秒 | 335.779秒 |
| 首张准入首次浏览器解码观察 | 430.679秒 | 368.982秒 |
| 第30张首次API观察 | 2014.370秒 | 2554.217秒 |
| 首次浏览器解码至少30张 | 2059.575秒 | 2569.843秒 |
| 首张合格照片正式Reference创建 | 2139.911秒 | 2573.932秒 |
| 最后一条本轮Reference入库 | 2153.218秒 | 2583.392秒 |
| 自动停止原因 | target_reached | detail_budget_exhausted；收尾准入已达31 |
| 正常应用attempt_started | 1 | 1 |
| 继续/加搜/补预算事件 | 0 | 0 |
| 真实模型尝试/成功/失败 | 45/44/1 | 37/37/0 |
| 已知Token/未知用量次数 | 1,606,652 / 0 | 1,309,090 / 0 |
| 模型调用wall合计 | 1724.829秒 | 1351.840秒 |

API每约15秒、浏览器第一轮约60秒/第二轮约120秒采样。表中明确写首次观察的时间，不反推精确准入/可见时刻；模型wall包含工具与等待，不称纯推理时间。Search路径没有单独attempt_finished事件，完整时间线保留search_stage及最后Reference导入事件，不伪造结束事件。泛用job.status为blocked/review idle，search_state=completed、collection_outcome=complete；没有声称独立身份Review或人工现场卡验收完成。

## 证据及其实际范围

- 逐张清单（SHA、原件、正式库文件、来源页/图片URL、名称元数据、Reference、原生读图回执、画质及历史关系）：`formal3-technical-audit.json`、`formal4-technical-audit.json`，均在`.local/one-click-audit-20261022/`。两轮合计82次尝试、81成功/1失败、2,915,742已知Token、0未知，原始流分别保存在各Job/current/type-evidence。首轮失败的37,332Token及首失败流未覆盖。
- 两轮SHA交集为空；FP3范围内轮内及对完整基线均未返回重复/待核关系。第二轮完整基线包含第一轮全部准入项，见`cross-round-duplicate-check.json`与两个baseline-coverage文件。**因下述裁切反例，这不构成所有合理裁切都已排除的证明。**
- ROOT逐个实际打开全部65张当前准入图片/子图，观察记在两个root-visual-complete文件。包含普通场照、合照、休闲造型及首轮1张试妆阶段，未冒称全为完整造型正片；没有从项目名称推断严格角色身份，也没有代替用户作审美接受。
- 两轮自动运行的完整应用事件及里程碑：`formal3-timeline-complete.json`、`formal4-timeline-complete.json`；ROOT每次表单动作均有独立run-control时间回执。没有CLI补采集、手动导入、写数据库/Goal计数或补完成状态。
- 首轮浏览器原始导出保留200请求、0丢请求，操作上限64淘汰13旧操作；第二轮结束后观察会话已注销，debug stop/export均not_found，原始录制未能导出。逐次动作、应用事件、模型流、15秒观察与31/31解码日志保留。此处不宣称完整浏览器原流已保存。

## C项仍失败的反例

源为第一轮真实横图`63daa0e7…`（1619×1080）。中心保留40%宽、100%高，框`[485,0,1133,1080]`，按原比例缩放并JPEG重编码，生成正常竖幅人像。原件SHA未变，ROOT已实际打开裁切结果。以原图构建ImageHistory后，`history.match(variant)`返回None。

根因：`ref_lab/collection_history.py::_photo_relation`只搜索16像素缩略图中宽10–16的窗口，且细拟合宽/高都必须>=0.60；较窄裁切直接跳过，却以None清除重复关系。没有改产品阈值来掩盖这次失败。

- 真实图片反例：`.local/one-click-audit-20261022/final-crop-boundary-counterexample.json`，衍生测试图在`.local/test-final-crop-boundary/`，未导入、未计数，按test目录规则不进入正式历史。
- 已在既有公开合成回归中加入`(240,0,560,600)`裁切。实际命令：`.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_one_click_audit_regressions.py::test_history_excludes_reencoded_crops_but_preserves_other_frames --basetemp=.local/test-final-crop-regression --junitxml=.local/one-click-audit-20261022/final-crop-regression.xml`。
- 结果：**3 passed / 1 failed**，新增box3在第148行`assert history.match(cropped)`失败，日志/XML完整保留。这是未修复缺陷的检查点，不能说测试全绿或A–H全部闭环。

## A–H及相邻路径

| 项 | 本轮结果 | 对应检查 |
| --- | --- | --- |
| A 预算与自动收尾 | 定向回归及两轮单次实跑通过；不是所有外部故障的普遍保证 | total budget / command timeout区分、过期禁止恢复/改写、单帖12共享截止、完整时序 |
| B 正常启动器 | 通过 | Windows生命周期用例；正常terminate/launch创建受管服务及记录；宿主退出后仍健康 |
| C 完整历史与裁切 | **未通过** | 完整指纹基线/损坏阻断/旧批次/并发/已测轻裁切通过；最终窄裁切真实及合成反例失败 |
| D Goal唯一性 | 回归通过 | 同项目同秒不同目标，UUID且目录禁止覆盖 |
| E 加搜一致性 | 回归通过 | 40+70拒绝不写；首/次文件写失败回滚DB及文件；任务包同步 |
| F 模型尝试记账 | 回归及真实失败记录通过 | limit1禁止第二调用、每次原流/耗时/用量保留、坏账本阻断、完整回执复用 |
| G 关闭身份 | 回归通过；本两轮自动closed | 失败保留原session/cleanup_pending，后续针对原session清理；失效恢复保留 |
| H 旧拼图升级 | 回归及旧真实图重算通过 | 版本3，v2快照后显式重算，旧原件/子图/人工决定保留 |

此前已有且内容未变的证据按影响复用：freezechecks305通过，后续85/86/77/4通过，单帖截止相关115通过，来源AI警示相关99及83通过。较早完整suite为1163通过/3失败/6跳过，3项后经对应调用方修正/复测；不把这一历史整套结果说成最终全部通过。最终新增裁切回归明确仍1失败。

## 正常重启与数据保护

- 最终官方备份1531资产，隔离恢复doctor无缺失/损坏，72既有外键错误一致。ZIP `.local/backups/backup-20261022-final-two.zip`，SHA `5d2c4f937a39da2a7a4d7d43d2a0aa6c7a0aefafaac08aa242860d959057e312`。
- 正常terminate停止46768；独立命令确认旧PID、health、server.json均不存在；正常launch自行冷启动11976并生成运行记录，未手动serve或手写记录。服务/adapter同日用checkout、83f7790及冻结digest。
- `final-before-restart.json`与`final-after-restart.json`比较189关键文件（含原件/来源/基线/原生流等）、91本轮引用、所有相关任务/表计数完全相同；34、31保持，无新采集或重复导入。原始1124条Reference（含人工决定/state/data）逐行保持。
- 重启后正常网页再次实际解码34/34、31/31，见`final-browser-decoding.json`。1531资产/1291引用保持。验证正常运行生命周期不等于本Goal通过C。

## 修改、交付与回退边界

工程修复已在`codex/one-click-audit-20261022`推送至83f7790，接续时ls-remote实查一致；日用验收分支`codex/one-click-runtime-v4-20261022`。本次接续额外修改仅任务记录/本报告/CURRENT及一个已知失败裁切回归；产品实现保持冻结版本。

修复范围：service/agent_collection/collection_stages、collection_history/counts/checkpoint、photo_types/classification/search_relevance/collage、collect_verified/exact_recall、api/web/app.js及Windows配置/启动脚本；相关测试与旧报告更正随工程提交保留。start.bat、stop.bat、terminate.ps1只检查/调用，未重写。本次未改main、全局代理/凭据、BrowserSkill配置或人工K/I/M/X。

本Goal不满足COMPLETED条件，因此Publisher不伪造seal/finish成功，保存有证据的DEFERRED事务；Git仅发布明确标注未完成的任务分支检查点，实际SHA/远端以最后回执为准。当前Windows事务基线来自接续前aa3c904，不能追认此前0ce起始编辑；切日用任务分支后与其原branch/HEAD不一致，未重造基线。Notion按项目`delivery.notion=false`不写入。

旧两轮36/31使用人工继续及追加900秒、累计2700秒，旧冷启动声明不成立，已在旧任务追加撤销；旧模型原流重建为46（旧账本44）/39次，已知Token1,275,605（3未知）/1,203,564（0未知）。本轮结果不倒写为旧轮通过。

停止原因是原先冻结的4正式+1诊断实跑额度已用完，同时C仍有确证缺陷；不是登录/验证码或模型不可用。继续完整Goal需要新的实跑资源授权，且必须先修C、保留连拍反例，再取得新版本两轮证据。这里不将这些未完成工作标成已实现。

回退不得恢复旧数据库覆盖本轮新增数据。当前服务可继续读取已有成果；已知裁切漏重未解决，不能把后续同图变体的“clear”当可靠新增证明。若以后切换代码，先正常stop并官方备份，在隔离恢复库验证兼容，再正常启动；本次未执行回退。
