# AGY 的只读 Chrome 通路

这是浏览器领域运行说明，不是基础 Orchestration Skill。使用已安装的 `browser-skill`、`tools/agy_browser_bridge.py` 和现有用户 Chrome；不安装新浏览器，不借用用户标签页，不切换账户或浏览器设置。AGY 自己调用桥接、读取文字并实开截图才算自主研究；ROOT 的冒烟测试只证明传输。

## 前检顺序

1. 检查实际 AGY/CC/BrowserSkill 版本与 CLI 参数，不照搬记忆。先确认模型入口当前能返回；原生 AGY JSON 是 `event` 和嵌套 `result`，CC 是 `type`。模型 API 错误与命令拒绝、网页 HTTP 错误分别记录。不可重试错误停在相应依赖；外部状态恢复后另开新会话，不覆盖旧记录。
2. 用 `BSK_AUTO_START=0` 查询现有 `bsk status --json`、`bsk browsers --json`。按已确认的用户 profile 实例显式绑定；如果实例映射已失效，先按 browser-skill 核对，不猜测另一浏览器。保留共享 daemon，不重新启动它。
3. ROOT 在项目 `.local/agy-browser-policy.json` 准备本任务策略：`browser_id`、`browser_name: "chrome"`、有限的 HTTPS `allowed_urls`、现有 `bsk_path` 与本机 `evidence_root`。证据根目录须已存在。策略不含凭据，仍不提交 Git。新来源由 ROOT 在已有用户任务授权范围内核对并更新策略；Agent 不能用 CLI 覆盖策略文件。
4. 查看脚本、策略和所需材料读取路径，预先覆盖完整的有限依赖。保留 AGY 设置原始字节，精确增加固定脚本命令和相应读路径/来源域名；整份 JSON 对比证明无关配置不变。Windows 对某些命令使用完整原始命令匹配；本机含空格的引号路径前缀授权未生效，改为有限的完整 `command(<exact raw command line>)` 后实际预检成功。逐字保留引号、斜杠、参数和空格，每个新输出目录也是新的有限规则。禁止 `command(*)`、`command(bsk)`、全部 Python、`read_url(*)` 或跳过权限。域名 `read_url` 与桥接的精确网址白名单不是同一粒度。匹配边界见 [AGY 官方 CLI 权限文档](https://antigravity.google/docs/permissions?tab=cli#cli-cross-platform-command-matching)；本机实际工具事件仍是最终依据。
5. 在派发前记录脚本/策略内容哈希、PID/UTC/argv/worktree/criteria 哈希。运行过程中不改它们。Agent 的提示词必须允许实际运输所需的限定命令；不要要求 CLI 浏览同时禁止全部 shell。

## 可复用命令

从项目自己的 Python 运行；AGY 的固定命令授权应匹配已验证的真实 argv。下面的实例与网址是参数占位，使用本次实际确认的值：

```text
python "<absolute-project>/tools/agy_browser_bridge.py" preflight --browser-id <confirmed-instance>
python "<absolute-project>/tools/agy_browser_bridge.py" capture --browser-id <confirmed-instance> --url <exact-allowed-https-url> --out-dir "<private-evidence-root>/<new-attempt>" --scroll-y 650
```

生产 CLI 没有 `--policy` 或任意 bsk 参数。桥接只执行自身固定的状态检查、Agent Window 创建、导航、观察/HTML、可选滚动、截图和自己的会话清理。拒绝错误实例、未知/重叠会话、版本不兼容、范围外网址/输出、已有输出目录和策略覆盖。导航最终地址需要核对，未知不能按种子网址推断成功；证据写失败和清理失败都不许返回成功。

AGY 需要等待实际命令完成，不能把“返回 CommandId”当完成，也不能重启已有成功 attempt。返回的 PNG 必须通过图像查看工具实开；仅看到路径、DOM 或图片 alt 不算视觉研究。观察深度、图像定位、版权与无法确认的内容写入研究材料；视频时间码仅在实际看过并核对视频时填写。

在前检阶段按本次观察目标准备有限取景命令，不能把统一的 650/1250 滚动量当作所有网页的图片定位。顶部人像需要 0 起点；正文或下部细节另选明确范围。截图未含脸部时，记录未观察，不解释脸部光线。补充新的观察目标须有新输出目录和对应精确命令授权，保留之前的裁切证据；这是补齐领域材料，不能替代已失败的代码回归或增加代码返工次数。

## 验收与恢复

- 调用前后核对限定实例、策略/脚本哈希及整个配置 JSON；原生 AGY 可能改写 JSON 排版，字节变化和语义变化分别报告。
- 原始 tool events、来源观察、截图、配置备份和失败产物留在 `.local`；正式报告只保存可公开的来源、摘要和证据索引。命令成功只证明运输，研究结论另由独立 Verifier 核对。
- 页面拒绝、登录/验证码/权限待批准、模型入口失败保持可见；不反复重试挑战、不导出 cookies、不切换通路绕过拒绝。ROOT 只在明确的授权修复依赖完成后启动新会话。
- 回滚必须核对原备份哈希和完整当前 JSON 恰好等于原设置加本次规则；有后续无关变化就拒绝覆盖。先预演，再按用户授权执行。不恢复代理、账户或浏览器状态，因为本流程不修改它们。

当前实验的实际结果和保留失败另见 `AGY_BROWSER_REPAIR.md`。两次受控复用不能证明任意来源、视频能力或长期无人值守稳定，也不构成全局安装许可。
