# Tunnel Prechecks Hardening & Auto-Heal Fix — 2026-10-04

## User Intent and Boundaries

- **User report**: "怎么手机端又连不上了"
- **Observable Acceptance Criteria**:
  1. 手机端重新访问 `https://ref.koshikorato.top` 恢复正常连接，不再报 HTTP 530 / 无法连接。
  2. 查明机器重启/后台守护恢复时 Cloudflare 隧道未就绪的真实根因。
  3. `scripts/ensure-external-services.ps1` 能够在开机/服务检查时自动拉起隧道且不再被 pre-check 硬性阻断。

## Root Cause Investigation

1. 机器重启或后台守护重启后，本地后端服务正常监听 18765。
2. 然而 Cloudflare 外部访问报 HTTP 530（Tunnel not connected）。
3. 深入调试 `cloudflared` 启动日志发现：
   `cloudflared.exe` 在启动时默认执行连通性预检（`precheck`），向 `region1.v2.argotunnel.com` / `region2.v2.argotunnel.com` 发送直接 UDP/QUIC 探测。由于国内网络对该特定 Argo 探测端口阻断，触发了 `hard_fail=true`，导致 `cloudflared` 进程直接中断退出，无法进入 HTTP/2 正常建连阶段。
4. 加入 `--no-prechecks` 参数后，`cloudflared` 直接建立基于 Anycast HTTP/2 的端点连接（lax01, lax09 等节点），瞬间完成注册上线。

## Implemented Changes

1. **`scripts/ensure-external-services.ps1`**:
   - 在 `Ensure-CloudflareTunnel` 的 `cloudflared` 启动参数中加入 `--no-prechecks`，防止因冗余的网络探测失败而中断隧道建连。
2. **Runtime Verification**:
   - 验证后台守护正常连接到 Cloudflare 边缘节点。
   - 验证手机端通过隧道访问 `/health` (200 OK), `/api/session` (200 OK, 免密模式有效), `/api/projects` (200 OK)。
