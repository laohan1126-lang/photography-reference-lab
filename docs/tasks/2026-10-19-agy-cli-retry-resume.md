# CLI真实原因、有限重试与25张原候选续核

用户要求：“先查清楚CLI报错原因，把有限重试和断点续跑修好，再让agy继续核验剩下25张，不要重新搜，不要你接管，也别放宽角色核验门槛。”

起点分支codex/learning-loop-v1-20261018、HEAD10ed862；保留全部已有改动。事务01a14fa3-e866-7e43-b46d-19bf52e62818先于首次编辑启动。只在仓库.local/agy-resume-20261019及正式.local/collection-resumes隔离保存新状态；旧39图/14结果/12通过名单及原始失败文件不改，正式库/K/I/M/X不写。历史896ec94隐私停止仍有效，不commit/push/Notion/合并main。

## 已查明原因与反补丁设计

对应失败文件attempt-d6f9daa48deb7eaf.json的记录时间为2026-10-19 00:14:10 JST；CLI归档log/cli-20261019_001405.log含原工作目录46f59fd7be8e4564b2d10e7f20f29e5e，登录已applyAuthResult，loadCodeAssist请求多次EOF，随后模型配置载入失败并把gemini-3.8-flash-medium误报为未知型号。日志中的启动阶段“not logged in”在成功调用也存在，不能据此让用户重登；这次证据是模型目录加载的连接EOF，不是已证明型号不存在或角色识别能力不足。更底层哪一网络跳点中断仍无法从日志确定。另有旧Hook引号失败噪声，在成功调用也出现，不以此解释本次EOF，不扩大修改全局Hook范围。

复核前两轮失败：根因修在传输重试与状态保存边界，不改提示词来让角色更容易通过，不新增角色/站点特例。原角色/图像门槛accepted、parse_agent_stream、trusted_images、CollectionVision及_review_once提示词保持原实现。参考仍用原两张可信原图，不重新搜资料，不用Root新结论给AGY。

Python现有CLI/worker：改verified_collection.py的run传输与安全诊断、collect_verified.py的失败隔离与--resume入口，新增针对测试；复用atomic_write/save与现有候选schema。最多3次/同一prompt（首次+2次重试），仅EOF/连接、5xx、短时429/超时等执行故障，延迟2/5秒；身份uncertain/mismatch、错误版本不是重试理由。登录/长期额度/预算/越界证据明确暂停；单项其他失败记录后继续，不把一次临时错误扩大为后面全停。尝试在启动前落盘记账，中断后预算不清零，已完成结果可复用，原图/条件/参照变更拒绝旧进度。

恢复仅原目录.local/collection-runs/agy-flowfix-maki-20261018/46f59fd7be8e4564b2d10e7f20f29e5e的25条review=null，前14条不再调用。原摄影调用预算60已用15，续核最多45次CLI摄影尝试、每图最多3次，49分钟单次续跑时限；全部25都要尝试，不因总通过数达到30就截断。先跑失败回归再实现，冻结后执行；任何剩余阻塞如实保存，禁止Root接管/补齐/调审美或排序。仅事后检查结果，不把本角色继续开发说成独立泛化。

## 回归、首次续跑的范围配置与恢复

8项新增/更新的行为检查在修改前失败；第一版105项及补充边界后108项通过。断点为原候选/context/参照与来源文件哈希绑定，结果逐项原子保存；锁随进程退出释放，实际CLI尝试在启动前原子记账，合法成功回执可在输入不变时复用，失败重启不清预算。身份不符/uncertain不是执行重试理由。

第一启动发现传输成功不等于读图：新状态目录与旧图目录分开，CLI拒绝外部工作目录read_file，4次返回SUCCESS但带denied_actions、无实际读图，全部被原校验挡住；第5次在处理中由Root暂停本轮自有进程树。没有新增有效预测或改写旧14条，5次尝试全部计账保留。这是续跑工作范围配置缺口，不把拒绝当模型认错，也不反复重试权限拒绝。

CLI本机help明确支持--add-dir；修复仅对本次已明确授权的原图父目录、参照图片父目录添加该官方工作范围参数，保留--sandbox、plan、实际目标及全部参照读取检查；不用dangerously-skip-permissions、不改全局授权/认证/代理。新增权限拒绝fatal不自动重试、工作范围只含输入目录的回归后，110项相关检查通过（37.70秒）。原freeze.json保留，范围修复另存freeze-workspace-fix.json；提示词/schema/准入函数哈希仍与首次修改前相同，旧尝试不清零，不改变验收条件。

随后从同一断点继续，首个原报错图片真实读取成功并由AGY通过（继承历史失败次数，本prompt第三次总尝试）；接着处理剩余24张。运行中新搜索0，旧14条跳过，后续结果待完整保存后报告，不用这次恢复宣称独立泛化或审美提升。

## 最终实跑与幂等验证

AGY已完成剩余25/25，原14条未重跑，总39条均有有效视觉结果，执行待处理0。本次新增12张通过，合计原12＋新12＝24张，未增删、重排或Root补齐。新增未通过13张：模型判角色不符9张、非独立摄影/插画3张、真人身份不确定1张；这些是模型判断，不是人工准确率，unknown未改match。全部仍用原两张参照/原摄影提示词，没有任何摄影或参照新搜索，没有Browser或补证研究阶段。

实际续核1814.980秒（约30分15秒，含首次范围配置中断和恢复），共32次新摄影CLI启动记账：25条有效回执、2次网络EOF、4次权限拒绝、1次被暂停中断；历史原失败另保留，不重置。每prompt含历史最多3次，45次新调用预算未超限。两次同类网络EOF都在有限重试后成功产出结果，后续图片照常进行，未再由单次临时错误全停。没有因为达到20/30张就提前停止核验原25张。

真实入口：http://127.0.0.1:18777/ 。24张原字节图，包含12张原已通过和12张新通过的明确标记；XHS12＋Pinterest12，保留原帖链接，原摄影者未全部核实。BrowserSkill独立无焦点会话验证24/24图片加载、无评分表单，验证会话已关闭；旧18776及旧12张报告保持原样。正式库没有导入这些新结果，不写K/I/M/X。

运行结束后保留evaluated-manifest.json/evaluated-audit.json及原评估freeze。收尾冷启动记账边界补充：所有CLI启动（包括SUCCESS但拒绝/校验失败）均迁入历史账，已有绑定且属于待核SHA的成功回执可复用，不迁入无绑定的旧注释；初始化输入提交标记放到证据搬运完成之后，避免中断留下半个断点。此补充未修改任何角色规则或本次25条预测，112项相关检查通过（27.97秒）。最终版本与原实际运行版本分开保留，不后改本次视觉结论。

再次实际执行同一--resume命令：0新增CLI尝试、0搜索、39条判断全部跳过；全部attempt文件字节、visual-audit字节及候选值/顺序不变，仅本轮自己的结果包batch元数据重建。原14个已完成SHA从未成为新CLI实际目标读取；原始源目录与原39图仍原样。详见.local/agy-resume-20261019/idempotence-proof.json与idempotent-output-freeze.json。

可复跑命令（在仓库根目录，原输入不变时会跳过已完成项）：

```powershell
.\.venv\Scripts\python.exe -X utf8 tools/collect_verified.py .local/agy-recall-flow-fix-20261018/job.json .local/collection-resumes/agy-flowfix-maki-20261018/46f59fd7be8e4564b2d10e7f20f29e5e/result.zip --resume .local/collection-runs/agy-flowfix-maki-20261018/46f59fd7be8e4564b2d10e7f20f29e5e
```

## 事后抽查与局限

只在结果冻结后打开新通过首/中/末3张和新未通过真人项按SHA排序最前2张；没有向AGY提供Root意见或重新判断要求。3个通过样本有圆窗/逆光/包带姿态、单腿屈膝展开手臂、场照中手指与嘴唇和道具层次等可借鉴内容，未见明显错角色；两张拒绝样本的黑双马尾红眼与另一作品金短发红西装组合支持非目标，未见明显误拒。这不是24张全部准确或13条拒绝全正确的证明，也不是人类喜好评价。

AGY原文仍存在过满解释：屈膝站姿不能据此断定实际跳跃，背景虚化不能单独证明大光圈，抵颌措辞不如指尖近唇准确；若干官方服装名称没有同版一手资料核定。只作单独附注，名单/原说明/旧14条全部不改，不宣称审美训练成功。具体另一角色名仍作为AI预测，不升成人工事实。

## 保护与正式交付

原937参考、1177原图、2993旧实验文件保持一致，原冻结输入/评价/前轮输出未改，quick_check=ok。accepted、parse_agent_stream、trusted_images、CollectionVision schema与_review_once摄影提示词哈希前后完全相同；角色/服装/实际读图门槛未放宽，未换模型、未改排序/审美/全局代理/认证/Hook/启动器/数据库/前端。仅原图和参照父目录通过官方--add-dir加入本次工作范围，不用权限跳过参数。日志仅保留安全分类/退出码/摘要哈希，不复制原始全局CLI日志/凭据。

实际改动：verified_collection.py的安全诊断/有限重试/计账/同输入成功回执复用，collect_verified.py的错误隔离/原子续核/锁/来源元数据/CLI入口，新增test_collection_resume.py及更新相关测试，README/WORKER_PROTOCOL/本任务/CURRENT。实际测试命令为C:/Users/Dell/AppData/Local/Programs/Python/Python312/python.exe -X utf8 -m pytest -q tests/test_collection_resume.py tests/test_verified_collection.py tests/test_visual_references.py tests/test_automatic_references.py tests/test_collection_runner.py tests/test_imports_jobs.py；没有安装新依赖。失败与中断、110及112项回归、原始模型结果、32次尝试、原冻结和幂等证据全部保留.local。角色/摄影新判断均由原gemini-3.8-flash-medium完成，Root只维护传输/进度及事后抽查。

分支codex/learning-loop-v1-20261018，HEAD10ed862；git diff --check通过、暂存区为空。历史896ec94缓存隐私停止继续，canonical Publisher记延期，未commit/push/Notion/合并main。工程修复和已授权25项续核完成；整体视觉准确率/个人审美/新角色独立泛化仍未验证。停止本轮，不再扩搜、重跑已完成项或自动加第三模型。
