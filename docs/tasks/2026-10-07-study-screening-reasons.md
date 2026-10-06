# 待筛摄影参考：人工筛选理由 — 2026-10-07

## 用户意图与边界（实施前）

用户在待筛摄影参考截图中要求：“筛选理由增加一下吧 构图可学 姿势可学 光线可学”。

- 在每张待筛图片的“你的筛选”区域增加这三个可多选理由，点击后持久保存，再次打开仍显示已选状态。
- 理由属于用户人工标注，与 Dot 文案关键词和待筛状态分别存储；不自动从 Dot 文字推断，不自动进入审美库或角色项目。
- 旧条目默认没有人工筛选理由，不改变原状态、备注、原图或来源。编辑继续使用 revision 冲突保护。

## 可观察验收

1. 三个理由可独立选中、取消、组合；页面反馈与 API 重新读取一致。
2. 修改理由不重置人工状态或备注；旧数据仍可打开。
3. 未知理由被 API 拒绝，过期 revision 不覆盖新编辑。
4. 相关 API 与 Chromium 组件测试通过；记录实际命令、结果与限制。

## 结果与验证（实施后追加）

在待筛单图的“你的筛选”中加入三个可多选按钮：构图可学、姿势可学、光线可学。点击即保存，选中态可再次点击取消；三者与待筛状态、个人备注和 Dot 文案线索分别存储。旧条目读取为空列表，不改原始资料或用户的既有决定。API 只接受三个指定理由，按 revision 拒绝过期写入；重复导入不会覆盖人工理由。

实施前先运行新 API 与 Chromium 用例，结果 **2 failed**，分别是编辑接口拒绝未知字段、页面没有理由按钮，确认回归能识别缺失行为。实施后，`tests/test_dot_study_import.py::test_study_reasons_are_independent_human_choices_with_revision tests/test_ui_components.py::test_dot_study_queue_keeps_candidate_separate_from_taste` **2 passed, 1 warning**；规定核心回归加 Dot 用例 **120 passed, 1 warning**；Chromium 组件回归 `tests/test_ui_components.py tests/test_collection_ui.py` **19 passed, 1 warning**。`node --check web/app.js`、`python -m compileall -q ref_lab tools tests`、`git diff --check` 均通过。

在用户实际导入的资料库上只读核对：238 条候选均无人工理由，P365 保持 pending。临时本地 HTTP + Chromium 打开 P365，原图与三个未预选按钮正常显示，HTTP 200、0 页面错误；服务已停止。再次核对原有项目/收藏/资产行无差异，SQLite 完整性 ok，原先 72 条外键错误数未变。没有替用户点击或评判这 238 幅图；实际长期使用中的审美选择仍需用户逐图完成。

下次回归：在隔离库中为同一候选多选和取消理由、切换视图后读取、保存备注与状态并重导；需要人工验收时在日用入口自行标记真实图片。真实 HTTP 检查只验证显示与读取，没有在日用资料库写入用户选择。
