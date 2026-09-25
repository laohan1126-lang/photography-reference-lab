# Codex 接手回归

## 本轮交付边界

基线 `main@2068dc2e9f269af38a261a92af34f8779a08b980`；重构分支 `codex/reference-library-rebuild`。主分支和历史图片/批次不被自动重写。本轮新增实际应用、迁移器、执行器、资料卡策略、测试与操作入口，不以旧 HTML 宣称新应用已经上线。

构建环境已运行：63 项后端/导入/执行器/运维测试通过；3 项无网络浏览器组件流程通过（包括桌面/移动布局、独立选择、核验到确认、笔记编辑与待执行任务）。Node 主脚本及离线内嵌脚本语法检查通过。测试图片为合成矩形样本，不是 cosplay 图像识别准确率证据。

当前环境的完整浏览器测试在导航本机 HTTP 地址时返回 `net::ERR_BLOCKED_BY_ADMINISTRATOR`，3 项未完成。组件测试不替代它们。真实旧素材全量迁移、实际站点采集、真实模型/Notion API、Windows/手机文件打开、Docker/域名部署均需下列回归；不可把它们报告为本轮已验证。

## 1. 先保全工作区

不要覆盖未提交的工作。确认分支与最新远端 SHA，必要时创建单独 worktree：

```bash
git fetch origin
git switch codex/reference-library-rebuild
# 无本地分支时：git switch -c codex/reference-library-rebuild --track origin/codex/reference-library-rebuild
git status --short
git rev-parse HEAD
python -m venv .venv
# 激活虚拟环境后：
python -m pip install -e ".[test]"
python -m playwright install chromium
```

先读 AGENTS.md 与本轮任务记录。不需要重做架构、重新找几百张图或以“闭环未验收”为由删除功能；重点验证真实运行和修缺陷。

## 2. 自动回归

```bash
python -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py
node --check web/app.js
python -m compileall -q ref_lab tools
python -m pytest -q tests/test_ui_components.py
python -m pytest -q tests/test_browser.py
```

缺少 Chromium 时先安装，不能把 skipped 当 passed。完整浏览器测试必须走真实 HTTP 服务与会话，并打开导出的离线 ZIP 解压页；组件测试使用 TestClient 桥接，不覆盖网络、Cookie、跨域策略或 file:// 实际环境。CI 会分别运行核心和浏览器任务，不自动部署。

## 3. 真实历史数据迁移

在**新的空 LAB_DATA_DIR** 试运行，不覆盖现用数据库：

```bash
# PowerShell: $env:LAB_DATA_DIR="$PWD/.local/regression-real"
# Bash: export LAB_DATA_DIR="$PWD/.local/regression-real"
python -m ref_lab migrate-legacy --root references/changye-huansheng
python -m ref_lab migrate-legacy --root references/changye-huansheng
python -m ref_lab doctor
python -m ref_lab serve
```

对照原文件真实计数：每个批次总项、实际有图/缺图、精确去重、KEEP/MAYBE/REJECT、导入失败。第二次不得新增重复条目或重置用户选择。抽查至少 20 张独立图片：实际尺寸、来源、原始哈希、原历史选择及图片绑定关系。确认全部旧 observed_pose/suitability 只进 legacy_notes，没有自动得到 review、card 或 field_ready。

如果某路径缺失，先查看原目录与导入错误，不能凭相似文件名配图，更不能拿旧拼图裁切冒充原图。已有被转存的 JPEG 只能称接收到的历史版本，不能宣称是作者无损原片。

## 4. 人工浏览器回归

桌面及约 390px 手机宽度分别验证：创建第二角色只填角色名；自由要求完整持久化；上传/候选 ZIP；独立大图放大；K/M/X；跨页过滤；关闭并重新登录后选择仍在；有未保存反馈时切换条目/过滤器会提示；两个窗口编辑同一条产生 409 而非覆盖。

将器材、场地、插画、拼图、低清、动作遮挡、错误角色和合格真人图作为**明确标记的测试批次**。逐项核验真实图片；错误素材不能被写成现场主卡。正向条目需要 KEEP→核验→来源确认→卡片草稿→独立确认。修改来源、图片和角色要求后资格应撤销，历史数据仍保留。

资料卡 UI 检查：静态/动作引导、摄影师动作、安全降级、现有一灯器材方案、布光证据与推测分栏、none/cleanup/composite 后期路线。检查人物左右与画面左右清晰，不编造原作者灯光参数。

## 5. 离线与恢复

导出 3–10 张真实确认的现场卡及独立灵感包。确认每张图片单独存储、原字节哈希相同；断开网络后打开解压的 `index.html`，大图、口令、上下张和 PS 内容可见。Windows Edge、用户实际手机文件打开方式各验一次；不能仅靠浏览器“已缓存过页面”宣布通过。

备份到新 ZIP，停服务后恢复到另一空目录，重新指定数据目录并 doctor，核对项目/选择/笔记和原图。复制一个测试资产并故意损坏后检查 doctor 撤销确认；测试后不要把损坏副本或测试标注混进用户正式库。

## 6. 执行器与集成

先测试“不配置 API”路径：建立任务→下载独立图片任务包→按 Schema 导入分析结果。检查过期 revision/hash、跨项目 ID、缺字段、AI 无法确定的图与部分失败。所有 AI 结果保持草稿，无模型也能正常使用网站。

实际小红书/Pinterest 采集仅使用用户正常授权的浏览器会话；最多小批量验证，出现访问限制立即停。免费网页浏览不保证平台自动化稳定可用。付费模型分析必须先确认 API 密钥、模型可用性、发送图片权限与费用；不得把 ChatGPT Pro 订阅当 API 支付方式。

Notion 导入用用户导出的 Markdown/CSV ZIP 验证文字、图片、源路径和未解析链接，重复导入不覆盖笔记编辑。摘要同步需用户指定并授权 Notion 父页面；尚未提供目标时保持未连接，不自行选库。

## 7. 回执与提交

将实际命令、退出码、测试统计、截图、迁移计数、发现的缺陷和明确未验证项写入 `docs/tasks/`。截图含用户参考图时仅保存在私有运行目录，不自动公开推 Git；可提交不含私人素材的摘要。合成截图必须标明“测试样本”。

修复缺陷后先提交任务分支，再推送并核对远端 SHA。不要 force push，不自动合并 main，不自动发布域名，不以“测试都过了”代替用户的真实图像/审美验收。
