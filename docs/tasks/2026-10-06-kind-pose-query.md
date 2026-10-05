# 修复“站姿 + 真人 cosplay”组合筛选
## 用户原话与事实
“我搜个站姿都搜不到 认真的吗。”
18766 当前代码 b9a079a，工作区干净。只读实际 API：站姿 5 张、真人 cosplay 5 张、两者组合 0 张。已分类站姿条目的 kind 全为 unknown。模型只输出三项，而类型筛选仅读取 asset_observations；是同一次检索的数据契约未接通，不能把问题归咎用户选了多个条件，也不能通过放宽 AND 或把未知当真人处理。

## Blueprint 与验收
沿用 blueprint-design-brief / tdd-guard。复用现有 Kind 枚举、asset_observations、摄影分类队列和图库；模型同一次实际看图同时输出 kind / viewpoint / framing / pose，在一次事务保存类型观察与导航分类。类型观察不伪造完整 review 或现场卡。
队列的完成条件改为所需检索维度均已处理；已经只有三项的旧结果补看图片类型，人工分类只补缺失维度，不覆盖。类型人工修正优先且可冲突检测。
修改 classification/library_browser/catalog_data/api/web/library-browser 及针对性测试；不新建工作树/数据库表，不改资产/项目选择、日用18765或公网服务。用户上一轮 Antigravity 图片发送授权持续有效。
验收必须实际使用站姿+真人 cosplay 组合；检查插画、generated、unknown 不混入、人类类型修正不会被 AI 覆盖、半完成旧结果能续接、提示区分排队未知与确无匹配。最后正常 start.bat 启动18766并验证真实模型结果。

## 用户进一步明确的范围
用户指出“站姿怎么可能只有五张 明明一大堆”。实际图库354张；之前队列仅156张保留/收藏，198张待选从未排队；当前浏览图片也为pending。已询问私人图片外发范围，用户明确回答“允许，补齐整个可浏览图库”。因此替换仅保留的入队假设，队列与图库共用同一可见性规则；不以修改K/I/M/X来凑入队资格。后台完成数不是图库实际站姿总量。

## 结果与回归
- 修正完成条件：类型观察 + 摄影分类均已存在才算完成，不再把“三项已填”当整个检索数据准备好。旧 AI 三项仍保留，缺类型者补看；人工三项不覆盖。
- 同次模型结果把 Kind 与三项在一事务保存；没有猜标题或放宽组合 AND。人工类型修正独立保护，可在图片详情修改，冲突返回409。
- 共用图库可见性，354张可浏览图片进入自动补齐范围，未改变任何K/I/M/X。已完成标签数不能表述为库中真实姿态数量。
- 全库补分类实际遇到1个旧单图输出失败，旧逻辑会使全队列暂停；改为 failed 只标记此图，blocked 才表示执行器不可用。失败仍可显式重试，不靠假标签填空。
- 筛选结果随后台分类完成自动刷新；未分类覆盖不足明确提示，避免误导为库里没有这类图片。

### 实际执行
命令在本工作树使用 .venv\\Scripts\\python.exe -B -X utf8，pytest 另带 -p no:cacheprovider。
1. 新增失败场景红测：pytest -q tests/test_classification.py -k 'populates_kind or missing_type or old_three'：3 failed，确认类型/三项契约断裂。
2. 完成范围规则调整后 pytest -q tests/test_classification.py tests/test_library_browser.py：40 passed / 23.67s（kind-pose-core.xml）。
3. pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py tests/test_library_browser.py：145 passed / 73.11s（kind-pose-default.xml）。
4. 最终 pytest -q tests/test_classification.py tests/test_library_browser_ui.py tests/test_library_browser_http.py：31 passed / 64.18s（kind-pose-final.xml）。含真实Chromium的“真人cosplay+站姿”、自动刷新、人工类型改回旧值、冲突及待选不被自动保留。
5. node --check web/app.js；node --check web/library-browser.js；git diff --check；变更Python内存AST：通过。
6. 真实图库补看6张，实际组合查询已返回1张真人cosplay站姿；对应原图已打开核对，画面俯拍、全身、双脚站立（451863…）。其余真实模型输出保持各自类型，未强行改为cosplay来凑结果。证据 .local/classification-evidence/kind-pose-live.json。
7. 原备份逐行对比：projects23/assets891/refs891/jobs64/inspirations23全部相同；仅检索注释、部分类型观察、队列及审计变化。
8. 适配新契约时已有测试4项失败：旧测试认为任何手工三项都不补类型，以及2处替身缺少必填kind；更新为“保护人工三项、只补缺失类型”并补齐替身字段后通过，没有削弱原人工保护断言。
9. 旧18766已用官方terminate.ps1停机，最终提交后再用原launch.ps1启动并保存实际HTTP/browser回执；日用18765未停止。

状态 PARTIALLY_VERIFIED：代码与真实组合路径已验证；全库354张后台批次仍待完成，不宣称视觉准确率或整库分类完成。已授权补齐整个可浏览图库，不推送GitHub/Notion，不切换公网。日常仍用同目录start.bat，端口18766。部署后页面证据保存在.local/classification-evidence/kind-pose-runtime.json。
