# 私人部署与运维

## 本地优先

### Windows 主运行环境

日常桌面使用以 Windows 为主：仓库内 `start.bat` / `scripts/launch.ps1` 启动当前 checkout 的 Windows `.venv\Scripts\python.exe`，并把同一 checkout 的 `tools\collect_adapter.py` 注入 `LAB_COLLECTION_COMMAND`。Edge 与 BrowserSkill 也运行在 Windows，从而避免 WSL Python 再跨边界调用 Windows 浏览器。

Windows 启动器不会自动创建新的资料库。已有资料必须先恢复到一个 Windows 本地目录，再通过 `scripts/configure-windows-runtime.ps1` 写入 gitignored 的 `.local/windows-runtime.json`。运行时 PID/log 也只写入 `.local/runtime/`，不提交 Git。

从历史 WSL 环境迁移时按以下顺序执行：

1. 停止旧 WSL 服务，确认不再有进程写入旧 SQLite。
2. 在旧环境执行完整 `python -m ref_lab backup --output ...zip`。
3. 将备份恢复到一个新的 Windows 数据目录；不要让两个运行环境共用同一个 SQLite/WAL 目录。
4. 用 `configure-windows-runtime.ps1 -DataDir <目录>` 配置 Windows。
5. 运行 Windows `.venv\Scripts\python.exe -m ref_lab doctor`（带相同 `LAB_DATA_DIR`）并确认通过。
6. 用 `start.bat` 启动，再做 BrowserSkill 真实 Golden Path 和人工图片验收。
7. Windows 验收通过后才退役旧 WSL 正式数据目录；保留备份。

WSL/Linux 仍是兼容与开发路径，但必须使用独立数据目录。禁止 Windows 与 WSL 轮流打开同一个活动 SQLite 库。

默认 `127.0.0.1:8765`。第一次运行会在 `.local/access-token` 生成随机口令，读取命令是 `python -m ref_lab token`。不要把终端输出截图公开，不要将口令贴到仓库、Notion 或任务包。

`LAB_DATA_DIR` 应指向持久化目录；只存于浏览器或容器临时层是不可靠的。`LAB_PUBLIC_ORIGIN` 必须与访问地址的协议、主机和端口一致；换端口同时更新它，不能含子路径、用户名、查询参数。单所有者工作台不支持多人账号隔离。

## 域名部署

先完成 Codex 回归和真实素材权限审核，再部署。当前提交不会修改域名、DNS、GitHub Pages、账户权限或公开素材。

1. 配置自己的 HTTPS 反向代理与真实域名，所有 API 和图片走同一源。反向代理保留正确 Host，限制总上传体积与请求超时；不要直接挂载 `/assets` 或 `.local` 成为公开目录。
2. 用密码生成器建立至少 32 字节随机口令，通过 `LAB_ACCESS_TOKEN` 注入。不要把示例测试口令当生产密码。设置实际 `https://域名` 为 `LAB_PUBLIC_ORIGIN`。
3. 容器或服务器只对受控代理监听；远程绑定需 `--allow-remote` 且环境中显式设置口令。Docker 推荐 `-p 127.0.0.1:8765:8765`，再由本机 HTTPS 代理转发。
4. 数据卷属非 root 运行用户；应用提供 HttpOnly / SameSite 会话、CSRF、Host 检查、受保护图片接口和 no-store。它不是完整企业零信任产品；服务端管理员仍能访问本机数据。
5. 登录会话约 24 小时有效。改口令并重启可撤销旧签名会话。浏览器锁定仅清理当前界面/会话，不是对已下载图片的 DRM。离线 ZIP 会包含私人图片和可能的 EXIF，谨慎分发。

Python 不自动读取 `.env`。PowerShell 可用 `$env:LAB_PUBLIC_ORIGIN="http://127.0.0.1:8765"`；Docker 使用 `--env-file .env` 时，**将 LAB_DATA_DIR 改为 `/data` 或删掉该行以使用镜像默认值**，不要用示例里的相对 `.local` 覆盖持久化目录。

## 备份与恢复

```bash
python -m ref_lab backup --output ../reference-backup-20260925.zip
python -m ref_lab doctor
python -m ref_lab doctor --repair-derived
```

备份目标已存在会拒绝覆盖。SQLite 使用一致快照，图片按快照引用导出；密钥与浏览器档案不包含在内。恢复：停止服务，把**自己的可信备份**解压到全新空目录，指定为 LAB_DATA_DIR，运行 doctor，生成/配置新口令后启动。不要覆盖运行中的数据库，不要把不可信 ZIP 当备份直接解压到服务器。

doctor 检查数据库、外键、原始哈希和展示图。可从完整原始文件重建展示图，但不会修复或伪造缺失/损坏的原始图；受影响确认会撤回，修复后仍需核对。新增数据库版本必须写迁移，不能直接把 user_version 改成最新版。

## 浏览器与外部服务

采集器只在自己的本机运行；不要在公网服务器暴露 CDP，也不要复制整套个人浏览器 Cookie。账号登录由用户正常完成；出现验证码/访问限制停止。平台 DOM 或下载策略改变时应调整采集器并回归，不探测隐藏端点。

OpenAI API 和 Notion 是可选功能，默认未连接、未调用。显式命令才能发起。生产环境不建议把外部 API 密钥交给浏览器；本版仅从本机执行器环境读取。外部服务真实可用性、授权与计费需单独验证。

## 未授权图片与公开仓库

现有公开 Git 历史中的图片不会因新系统登录保护而撤回。新系统不自动把收集图片推到 Git。需要另行审核已有公开素材，私人收藏、署名和非盈利均不自动代表具有公开转载授权。
