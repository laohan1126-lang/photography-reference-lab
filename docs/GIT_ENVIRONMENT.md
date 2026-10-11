# Windows Git 的现有桌面代理

2026-10-11 本轮失败发生在 canonical Publisher 的 `git_ops.run`：`git -C <worktree> ls-remote --heads origin refs/heads/codex/action-directing-module-upload-20261011` 返回 128，错误为 `Recv failure: Connection was reset`，尚未进入 commit 或 push。Publisher 没有清空环境或换 HOME；终端和 Publisher 都使用 `D:/program files/Git/cmd/git.exe`、账户 Dell、`USERPROFILE=C:/Users/Dell`，无 `HOME` 或 `GIT_CONFIG_GLOBAL` 覆盖。

用户当前使用桌面 iKuuu。Windows Internet Settings 的代理为 `127.0.0.1:12002`，运行中的 `iKuuuVPNCore` 确实监听这个 loopback HTTP 端口；Git 原先没有对应代理配置，不能依赖桌面系统代理自动传入 Git。先用临时、仅 GitHub 范围的参数取得真实远端 SHA，再将相同配置持久写入 `C:/Users/Dell/.gitconfig`：

```powershell
git config --global http.https://github.com.proxy http://127.0.0.1:12002
```

新 `pwsh -NoProfile` 和新 Python 导入实际 Publisher `git_ops.run` 均无需临时参数或代理环境变量，读取同一配置并成功取得 `e6c0eb6f7238443f5cb89ea443997b104bc8888c`。后续真正的 push 与远端 SHA 以本任务 Publisher receipt 为准。没有更换 remote、凭据、TLS、系统网络或代理软件设置。

日常保持 iKuuu 已连接。配置、软件或端口未变时无需重新全量排查；仅在环境改变或命令失败时查看相关边界：

```powershell
git config --show-origin --get-all http.https://github.com.proxy
git config --get-urlmatch http.proxy https://github.com/laohan1126-lang/photography-reference-lab.git
git ls-remote --heads origin
```

若 iKuuu 更新了本地端口，从 Windows 实际代理配置和监听进程重新核对，先局部测试再修改这个键。撤销本轮添加的 GitHub 专用代理：

```powershell
git config --global --unset-all http.https://github.com.proxy
```

不会因此改变既有 Git 凭据配置。此文件不包含订阅、令牌、完整代理配置或私人数据。
