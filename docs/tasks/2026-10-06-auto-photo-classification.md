# 保留图片后的自动摄影分类

## 原始意图与边界
用户：不可能所有的东西全都来手动；经过模型理解一遍；确认保留以后先初步分类，不对可以再调。
在现有测试分支实现视角、景别、主动作的图片级 AI 初步分类，并补处理已保留旧图。人工修正优先。不改变 K/I/M/X、身份核验、现场卡或验收，不调用单独付费 API，不部署日用库、不新增工作树。

## Blueprint
- Python/FastAPI/SQLite + 原生 JS；复用 library_annotations、FACETS、AssetStore、Antigravity CLI 和受控子进程退出逻辑。
- 新增 ref_lab/classification.py 作为独立资产分类队列及视觉适配器，新增相关回归；修改 config/api/library_browser/web/library-browser.js 和文档。
- 用后台队列统一扫描实际保留关系，避免在 K 按钮、导入、灵感收藏等入口各加一套触发分支；同 SHA 只分类一次。
- 队列检查点持久化，任务租约防重复执行；写回采用 annotation revision 比较，人工写入获胜。失败可见、显式重试。
- 模型只读实际图像，不提供标题/项目文本作为分类线索；复用现有枚举，未知时逐字段保留 unknown。
- 风险：真实 CLI 权限、供应商工具输出协议、网络/代理、人工修改竞争、停止保留或替换图片后的旧任务。

## 验收
真实保留触发、旧图补齐、同图复用、实际图像读取、分类可筛选、手动修正及竞争保护、失败重试、租约恢复、无额外卡片/选择写入；核心默认回归、图库 Chromium 回归与真实已保留图片 smoke。合成结果不代表视觉准确率。

## 初始证据
测试分支 codex/patch-convergence-20261004 @306ed12；提权只读 Git 状态干净（受限沙盒的 Git worktree 报错，真实工作区状态正常）。现有三项只有人工 annotation PUT。Antigravity 经原有 127.0.0.1:12000 代理 models 成功，包含 gemini-3.8-flash-medium。


## 实施及实际验证
- 已实现资产级持久队列，正常启动自动发现新 K / 全局收藏和既有已保留图片；仅新建两个分类相关扩展对象（任务表与索引），未改原资产/引用模型。
- 复用 Antigravity CLI 定位和受控进程树；plan + sandbox，无危险自动许可标志。实际图像完成回执、SHA 和 schema 均校验；没有标题猜分类回退。人工修改采用 revision 保护，UI 合并迟到 AI 的未编辑字段。
- 分类入口同时在项目图片详情及跨项目图库；展示模型依据、队列进度和失败，允许纠正与重试。未编辑原启动脚本，仍用该目录 start.bat。
- 本轮明确授权：用户回答“允许，使用现有 Antigravity”，允许测试库已保留私人图片发往现有模型。此前自动审批拒绝了一次真实图调用，未执行；未绕过，收到授权后才继续。

### 已执行命令与结果
在本工作树，用 .venv\\Scripts\\python.exe -B -X utf8 执行；每条 pytest 均带 -p no:cacheprovider。
1. pytest -q tests/test_classification.py 初始：ModuleNotFoundError（新流程尚未实现，红测）。
2. pytest -q tests/test_classification.py tests/test_library_browser.py：31 passed / 14.01s。
3. pytest -q tests/test_classification.py tests/test_library_browser.py tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py：158 passed / 54.51s，.local/classification-evidence/core.xml。
4. pytest -q tests/test_library_browser_ui.py tests/test_library_browser_http.py tests/test_ui_components.py：21 passed / 108.14s，browser.xml。
5. pytest -q tests/test_classification.py tests/test_library_browser_ui.py tests/test_library_browser_http.py tests/test_collection_ui.py：27 passed / 54.38s，final-targeted.xml。包括实际运行后台检测新保留、人工编辑时迟到 AI 合并、不同人工窗口 409 冲突。
6. pytest -q tests/test_windows_runtime_scripts.py tests/test_runtime_convergence.py：40 passed / 44.15s，runtime.xml。
7. node --check web/app.js；node --check web/library-browser.js；git diff --check：通过。
8. 一次组合命令误写不存在的 tests/test_windows_runtime.py，收集前失败；已改用第 6 项实际文件。受限沙盒对 Git 工作树和 SQLite 的访问曾失败，提权只读复核正常，未据失败结果修改文件配置。
9. 实际 agy models 经现有本地代理成功；合成图实际 view_file → JSON 成功（synthetic-stream.jsonl）。真实已保留单图返回平视/全身/站姿，并实际打开原图核对（real-photo-smoke.json）。
10. 真实队列 discover 156 张，执行一张后 pending=155/succeeded=1/error 为空。返回平视/头肩特写，画面缺乏下半身支撑证据所以动作 unknown（queue-smoke.json）；未把单张判断或合成测试当作整库视觉准确率。
11. 对原备份逐行比较 projects=23/assets=891/refs=891/jobs=64/notes=0/inspirations=23，全部保持相同（preserved-data.json）；分类写入独立表与审计事件。

### 交付与限制
状态 PARTIALLY_VERIFIED。功能与上述局部/核心回归及真实模型链路已验证；整批 156 张尚未全部完成，真实视觉分类不是人工验收。已有 Starlette/httpx 弃用警告未处理，不安装无关依赖。
本地任务分支 codex/patch-convergence-20261004；不推送、不写 Notion、不改变日用库端口 18765 或公网隧道。测试入口仍为 D:\\AI PROJECTS\\photography-reference-lab-convergence-20261004\\start.bat / http://127.0.0.1:18766/#view=library。
提交后用官方 launch.ps1 启动最终版本，并将实际 runtime、浏览器及后台队列进度保存到 .local/classification-evidence/runtime-smoke.json 和 real-library-classification.png；未跑的启动不预先标通过。服务保持开启才继续处理；失败在页面显式暂停并重试，停止/重启从持久队列继续。
