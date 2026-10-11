# 《动作导演》独立最终验收

结论：**PASS（可观察工程、来源/视觉事实及过程证据范围）**。15项原冻结标准均已按适用证据核查；没有尚未解决的已确认课程/业务缺陷。这不代表真人已经学会、审美接受或发布成功。

- 实际入口：<http://127.0.0.1:18772/learning?course=action-directing-module>。独立打开真实课程及图片，不仅检查 HTTP 200。
- 冻结UTC：2026-10-11T07:22:55.590737+00:00。CRITERIA.json SHA256 `a762419dfd97e1754b6a10a84dc7ff095d6c976c4a33b2f751498e4e0a2aacfe`；CRITERIA.md SHA256 `bd9e02617861cbaf3907edcdfecfb9071f3e80fda455cd24114da64295ec5e69`。终验复核未变。
- 验收时间：2026-10-11T08:21:09.189362+00:00。完整逐项结果与定位在 ACCEPTANCE.json。

## 来源与教学

独立重新打开 Lindsay 官方视频五个暂停帧（80/86/200/218/228秒）、官方说明、Lindsay署名Rangefinder正文及Jerry/Westcott合作教程正文和两幅1366×2048原图。课程视觉事实、作者说明、项目迁移和未知条件分开；没有把截图间变化当控制变量、未知脚部当承重证据、假设A/B当真实改片。连续完整视频及音频逐字核验未做，详见 SOURCE_AUDIT.md。

全文八节逐段核查：非武器宽袖信件案例有目标/问题→可说短口令→复拍判据→副作用；有新双人目标判断和固定场地/面罩/厚手套/乐器限制题、默认折叠分析及十分钟真人试拍复盘。16项关联均为现有技能，14域/71模块/247技能基库未扩张。

## 实际读者与状态

1440×1000及390×844隔离浏览器实际遍历八节，验证章节、图文、来源、展开/收起、关闭/重开/重载、技能、旧剑课和旧gateway。图片失败时署名、文本及原址回退可用；真实ROOT页面原图加载成功。无横向溢出/未捕获错误；此课无回答/评分/保存表单。seed revision=3旧记录的GET与底层文件字节前后相等，阅读网络无POST/PUT/DELETE；旧stale写409、新课程写404。未触主人日用数据库。

## 独立执行结果与失败历史

| 范围 | 结果 | 原始证据 |
| --- | --- | --- |
| 项目默认六套回归 | 123 passed | default.xml |
| 阅读/状态/新课相关套件首次 | 48 passed / 1 failed | related.xml |
| 用户授权额外单点CSP测试修正后独立复跑 | 1 passed | authorized-csp.xml |
| 独立桌面/移动/只读状态/兼容测试 | 2 passed | independent.xml |
| 目录/来源/教材/课程 | 30 passed / 1 skipped | catalogue.xml |

首次失败为 tests/test_learning_gateways_ui.py 的旧完整img-src字符串断言：新增两条精确Westcott图片URL后，旧列表不再立即以分号结束。它是已确认测试兼容失败，未证明安全漏洞。原两轮返工已使用；用户明确“允许这一次单点修正”。独立检查修正仅比较精确token集合并增加私人首页排除Westcott，原认证/CSRF路径保留；该用例独立复跑通过。未删测试、放宽来源边界或隐去首次失败。

Windows symlink创建用例因环境能力而skip，尚未验证。canonical `tools/build_action_directing.py --check`、`tools/build_photography_atlas.py --check`及atlas校验通过；扩展摘要 `c51bc07cceb9eb9cdbbbdfc0e5cf27a28a4c6d74b183298b924cfb192d4f6fec`，基库版本 `ce806dc25f42bc242b708939036b037a70da490ad6c5ec4806071c4ad78165a4`。`node --check`三个实际JS及`git diff --check`通过。直接运行tutorial校验模块曾出现`ModuleNotFoundError: tools`，随后正确canonical builder执行全部实际校验；此错误不计候选业务缺陷。

## AGY/CC实证与修订边界

七次真实进程PID/UTC/exit/event数对照原始日志；原始started/events/stderr/result共28文件全部SHA256及字节相等（ORIGINAL_ARTIFACT_HASH_AUDIT.json）。stream的ACTIVE/DONE事件计数不作为去重调用数。实际AGY第二轮完整response与留存稿字节一致（SHA256 `ba0fec692eb6ba3e84af7632e8304469a0fc4b13e232685a1e4690991f9cebf5`），八节均改动；前后两段diff独立重算全等，案例/技能/来源保持。最终明确镜像方法作者、不预认证仿制道具安全、恢复机位光影“可能”条件，逐差异核查。

AGY研究权限拒绝/空输出、CC turn上限、首轮AGY provider错误及实际事实新增均保留。协作报告最初误称receipt已有原始哈希，现已补入实测28条，原缺漏历史保留；独立全核通过。没有假造缺陷或对速度/成本/质量作因果收益宣称。

## 未验证与交付界限

真人记忆、技能迁移、真实试拍效果和用户审美接受仍UNVERIFIED；完整BTS/音频与Jerry长视频未全看，Rangefinder全部插图未打开。原图远程显示的来源/权利说明不授予转载许可。Git/Notion发布与远端SHA由ROOT另验收；本Agent没有提交、推送或发布。既有其他任务dirty依赖只用于保留兼容比较，不纳入本任务拥有变更。

独立只新增 tests/test_action_directing_acceptance.py 与 ignored .local/verifier/证据。各pytest套件的完整命令见下；全部用ROOT现有 `.venv/Scripts/python.exe -X utf8`、当前候选worktree及隔离 `.local/verifier/pytest-*`，未安装依赖。

```text
python -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp .local/verifier/pytest-default --junitxml .local/verifier/default.xml
python -X utf8 -m pytest -q tests/test_learning_course_ui.py tests/test_learning_gateways_ui.py tests/test_learning_state.py tests/test_learning_gateways_state.py tests/test_action_directing.py --basetemp .local/verifier/pytest-related --junitxml .local/verifier/related.xml
python -X utf8 -m pytest -q tests/test_learning_gateways_ui.py::test_gateway_endpoint_requires_session_and_csrf --basetemp .local/verifier/pytest-authorized-csp --junitxml .local/verifier/authorized-csp.xml
python -X utf8 -m pytest -q tests/test_action_directing_acceptance.py --basetemp .local/verifier/pytest-independent --junitxml .local/verifier/independent.xml
python -X utf8 -m pytest -q tests/test_atlas_provenance.py tests/test_learning_content.py tests/test_learning_gateways.py tests/test_learning_course.py --basetemp .local/verifier/pytest-catalogue --junitxml .local/verifier/catalogue.xml
```
