# ROOT 集成与复查说明

这份补充由 ROOT 编写；ACCEPTANCE.md / JSON 是独立 Verifier 的原样终验报告，不把发布结果改写进独立验收。

当前实际入口：<http://127.0.0.1:18772/learning?course=action-directing-module>。独立 preview 已运行；原日用 18765 服务未重启。浏览器可从“完整课程”列表进入，也可用以上深链；正文、来源、现场问题与折叠解析均复用既有阅读器。查看原图需能访问作者站点；若图片失败，页面保留署名、文本及原地址回退。

重新启动 preview（项目根目录）：

```powershell
& .venv/Scripts/python.exe -X utf8 tools/preview_learning.py --port 18772 --reference-url http://127.0.0.1:18765/
```

独立只读回归已原样复制到 `tests/test_action_directing_acceptance.py`，ROOT 实际复跑 2 passed（14.57s）；它使用隔离数据并验证旧记录字节不变、阅读零写请求、旧 stale 写409与课程写404。复跑前创建 ignored 证据目录；不会打开日用图库数据库：

```powershell
& .venv/Scripts/python.exe -X utf8 -c "from pathlib import Path; Path('.local/verifier').mkdir(parents=True, exist_ok=True)"
& .venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_action_directing_acceptance.py --basetemp .local/verifier/pytest-independent
& .venv/Scripts/python.exe -X utf8 tools/build_action_directing.py --check
```

`default.xml`、`related.xml`、`authorized-csp.xml`、`independent.xml`、`catalogue.xml` 为 Verifier 实际运行的原始 XML，保留首次失败。`ORIGINAL_PROCESS_AUDIT.json` 与 `ORIGINAL_ARTIFACT_HASH_AUDIT.json` 为独立审核；原图截图与原始进程日志仍在 ignored `.local/`，未进入 Git。ROOT 的追加复跑 XML 在 `.local/action-directing/root-independent.xml`。

发布采用首次编辑前已建立的 immutable Publisher 事务。用户另明确批准临时保留/移出六项其他任务暂存内容、发布后按原 blob/mode/stage 恢复；项目工作文件不改变。仅课程及最小阅读器适配/回归/本任务报告纳入提交。最终 Git commit/push/remote SHA 和 Notion 状态以保存的 Publisher 收据分别报告；不由本说明预认成功。真人学习、审美接受与现场效果等待用户试学反馈，流程推广尚未决定。
