# V2 交互复核

复核对象：隔离预览 `http://127.0.0.1:18766/learning`（数据目录为 `.local/atlas-v2-qa/v2-data`），桌面视口 1440×1000、移动视口 390×844。未修改产品代码；旧状态并发复现使用独立 synthetic 数据。页面内容及截图均已实际查看。

## 交互核对

1. **三个入口均打开完整教学正文。** 三篇入口逐一打开，标题与正文相符；每篇 8 个目录章节均可见并可定位。入口 A 桌面截图见 [gateway-1-observe-1440.png](../../../../.local/atlas-v2-qa/reviews/gateway-1-observe-1440.png)。
2. **章节定位有效。** 三篇共 24 个章节按钮逐一点击后，目标章节成为焦点并滚入阅读区；入口 A 桌面转场见 [gateway-1-transfer-after-csp-1440.png](../../../../.local/atlas-v2-qa/reviews/gateway-1-transfer-after-csp-1440.png)。
3. **关闭与恢复保留上下文。** Escape 关闭后焦点回到原入口，页面滚动位置保留；再次打开恢复阅读位置与未提交输入。手动关闭按钮及切换重开也保持草稿。
4. **入口之间的草稿隔离。** 在入口 A、B 分别输入不同练习答案，切换往返后两份草稿均各自保留，没有串到另一篇。
5. **移动端可读与素材加载。** 390×844 下阅读器、章节目录和正文可用，无横向溢出；转场图片已等到真实解码完成（Wikimedia 响应 200、`naturalWidth=960`、`complete=true`）。我查看了最终截图：[gateway-1-mobile-open.png](../../../../.local/atlas-v2-qa/reviews/gateway-1-mobile-open.png)、[gateway-1-mobile-transfer-after-csp.png](../../../../.local/atlas-v2-qa/reviews/gateway-1-mobile-transfer-after-csp.png)。最初立即截图会捕获图片下载中的空白/局部画面；等待下载解码后画面完整，因此这属于截图时机，不是当前 CSP 缺陷。
6. **键盘焦点陷阱有效。** 在对话框内正向 Tab 14 次、反向 Shift+Tab 8 次，焦点始终留在阅读器内；Escape 后返回原入口。
7. **共享 revision 冲突及旧技能状态。** 并发复核曾发现 P2：另一页面更新技能备注后，阅读器保存返回 409 并刷新共享 revision；旧技能表单仍显示旧备注，而后续提交可能错误地把旧值作为新 revision 写回，覆盖并发备注。根因是刷新共享版本号并不代表技能表单已载入新字段。当前修复在 [learning.js](../../../../web/learning.js#L299) 保留字段加载快照，[冲突检查与显式重载](../../../../web/learning.js#L377) 会阻止旧表单写回并保留草稿。主代理报告定向回归 `test_gateway_refresh_does_not_authorize_a_stale_skill_form` 已通过：旧技能备注和入口练习草稿均保留，用户可显式选择“载入服务器版本（替换此技能的本页草稿）”。修复后没有发现该覆盖路径仍可发生。

## 验证边界

桌面 / 移动截图保存在本目录。三入口正文、章节、焦点、阅读位置、草稿切换和键盘陷阱来自真实浏览器操作。图片已确认加载且已检查最终像素截图。并发修复的专门回归由主代理运行并回报通过；我自己的 synthetic 扩展脚本在初始状态断言处退出，未将其失败伪称为应用回归通过。该脚本未写入用户数据。未审查整套学习业务以外的流程。
