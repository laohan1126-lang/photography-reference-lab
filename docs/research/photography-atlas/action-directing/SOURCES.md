# 《动作导演》来源、读取者与证据边界

本轮取证日期：2026-10-11。作者姓名、搜索摘要和 Agent 的 SUCCESS 均不作为内容核验。具体观察与项目推论见 [FACTS.md](FACTS.md)；课程只使用下述已核验范围。

| 一手材料 | 实际读取者与范围 | 可以支持 | 不能支持 |
| --- | --- | --- | --- |
| [Lindsay Adler 官方手部指导视频](https://www.youtube.com/watch?v=fG_XVo8YmhE&t=80s) | Codex：正常浏览器打开官方频道页面及展开说明；实际抽查 01:20、01:26、03:20、03:38、03:48 等画面。时长由页面 video DOM 读取为 287.781 秒；不是连续完整观看或逐音听写。 | 01:20 到 01:26 的手部位置和示范变化；03:38/03:48 手与头部同时变化；作者说明中的移动、放松及联想提示。 | 成片前后改善、单变量因果、精确器材、未经核对的现场对白或作者动机。 |
| [Jerry Ghionis / Westcott 官方合作教程](https://westcottu.com/portrait-lighting-posing-techniques-an-in-depth-guide-with-jerry-ghionis) | Codex：实际读取 Posing Tips That Make Every Shot Count 及对应人物段落，打开单人长裙、双人近景原图并检查像素。页面标注 2025-07-14；长视频未观看。 | 原文陈述的示范、转向、轮廓空隙及摄影师移动；两张真实成片的可见关系。 | 对应实际口令、调整前的错误照片、隐藏的承重脚、拍摄动机或控制实验。官方合作不等于独立转载许可。 |
| [Lindsay Adler 署名的动作流文章](https://rangefinderonline.com/wedding-portrait/high-school-seniors-sports/lindsay-adler-bridges-worlds-fashion-posing-senior-portraiture/) | Codex：实际读 By Lindsay Adler / 2017-09-29 的 Add Movement、Clear Concept、Movement Techniques 1–3 等正文；未逐张核验全部插图。 | 作者介绍基础姿势后的受控移动、动作与概念的关系及不强迫不适合的姿势。 | 中国漫展、宽袖服装或本课慢动作练习已被实测；与视频是同一作者，不能算第三位独立摄影师。 |

## 视频与图片复核索引

视频的 01:20/01:26 用来观察从膝部到脸旁的手部路径；03:38/03:48 用来提醒头、手可能同时改变。未观察连续段落中的每一帧，不把两帧之间发生的一切补写出来。官方说明中的 `ballet fingers` 和 `wiggle their fingers` 是页面原文短语，未认证为逐音核验的对白。中文口令是本课设计。

两张图的地址来自原页实际 DOM，未猜测高清 CDN：

- [单人长裙原图](https://westcottu.com/wp-content/uploads/Portrait-Lit-from-the-Front-Using-One-Ice-Light-3-on-a-Boom-Arm.jpg)：浏览器 natural size 1366×2048、complete=true。肩附近和腰侧的手、弯肘与局部空隙可见；裙内腿脚不可见。
- [双人近景原图](https://westcottu.com/wp-content/uploads/Studio-Couples-Portrait-with-Two-Ice-Light-3-Bi-Color-Lights.jpg)：1366×2048、complete=true。前后脸部层次、前景闭眼和后方可见眼睛可核对；脚与完整手不在裁切内。保护/对峙任务是课程新假设，不是原照片的角色身份。

原始浏览器截图存放于 gitignored `.local/action-directing/sources/`；没有下载原视频。截图已由 Codex 实际打开，独立复核范围另见 ACCEPTANCE.md。媒体 registry 与 CSP 只允许这两条精确原图 URL；远程展示仍依赖原站和网络，失败时保留观察说明与出处。`rights.allowed=false` 表示未取得再分发许可，不提交原图、商业视频或私人截图。

## AGY 的真实研究范围与限制

真实进程 `agy-research` 使用既有 AGY CLI。它调用 `read_url_content` 读取官方 YouTube 地址，再两次读取工具生成的 80 行、1,286,122 字节页面文件。该行为证明读取了页面内容，不能证明播放视频、查看像素或理解完整教学。随后 `read_url_content` 请求 Rangefinder 被既有权限拒绝，Headless 无法询问；最终 CLI exit=0、status=SUCCESS 但 response 为空，未写出 RESEARCH.md/RESEARCH.json。因此首次 AGY 研究没有可供认证的事实结论，也不能编造“抓出 AGY 错误对白”的故事。

Codex 使用现有合法公开浏览器及公开原文完成必要核验，读取者归属如上。没有扩大 AGY 全局权限、使用 skip-permissions、绕挑战、换供应商或反复重试拒绝站点。ePHOTOzine 仅用于找到实际官方视频链接，不作为教学一手依据。错误/不可用的初始发现 URL 和通用 Web 图像超时没有转成事实；在正常浏览器中成功打开的原图则保留其真实读取结果。

AGY 最后编辑使用 Codex 已核验的本地完整底稿，属于表达编辑；实际调用、成功或失败以及前后文本见 AGENT_COLLAB_REPORT.md 与 AGY_POLISH_DIFF.md。不能把这一阶段反记为 AGY 自主获得原始资料。

## 教学迁移边界

本课有关信件、宽袖、厚手套、假发、拥挤场地、仪器、重道具及十分钟练习的指导句是项目建议，需当事人确认舒适度、服装限制和场地可用性后复拍。没有附加拍摄参数、精确关节角度或人体力学证明。工程验收与实际学会指导人物分开；用户试学和实拍仍待反馈。
