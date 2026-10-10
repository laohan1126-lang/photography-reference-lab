# AGY read_url 权限最小修复与真实复测

日期：2026-10-10（Windows 主机）。结论：**官方域名真实读取 VERIFIED；B&H 授权后仍 HTTP 403，无正文，读取未成功。** 不能把任何一次 CLI `SUCCESS` 单独当作网页读取成功。

## 实际环境与初始规则

当前 PATH 命中 `C:/Users/Dell/AppData/Local/agy/bin/agy.EXE`；实际 `--version` 为 **1.3.3**，不是上次任务记录的 1.3.2。本轮没有安装、更新或降级 CLI，结论只覆盖此次实际执行的 1.3.3。

实际用户配置：`C:/Users/Dell/.gemini/antigravity-cli/settings.json`。没有 AGY/Antigravity/Gemini 环境变量覆盖。仅检查并报告相关权限，不输出凭据或无关设置。原 `permissions` 对象仅有 `allow` 键：

```json
{"allow":["read_url(youtube.com)"]}
```

`ask`、`deny` 未配置，没有匹配指定域名的显式 Ask/Deny。原有 YouTube 网页规则保留。

[官方 Windows/CLI 权限文档](https://www.antigravity.google/docs/permissions?tab=cli)规定全局 CLI 设置路径、Deny > Ask > Allow 的优先级，以及 `read_url(domain)` 对域名及其子域的匹配。`read_url` 对应内部 `read_url_content`；浏览器交互权限另行处理。[Headless 文档](https://www.antigravity.google/docs/cli/headless/)说明非交互会话不能提示批准时会 soft-deny，退出码仍可能为 0。本轮使用具体域名规则，没有 wildcard 或跳过权限。

## 实际修改与回滚

第一次修改前保存现有配置的原始字节：

- 私人备份：`D:/AI PROJECTS/photography-reference-lab-agy-headless-20261010/.local/agy-readurl-retest/settings.before.json`。
- 原始/备份 SHA256：`cf9cdb5f7ecf51af1c5fad8378d52c832946a089775a3c9a43f8153630f3a471`。
- 先仅插入 `read_url(antigravity.google)`；官方页面正文取得且工具未拒绝后，才插入 `read_url(bhphotovideo.com)`。
- 最终 Allow 顺序：`read_url(youtube.com)`、`read_url(antigravity.google)`、`read_url(bhphotovideo.com)`；没有新增 Ask/Deny 键。
- 完整 JSON 对比通过：除两个新增 Allow 值外，其余全部设置相同。两次人工插入都保留当时文件的其他字节；会话运行后观察到仅格式变化，最终字节哈希为 `54f8eb9ccf2ce70d820536c8f2856868f163c139973bcc7cc347683851915048`。不能声称会话结束后原文件格式仍逐字相同。`permissions-change.json` 分别保留人工插入后的哈希及最终复核哈希。

受保护回滚脚本位于 `.local/agy-readurl-retest/rollback.py`，已实际运行默认 dry-run：**PASS**。它校验原备份哈希，并要求当前完整 JSON 恰好等于原设置加上述两项；有后续其他修改时拒绝覆盖。回滚预演没有修改配置；本轮没有实际回滚，以便保留已验证的官方域名授权。

```powershell
# 预演；加 --apply 才恢复原始配置字节
& 'D:\program files\bin\python.exe' -X utf8 'D:\AI PROJECTS\photography-reference-lab-agy-headless-20261010\.local\agy-readurl-retest\rollback.py'
```

## 两个目标的真实结果

两次目标调用均为**新会话**，没有 `--continue` 或 `--conversation`，使用 `--output-format stream-json --print-timeout 180s`，外层截止 240 秒均未触发。实际参数、UTF-8 提示词、stdout、stderr、CLI 日志、退出码、墙钟和正文在私人目录保存；不用另一个工具的读取结果代替 AGY 的结果。

| 目标 | 新 conversation | `read_url_content` 真实结果 | CLI 终态 / 正文 | stderr / denied_actions |
|---|---|---|---|---|
| [官方 Headless 页](https://www.antigravity.google/docs/cli/headless/) | `dfa2ccdd-dbe8-49eb-baf4-df0a97a976f5` | step 2 DONE，2.9762534 秒 | exit 0 / SUCCESS；返回标题、正文摘录及三项页面事实，response 1279 字符；实际进程 55.52 秒 | stderr 0 字节；result 未输出 denied_actions 字段，未观察到拒绝 |
| [B&H Beginner's Guide to Portrait Composition](https://www.bhphotovideo.com/explora/photography/tips-and-solutions/beginners-guide-to-portrait-composition) | `a4f70f37-f52c-4fcd-9287-5cd755281ba4` | step 2 ERROR，2.8626719 秒；`Failed to fetch document content ... status code 403` | exit 0 / SUCCESS；response 427 字符是错误说明，**没有页面正文**；实际进程 30.20 秒 | stderr 0 字节；result 未输出 denied_actions 字段，未观察到权限 soft-deny |

官方工具抓取文件实际位于该会话 `.system_generated/steps/2/content.md`。文件扩展名为 md，实际内容含 HTML；已逐字复制到 `official.page-body.md`，215205 字节，SHA256 `25d4d14619e42f65d57880dd440754fcadac9c6068a0dd889c1d9771e527d0ea`。AGY 随后通过 `view_file` 读取自己的抓取结果，没有使用命令或其他 URL。Codex 使用标准库 HTMLParser 排除 script/style 后检查了 29185 字符的可见正文，包含 Headless 的运行方式、输出格式及权限段落；这些是正文内容，不只是标题或 meta 标签。AGY 最终引文有标点编码损伤，原始结果与原抓取字节均保留，没有改写成伪造的“完整成功输出”。

B&H 工具实际走到 HTTP 请求并返回 403，和权限系统拒绝不同；**未证明 B&H 正文可读，也未确定 403 的具体原因**。不重试挑战、不换工具绕过、不扩大域名权限。

## 保留的失败与异常记录

第一次会话结束后，配置字节哈希变化，但完整 JSON 与原配置加第一项授权完全一致。第二次人工补充的严格字节保护检查因此中止，未写入 B&H Allow。Codex 随后误启动了一次尚未加授权的 B&H 会话，未覆盖或掩盖这个失败：

- 私人记录前缀 `bh`；独立会话 `1568a53e-9a20-410e-866c-350e3f04ac38`。
- `read_url_content` step 2 ERROR：`user denied permission for read_url(bhphotovideo.com)`；退出码 0/SUCCESS，response 空。
- `denied_actions=[{"action":"read_url","display_name":"ReadUrlContent"}]`；stderr 303 字符，明确提示 headless 自动拒绝。
- 后续先核对**全部 JSON 值**相等，再做仅指定域名的人工插入，最后另开 `bh-authorized` 新会话。未恢复/绕过该被拒绝会话，未用其他工具获取同一 URL。

三个会话 init 均记录 `permission_mode=request-review`，实际调用参数没有 `--dangerously-skip-permissions`。私人 CLI 日志仍出现上轮已知 `task-finalization_PreInvocation` 路径引号错误；AGY 自定义 hook 的现场兼容性仍为 **FAIL**，本轮没有修改它。Codex canonical Publisher 独立运行，不用 Headless 正文成功推断 hook 成功；WSL_NOT_COVERED。

## 范围与后续判断

可以继续在 Codex 中用无 IDE 的 `agy -p` 读取**已授权且站点允许抓取的网页**；本轮官方域名已真实验证。B&H 仍有 HTTP 403，其他域名没有自动放行；域名规则匹配的是站点及子域，不是单一路径授权。

YouTube：原 `read_url(youtube.com)` 保留；本轮没有调用其网页、浏览器视频播放、音轨或下载工具。旧规则不是播放/下载成功证据，未新增 `execute_url`、命令执行或下载授权。上轮 BrowserSkill 播放及媒体 403 的历史结果保持原记录，不升级为本轮 AGY 能力。

没有修改系统代理、凭据、IDE 配置、其他权限、项目产品代码或摄影主数据。AGY 子进程仅复用已启用且检查连通的 Windows `127.0.0.1:12002` 代理路径，和上轮一致；没有改系统设置。两份正式文档之外，备份、抓取全文、提示词、原始日志及回滚脚本均位于 Git 忽略目录，已用 `git check-ignore` 核验。保留主工作区原有未提交改动。

复测方法：从 `.local/agy-readurl-retest/official.prompt.txt` 或 `bh-authorized.prompt.txt` 读取原提示词，再以当前 AGY 路径运行 `-p <提示词> --output-format stream-json --print-timeout 180s`，为新 stdout/stderr/log 使用新文件名，检查新会话工具状态、生成的页面正文、stderr 与 denied_actions。B&H 403 不应靠重复重试变成“通过”。本轮只做两站权限和真实读取验证，未开发框架或调用独立收费 API。

工程测试和正式交付状态另以 canonical Publisher 的实际 checks/receipt 为准；Git/Notion 与网页读取结果独立报告，不预填提交或外部同步成功。


## 正式记录交付路径

主项目实际检查：`.venv/Scripts/python.exe -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py` 得到 **70 passed，1 依赖弃用 warning**；`node --check web/app.js`、`git diff --check` 均 exit 0。这些是项目兼容检查，不证明 B&H 读取或 YouTube 视频能力。

真实 AGY 复测与私人证据保留在原试验 worktree。该 worktree canonical finish 实际记录 Git/Notion SKIPPED，原因 TASK_DELIVERY_NOT_AUTHORIZED；其本地 SUCCESS 回执不代表发布。未改写该回执或扩大授权。两份正式文档转交已配置授权的主项目目录，在现有任务分支 codex/evidence-photography-atlas 通过本轮最初编辑前已启动的 root 事务交付；仅新增这两个文档，保留主项目预先存在的所有未提交改动。未合并旧试验分支或重捕先前改动的基线。最终实际 checks、Git/Notion 与远端 SHA 以 root canonical receipt 为准。
