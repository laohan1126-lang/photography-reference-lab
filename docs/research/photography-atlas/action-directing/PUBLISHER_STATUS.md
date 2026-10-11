# ROOT 发布阻塞记录

课程工程/来源/协作的独立终验通过；**本轮正式发布未完成**。这是 ROOT 的 Publisher 事务初始化顺序错误，不是用户缺少推送授权，也不改变独立课程验收结论。

事务在首次文件编辑前建立并冻结原始 baseline，但当时仍在 `codex/evidence-photography-atlas`；ROOT 随后才建立/切换本轮要求的 `codex/action-directing-module-pilot-20261011`。canonical `core/lifecycle.py::validate_workspace` 要求当前分支等于事务已绑定分支；实际 seal 返回 `WORKSPACE_BRANCH_CHANGED`（CLI exit2）。没有 sealed manifest、commit或push意图，也没有 Notion 写入。

现有 recover 同样验证分支，bind-existing 只处理已有 Git SUCCESS 的终结事务，均不能迁移这项未完成事务。不得修改 state/baseline、重采已经编辑后的基线、把新用户 turn 绑定到旧事务、临时冒用原分支发布或绕过 Publisher。ROOT 没有尝试这些操作，也没有重复提交。

经用户明确授权，其他任务六项暂存内容曾临时保留/移出；两个尝试都在 finally 恢复。第二次核对：全部原 staged blob/mode/stage 及 cached raw 完全相同，项目工作文件哈希完全相同，HEAD 仍 `fc6290cc4978529fdd9f58ed6cea02bab736de8a`。第一次停在保护脚本误将 tracked-missing 元数据作为文件变化的预检；根因及有边界恢复记录在任务文档。原备份和两次恢复证据保留在 ignored `.local/action-directing/`，没有覆盖原备份。

状态：Git **未提交/未推送**，新 commit SHA 无；Notion **未执行、待处理**。当前目标任务分支保留全部本课程工作文件；不把原 HEAD 当作本轮交付 commit。canonical defer 的实际结果另保存在本事务收据中。真人试学入口仍为 <http://127.0.0.1:18772/learning?course=action-directing-module>，重启说明见 ROOT_INTEGRATION.md。

canonical `defer --blocker <实际分支错误证据>` 已执行成功，保存的真实收据为 `receipt_status=DEFERRED`、`completion_status=BLOCKED`、Git `PENDING` / commit_sha null、Notion `PENDING`。没有重新创建事务或改写 baseline。收据副本为 `.local/action-directing/publisher-deferred-receipt.json`；完整 canonical receipt 仍在原事务目录。最终复查实际入口 HTTP200，附加包恰好一门课程；原六项 cached name-status 与重命名比例再次核对相同，`git diff --check` 无错误。

补充外部验证边界：末次 `git ls-remote origin refs/heads/codex/action-directing-module-pilot-20261011` 长时间无输出，ROOT 只终止已确认属于该查询的两个 Git 进程；没有得到当前远端 SHA，不能将其空输出称作“远端不存在”或“SHA匹配”。先前基线查询与本轮末次查询分开记录。seal 未成功，因此 canonical finish 的配置检查/提交/推送/Notion阶段未执行；报告中的已通过回归是 ROOT/Verifier 的真实独立运行，不冒称 finish 已通过。
