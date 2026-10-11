# 《动作导演》独立来源阶段审计（2026-10-11）

范围：仅 ROOT 候选 `docs/research/photography-atlas/action-directing/FACTS.md` 与原始公开材料；最终网站、完整课程、AGY 润色及原始调用记录尚未交付，本文件不是整体验收 PASS。冻结的 JSON/MD SHA256 本阶段结束复核均保持相等；定向返工轮次 0。

## 实际取证

1. 本 Verifier 用 `view_image` 打开 ROOT 的七张截图，随后用独立 BrowserSkill Agent Window `ssdm`（Chrome instance `1f5bd99b`，tab `1775091526`）重新打开 [Lindsay 官方视频](https://www.youtube.com/watch?v=fG_XVo8YmhE&t=80s)。实际展开官方说明并读取三种手部指导方法。随后独立 seek 到 80 / 86 / 200 / 218 / 228 秒：五次均回报同一视频 `duration=287.781`、`paused=true`、`readyState=4`；五张截图全部再次用 `view_image` 打开。原始 argv、UTC 与返回值在 `source_capture_receipts.json`，截图为 `independent-lindsay-{second}.png`。结束已 `bsk session stop ssdm`。
2. 本 Verifier 用 web 读取 [Westcott Jerry 教程正文](https://westcottu.com/portrait-lighting-posing-techniques-an-in-depth-guide-with-jerry-ghionis)：署名、发布日期、五要素、姿势指导、单人、双人及摄影师移动机位部分（页面定位约 L18–106）。从正文图像链接核对两个精确 URL，再用独立 Agent Window `bdoa`（tab `1775091529`）打开两张原站 JPG，浏览器标明 1366×2048；独立截图 `independent-jerry-solo.png` 与 `independent-jerry-couple.png` 均已打开。结束已 stop `bdoa`。
3. 本 Verifier 用 web 读取 [Lindsay 署名 Rangefinder 正文](https://rangefinderonline.com/wedding-portrait/high-school-seniors-sports/lindsay-adler-bridges-worlds-fashion-posing-senior-portraiture/)：署名/日期、Add Movement、Don't Force、Clear Concept、Movement Techniques 1–3（页面约 L39–84）。本轮没有打开该文全部插图。

## 事实与边界

| 底稿项 | 独立观察/原文支持 | 结论边界 |
| --- | --- | --- |
| F1 01:20→01:26 | 两帧显示坐姿双手靠膝变为一手在脸侧，摄影师面对模特抬手示范 | 对应 URL 与帧独立复现；未逐音核验现场对白，不能用两帧证明路径全程或拍摄结果改善 |
| F1 03:20→03:38→03:48 | 桌后双臂交叠变为一前臂上抬、另一手靠近腕部；后帧头向/手指形态不同 | 底稿与实际像素一致；头向与手形共同变化，不能宣称控制变量实验 |
| F1 原作者方法 | 官方展开说明支持移动路径、放松手指与联想词三类经验方法 | 可称原作者说明，不可称本 Verifier 逐音听写或通用科学规律 |
| F2 长裙单人 | 两肘弯曲，一手近肩一手腰侧，手臂与躯干有局部空隙；裙遮住腿脚 | 支持轮廓观察，不支持承重脚、精确身体角度或摄影师当刻动机 |
| F2 双人 | 左前景侧脸闭眼，右后方人物可见眼睛；不同面部层次，脚和完整手不在画面 | 可以作为新场景判断照片，不能叫修正前的坏姿势 |
| F2 正文 | 官方合作教程确实描述镜像示范、保持姿势旋转、负空间及摄影师换角度 | 同一站点不是多个独立来源；60分钟视频本轮未完整观看；商品参数不成为本课必要事实 |
| F3 动作流 | 署名正文支持有概念的控制移动、基础姿势上转换、不强迫不合适姿势 | 中国漫展/宽袖/慢速替代仍为项目迁移建议，未获本源实拍验证 |

已核对材料包含两个独立摄影师的一手官方/署名方法；没有用作者数量证明结论适用于全部人物。当前 FACTS 中未发现已确认的高影响事实错误，无须为展示返工而制造缺陷。

## 实际失败与限制

- web 抓取 YouTube 返回 `Online fetch throttled`；仅改用项目既有合法 BrowserSkill，不修改权限或绕过挑战。
- 首次 PowerShell `bsk click @e11/@e35` 因未加引号返回 missing target；重新观察并引用 `@e11/@e35` 成功。初次截图脚本打印 emoji 遇 cp950 编码错误；原始说明已经落盘，改用现有 Python `-X utf8` 后完整截图过程成功。这些是取证执行错误，不是课程缺陷。
- 实际独立观察为五个暂停帧及两幅成片；没有连续观看整段 BTS、听写音频、下载视频或授权转载原图。
- 后续仍需检查最终课程是否保持以上边界、完整教学/新场景、真实 AGY 前后事实差异以及工程体验。用户试学/复拍效果仍 UNVERIFIED。

所有视觉截图及取证原文只在本 worktree ignored `.local/verifier/`，未提交 Git、未发布、未读取主人日用数据。
