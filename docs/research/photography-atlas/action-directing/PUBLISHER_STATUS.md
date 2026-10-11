# ROOT 发布阻塞记录

课程工程/来源/协作的独立终验通过；**本轮正式发布未完成**。这是 ROOT 的 Publisher 事务初始化顺序错误，不是用户缺少推送授权，也不改变独立课程验收结论。

事务在首次文件编辑前建立并冻结原始 baseline，但当时仍在 `codex/evidence-photography-atlas`；ROOT 随后才建立/切换本轮要求的 `codex/action-directing-module-pilot-20261011`。canonical `core/lifecycle.py::validate_workspace` 要求当前分支等于事务已绑定分支；实际 seal 返回 `WORKSPACE_BRANCH_CHANGED`（CLI exit2）。没有 sealed manifest、commit或push意图，也没有 Notion 写入。

现有 recover 同样验证分支，bind-existing 只处理已有 Git SUCCESS 的终结事务，均不能迁移这项未完成事务。不得修改 state/baseline、重采已经编辑后的基线、把新用户 turn 绑定到旧事务、临时冒用原分支发布或绕过 Publisher。ROOT 没有尝试这些操作，也没有重复提交。

经用户明确授权，其他任务六项暂存内容曾临时保留/移出；两个尝试都在 finally 恢复。第二次核对：全部原 staged blob/mode/stage 及 cached raw 完全相同，项目工作文件哈希完全相同，HEAD 仍 `fc6290cc4978529fdd9f58ed6cea02bab736de8a`。第一次停在保护脚本误将 tracked-missing 元数据作为文件变化的预检；根因及有边界恢复记录在任务文档。原备份和两次恢复证据保留在 ignored `.local/action-directing/`，没有覆盖原备份。

状态：Git **未提交/未推送**，新 commit SHA 无；Notion **未执行、待处理**。当前目标任务分支保留全部本课程工作文件；不把原 HEAD 当作本轮交付 commit。canonical defer 的实际结果另保存在本事务收据中。真人试学入口仍为 <http://127.0.0.1:18772/learning?course=action-directing-module>，重启说明见 ROOT_INTEGRATION.md。

canonical `defer --blocker <实际分支错误证据>` 已执行成功，保存的真实收据为 `receipt_status=DEFERRED`、`completion_status=BLOCKED`、Git `PENDING` / commit_sha null、Notion `PENDING`。没有重新创建事务或改写 baseline。收据副本为 `.local/action-directing/publisher-deferred-receipt.json`；完整 canonical receipt 仍在原事务目录。最终复查实际入口 HTTP200，附加包恰好一门课程；原六项 cached name-status 与重命名比例再次核对相同，`git diff --check` 无错误。

补充外部验证边界：末次 `git ls-remote origin refs/heads/codex/action-directing-module-pilot-20261011` 长时间无输出，ROOT 只终止已确认属于该查询的两个 Git 进程；没有得到当前远端 SHA，不能将其空输出称作“远端不存在”或“SHA匹配”。先前基线查询与本轮末次查询分开记录。seal 未成功，因此 canonical finish 的配置检查/提交/推送/Notion阶段未执行；报告中的已通过回归是 ROOT/Verifier 的真实独立运行，不冒称 finish 已通过。


## 新工作树恢复验证与封存前状态（2026-10-11）

本次仅恢复正式交付；旧失败历史及来源/Agent/润色/独立验收证据原样保留，不声称重新执行 AGY/CC 或重新观看来源。新事务位于正确的任务分支，并在首次复制前建立。

- 41 项复制时全部逐字节相同；除任务文档和本发布报告仅追加记录外，其余39项保持源SHA256。冻结标准 SHA `a762419dfd97e1754b6a10a84dc7ff095d6c976c4a33b2f751498e4e0a2aacfe`、独立阅读测试 SHA `a347c4c3e52198741dc274bac2c3b1d018661bb5798774f52593e016ffc5a625` 均未变。独立只读审计确认精确delta为41项，16个既有skill引用齐全，无需源仓库其他dirty依赖。
- 当前实际回归：默认六文件最终 `123 passed`（79.99s）；`test_action_directing.py`、`test_action_directing_acceptance.py`、`test_learning_course.py`、`test_learning_course_ui.py` 共 `25 passed`（91.02s）；`test_learning_state.py`、`test_learning_ui.py`、`test_learning_gateways_state.py`、`test_learning_gateways_ui.py` 共 `43 passed`（174.52s）。三组最终191项通过，XML/完整命令/日志存于 ignored `.local/action-directing-upload/`。
- 首次并行默认回归真实 `122 passed / 1 failed`，失败为 `test_real_process_is_stopped_on_cancel` 期望 `attempt_superseded`、实际 `adapter_or_result_error`。隔离DB收据记录 `PermissionError`；该路径代码与测试均为HEAD原样，异常具体发生位置未证实，不称已修复或直接认定为flaky。所有并行UI结束后该例独跑 `1 passed`（2.94s），再串行复跑完整默认六文件得到上述123通过；首次失败XML/log保留。已有9月30日、10月5日Windows取消风险历史已复核。
- 三项 `node --check web/learning.js`、`web/learning-gateways.js`、`web/app.js` 通过；`tools/build_action_directing.py --check` 与 `tools/build_photography_atlas.py --check` 通过，基础地图14/71/247保持；`git diff --check` 通过。import路径实测为本新工作树。现有D盘venv以ignored junction复用，没有安装软件或新依赖。
- 新桌面1440px/手机390px实际阅读回归通过：八节、三折叠问题、无填写/保存控件，旧课程可读，阅读期间零写请求及已有学习文件字节不变，过期写409、课程写404仍有效；图片主动中断只验证失败回退，不能作为来源图像准确性证明。ROOT另查看本次390px截图；不计为用户审美验收。
- 源仓库1493个tracked/untracked文件hash、HEAD、branch、index与cached raw/status哈希在复制前后及测试后均一致；源staged内容不操作。日用18765服务/数据及原18772预览不重启、不改动。
- 默认 `git ls-remote` 本次20秒超时，结果未知，失败checkpoint保留。采用现有授权 `gh auth git-credential` 仅对子进程的Git配置后，查询1.26秒exit0，上传分支无ref；与明确gh API HTTP404相符。不会改全局认证设置或绕过Publisher push guard。Notion保持有效配置指定的数据源与HKCU用户环境凭据，不选择其他目标。
- 本次先review旧 `DEFERRED/BLOCKED` 原事务（无manifest/commit/push/Notion），保留其fingerprint及收据，不改绑/重采。清洁工作树使本轮无需暂存区保护脚本或临时unstage。未修改Publisher/Skill/Hook/权限/provider，未增加业务返工。
- 封存前实际状态：Git/Notion尚未执行；将在相同事务canonical seal/finish中提交精确41项并运行配置mandatory checks。此报告此后不修改，以saved receipt和额外实时commit/远端SHA核验为最终外部结果。真实收据路径：`C:/Users/Dell/.codex/task-finalization-data/tasks/6a2d6ed857c942e5509d45322f6a9946/receipt.json`。
- 未验证：真人学习、审美、实拍迁移；Windows首次PermissionError精确异常来源；旧Hook的实时兼容及WSL。未部署、未合并main。

重复验证：先确保 `.local/verifier` 存在，再运行 `.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py`；课程/状态/UI按上列文件复跑。原试读入口仍为 `http://127.0.0.1:18772/learning?course=action-directing-module`；本次未重启或改动此服务。


## 42项恢复的本工作树验证与封存前状态（2026-10-11）

本段是新ROOT的实际恢复结果，完整保留此前两次发布失败及课程历史，不将旧报告中的191项当作本次执行。源cf7c的41项全部匹配旧sealed manifest expected_hashes；独立只读审计确认39固定项同时与原D盘字节相同，两报告只保留完整源prefix后追加。新增 `.gitattributes` 精确两行，SHA256 `4881d784a0f455dc0054db330fde570e44777c24367877b027e933917d943550`；55条单空格均在真实unified diff hunk中，无其他尾空白，原diff SHA `d73066a2d9650edd0673808c018255b7f12777adc7c0306c2c4469fb46229efd` 不变。规则仅匹配该证据文件的blank-at-eol，其余路径属性为unspecified；该文件以后所有行尾空白也受该语义规则，不能宣称只豁免55个行号。官方依据：https://git-scm.com/docs/gitattributes#_checking_whitespace_errors 。

- 本树串行默认六文件：123 passed（pytest XML 59.643s）；新课程/冻结桌面手机验收/旧课程四文件：25 passed（103.458s）；学习state/UI/gateway四文件：43 passed（154.220s）。合计191 passed，本次无失败/跳过；三个node语法检查、两个构建器--check与tracked diff --check通过。原cf7c首次并行122pass/1fail的取消PermissionError历史仍保留，未定位或修复根因。
- 当前真实命令/PID/UTC开始结束/退出码、JUnit/XML和日志在ignored `.local/action-directing-upload/` 的default、course、state-ui及static result文件中；运行import来自本8f1b树，ignored .venv junction复用现有D盘环境，没有安装依赖。
- 实际1440px与390px只读验收：八节、三折叠问题、无填写/保存控件，旧课程及原笔记保留；阅读写请求0、页面错误0、隔离学习状态字节不变，过期写409/课程写404。ROOT已查看本次390px展开截图；中断媒体只证明失败回退，不证明图片事实或本人学习效果。
- frozen标准JSON SHA `a762419dfd97e1754b6a10a84dc7ff095d6c976c4a33b2f751498e4e0a2aacfe` 与test SHA `a347c4c3e52198741dc274bac2c3b1d018661bb5798774f52593e016ffc5a625` 未变；没有第三轮业务修复。
- 本轮source 1465项文件hash、HEAD/branch/index/cached raw/status及两旧事务baseline/state/manifest/receipt与Publisher/core/config hash前后相同。日用18765与原18772未改动/重启。历史failure-checkpoint的index hash与本轮起点不同；本轮起点与当前源index同为 `f8bc37946110f40e2861d3674e53f5c74421056096983c76572e71b8b715a742`，不以跨历史元数据差异推定本次写入。
- 当前process-only gh credential helper的实时ls-remote exit0，用时1.55s，授权上传分支无ref；旧默认GCM超时历史不抹除。有效Notion仍为既有verified data_source与Windows HKCU用户环境凭据，目标/配置不改动。
- 独立只读no-index空白对照：源exit3/55条错误，目标exit1/0条错误；exit1只是内容差异。完整42项尚将在本ROOT自己的标准index进行精确stage/check/blob dry-run，并只unstage本42项、保持工作字节；标准canonical finish仍自行执行全部配置mandatory checks与空白guard。
- 封存前Git/Notion尚未执行；本报告封存后不再追加外部结果。当前新事务目录 `C:/Users/Dell/.codex/task-finalization-data/tasks/bae650ad053038acb6d57c1464486db6`，savedreceipt `C:/Users/Dell/.codex/task-finalization-data/tasks/bae650ad053038acb6d57c1464486db6/receipt.json` 与ignored后验检查将给出实际commit/push/远端SHA和Notion身份/内容读回结果，分别报告；不预称发布成功。
- 验收状态PARTIALLY_VERIFIED：真人学习、审美/实拍迁移、旧Hook实时兼容、WSL、旧PermissionError具体异常点未验证。本次无新的AGY/CC或来源视觉重执行，不部署、不合并main。

重复回归：先创建ignored `.local/verifier`，以本树 `.venv/Scripts/python.exe -X utf8 -m pytest -q` 按上列default6、course4、state/UI4顺序串行执行；再node3/builders2，完整42项空白检查参看ignored preseal-check。旧试读服务入口仍为 `http://127.0.0.1:18772/learning?course=action-directing-module`。
