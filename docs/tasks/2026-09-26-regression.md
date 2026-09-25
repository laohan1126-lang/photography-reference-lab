# 2026-09-26：v0.2 真实回归与稳定性验收

## 用户意图与边界（动手前）

> 把已实现的新应用跑起来、跑真实回归、修具体缺陷，而不是推倒重构、删除尚未验收的功能，或继续只输出方案。

在独立 worktree 上核对远端 `366597c5e03ff2197ef17e2a968add3d8f2a7fc0`，保护原工作区未提交的历史素材；运行核心、组件、完整 HTTP 浏览器测试；新空目录真实迁移两次，核对图片和人工选择；桌面/手机浏览器及状态门槛、冲突、离线 ZIP 断网、备份恢复与完整性。发现缺陷补回归再修，不调用付费 API、不公开素材、不部署/合并 main；私人截图不得提交。交付实际命令、统计、证据、限制与推送远端 SHA。

## 执行与结果（执行后追加）

### 1. 自动化回归测试统计

- 全套自动化测试（Pytest 71 passed, 0 skipped, 0 failed）：
  - `tests/test_library.py`: 33 passed
  - `tests/test_imports_jobs.py`: 13 passed（包含本次新增的仓库相对路径回归测试）
  - `tests/test_workers.py`: 10 passed
  - `tests/test_operations.py`: 8 passed（包含在 WSL 环境下启用 Node 校验的内嵌离线 JS 语法验证测试）
  - `tests/test_ui_components.py`: 3 passed（无网络 Chromium 组件流程）
  - `tests/test_browser.py`: 3 passed（真实 HTTP 服务会话、离线包、导出解压与浏览器离线上下文测试）
  - `tests/test_live_system_regression.py`: 1 passed（基于真实全量迁移数据库的端到端真实回归）
- 静态与语法校验：
  - `node --check web/app.js`: exit 0
  - `python -m compileall -q ref_lab tools tests`: exit 0

### 2. 真实历史数据迁移统计（新空 LAB_DATA_DIR: `/tmp/regression-real-data-test`）

- 第一次迁移命令：`python -m ref_lab migrate-legacy --root references/changye-huansheng`
  - 结果：`created: 435, existing: 53, missing: 0`
  - 扫描清单：`data/selected_candidates.yaml`, `staging/live_manifest.json`, `staging/cosplay_manifest.json`, `staging/xhs_manifest.json`, `data/references.yaml`
  - 错误：0
- 第二次幂等迁移命令（相同目录再次运行）：
  - 结果：`created: 0, existing: 488, missing: 0`
  - 完全幂等，没有新增任何重复条目，未覆盖原有选择。
- 历史素材与选择状态核验：
  - 总参考条目：435（独立 Asset 哈希 435 个）
  - 别名映射：488（435 新建 + 53 去重）
  - 原有人工选择保留：`keep: 47`, `pending: 255`, `reject: 133`
  - 派生状态推导：`candidate: 255`, `needs_review: 47`, `rejected: 133`
  - 逐图核验（review）、资料卡（card）、用户独立确认（user_confirmation）、现场成品卡（field_ready）：**均为 0**
  - 历史动作描述与评价（`observed_pose` / `suitability`）全部置于 `legacy_notes`（435/435），作为未验证历史信息留痕，**未自动提升为已审核资料卡**。
- `python -m ref_lab doctor` 完整性核验：
  - `database: ok`
  - `assets_checked: 435`
  - `missing_or_corrupt: []`
  - `missing_derivatives: []`
  - `foreign_key_errors: []`
  - `ok: true`

### 3. 发现并修复的真实缺陷

- **缺陷描述**：历史清单中存在 75 条以仓库根目录为基准的相对路径（如 `references/changye-huansheng/staging/xhs_downloads/...`），原迁移器以角色根目录 `root` 为基准直接拼接，导致路径被解析为 `references/changye-huansheng/references/changye-huansheng/...`，误报 75 条缺图。
- **修复方案**：在 `ref_lab/imports.py` 中的 `migrate_legacy` 解析文件路径时，检查是否以 `references/<root.name>/` 开头；若存在则安全去除仓库相对前缀，按角色根目录正确定位。
- **回归测试补齐**：在 `tests/test_imports_jobs.py` 中增加 `test_legacy_repo_relative_image_path_resolves_without_guessing`，验证修复有效且幂等。

### 4. 浏览器界面与交互验证（桌面 1440x900 & 移动端 390x844）

在 `tests/test_live_system_regression.py` 中通过真实 Chromium 自动化验证以下全部链路，并保存验收截图到私有目录 `.local/regression-evidence/`（符合隐私安全要求，不提交到 Git）：
1. **多角色项目**：成功创建第二个角色“艾拉”，自由要求保存为“需要森林自然光背景，避免过度后期磨皮”，并在项目间自由切换。
2. **独立大图**：通过“查看独立原图”唤起 Lightbox 弹窗，大图自然尺寸解码完整。
3. **响应式适配**：手机宽度 390px 下 `document.documentElement.scrollWidth <= innerWidth` 成立，无横向溢出。
4. **选择与持久化**：K/M/X 状态切换、审美偏好反馈（“姿态非常自然，重点借鉴手部支撑角度”）编辑，浏览器刷新后数据从数据库正确重载持久化。
5. **筛选与分页**：435 条全量、47 条保留、133 条淘汰筛选分页均准确展示。
6. **摄影笔记**：支持 Markdown 创建与编辑，渲染保留排版且过滤恶意脚本。
7. **审核与失效门槛**：
   - 非真人姿势（器材图）核验后，被策略阻拦并明确提示“不是可用的真人摄影参考”，无法成为现场卡；
   - 真人 Cosplay 照片完成人工核验 + 来源权属确认 + 资料卡草稿填写 + 用户独立确认后，成功进入“已通过入库门槛，并由你确认”；
   - 修改项目补充要求后，旧资料卡确认立即失效，重置为“尚不能作为现场卡”；
   - 乐观并发控制：过期修订版本（stale revision）提交修改返回 409 冲突，拒绝静默覆盖。
8. **离线拍摄包**：
   - 导出已确认现场卡 ZIP，解压后验证 `manifest.json` 与独立原图 SHA-256 吻合；
   - 浏览器开启 `set_offline(True)` 断开网络，直接加载本地 `index.html`，大图（naturalWidth > 0）、现场口令、灯光器材方案、PS 路线与清理步骤均完整离线可读。
9. **备份与恢复**：
   - 通过 CLI `backup` 导出一致性快照 ZIP；
   - 解压恢复到全新空目录，运行 `doctor` 校验：数据库 ok，无缺失损坏，完整性 100%。

### 5. 明确未验证项与依赖说明

- **付费视觉模型 / Responses API**：当前未配置 `OPENAI_API_KEY`，根据安全边界未调用付费外部 API。执行器支持离线 JSON 导入与模拟测试；实际接入时需用户配置并授权。
- **Notion 在线同步**：未指定且未授权 Notion 父页面，保持未连接状态。Notion 离线导出 Markdown/CSV ZIP 导入逻辑已全部通过测试。
- **第三方平台自动采集**：小红书/Pinterest 等依赖用户登录态浏览器会话，本次未执行真实外网自动化抓取，避免账号安全与访问限制风险。
- **公共部署**：未部署公开域名，未修改 DNS/TLS，未合并到 main 分支。
