# 图库检索与导航优化 — 2026-10-02

## 用户意图（实施前记录）

用户："请按照你的设计修改仓库 我同意你的判断和优化方案"。
此前批准的方向：从功能可行转向使用体验；高/低机位是跨项目找图条件，不是继续增加平铺项目；保留独立资产、项目引用和人工判断；优化过滤不能以新增误杀为代价。

## 基线与边界

- 源分支：`codex/data-safety-recovery-20260930`，实查 SHA `83c422a6acc2fed11a20528c07946f223f4268ca`（比上轮 c18ccea 更新）。
- 任务分支：`codex/library-discovery-optimization-20261002`。
- 本轮优先落地跨项目图库、组合筛选、可保存查询、项目搜索及常用项目导航，并检查过滤反例。
- 不重构 CAS/人工选择/现场卡验收，不改变 Windows 主运行路径，不访问用户真实 SQLite，不上传新图片/凭证，不调用付费模型，不合并 main，不自动部署。
- 图库查询不把项目名、标题、搜索词或淘汰原因升级为图像事实；缺少摄影分类保持未知。
- 保存查询不是固定拍摄清单。审美库收藏不等于项目 keep。跨项目浏览不合并/覆盖各项目 decision。
- 本轮不宣称完成视觉模型训练、个性化排序、近似图比较或离线现场卡改版；这些属于后续独立阶段。

## 可观察验收

1. 不知道图片所在项目，也能跨项目浏览与检索；同一 asset 在同一结果集只出现一次，能回到各自项目的原 reference。
2. 筛选在服务端分页前完成，未知分类不猜测补齐，查询稳定排序，有无结果/失败/过期请求处理。
3. 项目数量增加时，导航不无上限平铺；可搜索并打开旧项目；当前项目保持可到达。
4. 常用筛选可保存、重用、删除；不复制图片，不改变审美反馈。
5. 所有新增 API 沿用登录、CSRF、Host/Origin 和维护模式防护。
6. 过滤规则保留明确无关内容的拦截，不以泛词/单一白底比例代替视觉识别；针对实际反例增加回归。
7. 记录实际执行命令、结果、环境局限与 Windows/真实图库未验证范围；验证远端 SHA 后才宣称推送成功。

## 执行记录

- 已通过 GitHub 连接核验基线并读取 AGENTS.md、README.md、docs/ARCHITECTURE.md。
- 当前隔离执行环境直接 git clone 因 DNS 不可用受阻；GitHub 连接读写正常。独立模块可本地测试；整库验证通过分支 CI 或交接命令明确报告，不将其默认标为通过。

## Outcomes

### 已实现（隔离代码副本）

- 新增 `ref_lab/library_browser.py`、`web/library-browser.js`，注册到原 API 与网页，不替换已有单图工作台。
- 跨项目独立资产网格；SQL 组合条件在分页前执行，精确资产去重，限定项目的 K 不借用其他项目决定；图片详情可回到精确原 reference。
- 明确视角/景别/主动作导航分类，缺省 unknown；读取现有观察的图片类型，横竖幅来自尺寸，不猜图像内容。分类保存有 revision 冲突检查，原选择/原字节不变。
- 服务器保存动态查询；项目搜索、最多 8 个常用项目、置顶/最近访问、每页 30 个的全部项目目录。手机保留目录入口；过期图库响应不会覆盖其他视图。
- 独立扩展表，与现有 schema 3 兼容；完整 backup/restore 覆盖新导航数据，不改 CAS/旧表/真实库。
- 移除泛词与作者/URL 路径的负向意图误杀。近白比例改为 discovery 提示，不写伪造视觉 preflight；保留明确招募/出租/出售/教程等过滤。
- 新 JS 纳入安装包，原 API 安全中间件覆盖新路由。CI 增加新后端、组件与真实 HTTP 用例，不移除原回归。

### 实际验证

隔离 Linux / Python 3.13、Node 22、Chromium；全是独立测试数据，没有打开用户本机 SQLite。

1. 改动前原有后端范围：**185 passed**（25.71s）。
2. 完整本轮本地回归：**241 passed**（89.84s）：
   ```sh
   python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_modality_archive.py tests/test_reference_transfer_board.py tests/test_collect_adapter.py tests/test_collection_runner.py tests/test_candidate_pipeline.py tests/test_collection_dispatch.py tests/test_windows_runtime_scripts.py tests/test_data_safety.py tests/test_confirmed_archive.py tests/test_library_browser.py tests/test_collector_boundary_regressions.py tests/test_ui_components.py tests/test_collection_ui.py tests/test_library_browser_ui.py
   ```
3. 最后补正手机全部项目入口与目录对比度后：`python -m pytest -q tests/test_library_browser_ui.py` **4 passed**（8.21s）。
4. `node --check web/app.js`、`node --check web/library-browser.js`、`python -m compileall -q ref_lab tools`、`git diff --check`：退出 0。
5. 新测试覆盖一万条合成元数据的分页/过滤、共享资产选择隔离、unknown、备份恢复、认证/CSRF/维护模式、保存查询动态成员、手机视口和过期响应。元数据规模测试不是一万张实拍或视觉准确率测试。
6. 实际尝试 `python -m pytest -q tests/test_browser.py`：**5 failed**，均在 `page.goto(127.0.0.1)` 被执行环境 `net::ERR_BLOCKED_BY_ADMINISTRATOR` 阻止，未进入业务断言。不计为通过，也没有通过更改生产代码/跳过断言规避。真实 HTTP/离线链路仍需分支 CI 与 Windows 本机验证。
7. 新增独立 `tests/test_library_browser_http.py` 到 CI；本地已知 HTTP 限制下未重复声称跑通。代码副本不含历史图库，所以 `test_live_system_regression.py` 留给完整仓库 CI，没有编造历史迁移结果。
8. 首次新测试出现两处 TestClient DELETE 参数写法错误，已修正并重跑；没有以减少测试断言修绿。

### Git 发布与环境边界

- GitHub 连接获取代码专用临时 artifact，私有运行数据/新图片/凭证未入包；原图相关仓库目录不被此代码副本覆盖。
- 发布使用已本地检查的逐文件 patch 与 blob 哈希校验，只允许本任务分支快进写入；临时代码快照/应用辅助 workflow 随交付清理。后续最终远端 SHA、PR 与 CI 结果以 GitHub 回执为准，不用本地摘要冒充远端运行。
- 没有合并源分支或 main，没有自动升级用户 Windows/手机服务，没有触碰本地 Skill 安装目录或进行 Notion 同步。
- 未完成也未宣称：自动视觉标注、个性化排序、Skill 新旧同池 A/B、近似图比较、固定拍摄选集和离线界面统一。

### AntiGravity 本机接手

1. 读取本任务与 `docs/LIBRARY_DISCOVERY.md`；`git fetch origin`、核对任务分支最终 SHA、检查工作区，不覆盖未提交工作。源分支又有新提交时先比较，不盲目 reset。
2. 从当前实际运行进程/API 与 `.local/windows-runtime.json` 确认真实数据目录。先停止采集写入并备份，禁止靠默认路径猜库；保留完整备份及旧 checkout。
3. 在独立任务分支先用备份副本运行 doctor 和上述回归，补跑 `tests/test_library_browser_http.py tests/test_browser.py tests/test_live_system_regression.py`。Windows Python 与 collector 必须来自同一 checkout。
4. 用真实图库检查：跨项目同图只有一条；K/淘汰独立；仰拍+全身筛选、保存查询、重启恢复、搜索旧项目、手机目录可读。新分类不要求一次性标完，未知不自动填事实。
5. 真实采集再检查一组有翅膀的好图、白背景好图及明确招募/广告；记录误收/误杀，不凑数、不通过 SQL 伪造人工反馈。
6. 本机验收后再按用户意愿采用该分支。保持现有域名、端口、token、Windows 启动路径；不自动合并 main。记录采用前后计数、backup/doctor 与实际 SHA，不把 CI 等同于本机已部署。
