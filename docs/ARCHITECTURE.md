# v0.3：个人参考库的数据与交互契约

## Dot 待筛摄影参考（2026-10）

数据库 v4 增加独立的 `study_candidates`，用稳定的 Dot 编号指向内容寻址 Asset；兼容副本仍只属于同一作品。该入口没有项目父键，也不建立全局 Inspiration。批次导入保存原记录、来源、限制和 Dot 原文，关键词主题标明为未视觉核验的文字建议。人工状态及笔记单独保存，带 revision 冲突保护；再次导入核对原图/兼容图哈希和 Drive 文件 ID，不覆盖人工编辑。原图 Asset 受到清理引用保护。迁移前的 SQLite 备份与批次导入前的私有备份分别保存，现有 Reference、Inspiration 和项目数据不重写。

人工筛选理由 `study_reasons` 与 Dot 的 `suggested_topics` 分字段保存。允许多选 `composition`、`pose`、`lighting`，对应“构图可学 / 姿势可学 / 光线可学”；旧记录读取为空列表。修改理由不改变候选的待筛状态、个人备注、角色引用或全局收藏，继续按 revision 拒绝过期编辑。

## 选择的改动范围

保留 FastAPI、SQLite WAL、内容寻址原图、策略门槛、单图资料卡、离线导出和既有权限系统。没有新框架或额外付费依赖。新增独立收藏与发现/观察记录，局部重构前端浏览器，而不是重写正确的存储层。

- `service.py`：Web、CLI、迁移、执行器共享的事务与用例层。
- `db.py` / `migrations.py`：版本、事务、迁移前一致性备份。
- `catalog_data.py`：发现上下文、资产观察、全局收藏记录。
- `storage.py`：按收到的字节 SHA-256 去重；原图不变，另生成预览和缩略图。
- `policy.py`：现场卡门槛；未知不通过，客户端不能声明已验收。
- `acquisition.py` / `export.py`：Agent 检索契约、独立任务包与生成的 JSON Schema。
- `imports.py`：不信任候选包自称事实，校验任务、图片、路径、大小和 revision；schema 3 的候选视觉预检仍作为 Agent prediction 保存，不提升成人工事实。
- `recycle.py`：显式、延迟、带活跃引用检查的本地清理。
- `web/`：稳定单图工作台、全局导航、单步制卡入口和持久化浏览定位。

## 四类概念不能混在一起

**Asset** 是独立的文件资产，表 `assets` 不属于角色。收到的字节不代表作者相机原片或平台最高分辨率。精确重复合并；近似重复仅提示，不自动删除。

**Discovery** 记录为什么、在哪次任务、用什么词找到这张图：原发布信息、搜索入口、任务、导入别名、发现意图和当时项目快照。`discoveries` 可以有多次发现。旧来源保留，不能从当前角色要求倒推当年的搜索条件；旧快照未知明确记为 `legacy_context_unknown`。任务要求冻结，不因之后改项目而悄悄变化。

**Observation** 是绑定实际 `asset_sha` 的图像观察，`asset_observations` 保存观察及产出者历史；来自实际 review，不从标题、意图或旧说明生成。`character_match` 不放进通用资产事实，因为它回答的是与某个项目角色的关系。观察存在不等于正确、也不等于用户确认，界面仍允许修正。

**Reference** 保留现有 `(project_id, asset_sha)` 唯一使用关系，以及本项目的选择、偏好、角色适配、review、卡片、确认与复盘。候选阶段的 `preflight` 也是项目使用上下文：保存实际图片的 modality、相对当前角色的 identity prediction、置信度、可见证据与 producer，并与 K/I/M/X、现场卡 VisualReview 分开。非真人 modality 或 mismatch 默认只进入可恢复的过滤视图；uncertain 不强行 pass。为兼容不把既有卡片全部拆表；这是项目使用视图，不是“图片语义属于这个角色”。

跨项目复制/转移操作只复用 Asset：目标项目新 Reference 默认 pending，并清空搜索确认、角色 preflight、review、card 与 acceptance；如果目标项目已经有同一 Asset，则保留目标自己的旧选择而不是覆盖。转移/“从当前项目移出”使用 `detached_at` 标记 source Reference，和 X/reject 分离；detached 引用从正常项目流与现场卡导出中隐藏，但完整保留历史，可从项目回收视图恢复。

**Inspiration** 是独立的全局收藏表，直接引用 Asset，没有项目父键，也没有伪造的“全局角色项目”。一个资产一个收藏记录，保留自己的标题、来源和审美笔记。不同项目的历史偏好聚合为带上下文的笔记，不让后来的项目偏好覆盖前面的判断。来源项目仅是溯源线索。移除收藏、项目淘汰互不级联。

`Note.project_id` 可空，新笔记默认独立；旧项目笔记保留并统一浏览。去重指纹不随编辑变化，重复导入不覆盖已修改正文。Event 只追加业务审计，不宣称能防数据库管理员篡改。

## 迁移与兼容

数据库 `user_version=2`。打开 v1 时通过 SQLite backup API 保留 WAL 内已提交数据，再用 `BEGIN IMMEDIATE` 原子迁移；失败回滚，不出现半套表。旧项目、资产、别名、任务、笔记和引用不删不换 ID，旧 choice/revision/review/card/acceptance 不重置。旧 keep+inspiration 聚合为全局收藏；旧 reject 没有可证明的前一选择，恢复默认 pending。没有图的旧收藏保留元数据，不配猜测图片。

新增发现/观察表是补充，不把旧图注提升为事实。只有 review 绑定当前图片哈希时才迁入观察历史。正常重启不重跑迁移；用户后来移出的全局收藏不会被旧 lane 再次偷偷收藏。候选包 schema 1/2 保持导入兼容且不伪造视觉证据；当前任务导出 schema 3，要求每个新候选携带实际逐图得到的 modality + identity preflight。数据库仍是 user_version=2，本次没有为了这些 JSON 字段增加破坏性表迁移。

所有可编辑实体使用 revision 检查，冲突 409 而非后写覆盖。自动备份只有数据库；完整备份需要 CLI，使用一致性快照和对应原图。备份与清理共用写锁，避免快照列出正在被清理的文件。已明确清理的文件只保留元数据，doctor 区分有意清理和意外丢失。

## 稳定图片浏览器

只有切换项目/视图时挂载图片工作台。点击缩略图、上下张只更新活跃图片和右侧信息，不重建缩略图。成员变化使用 reference ID 为键原位协调 DOM；保持可见锚点，必要时仅水平微调，以让当前图可见，不滚动祖先页面。

淘汰响应成功后立即移走本项目成员；**先选相邻存活 ID 再渲染**，不能中间退回第一张。下一页属于明确列表变化；跨页导航、自动下一张和刷新定位有回归。每页 60 张，不全量渲染数千张图片。异步读取有 epoch/scope 检查，写入期间禁重复操作与切换，过期写入不自动前进。URL hash 保存项目、视图、筛选、页码及当前 ID；用户选择本身始终来自数据库，不以 localStorage 充当数据库。

第一层只显示 K 角色参考 / I 通用灵感 / M 待定 / X 淘汰。高级信息放折叠区。预检过滤不是第五种人工选择：默认候选流隐藏 `preflight_filtered`，独立“已过滤候选”视图展示理由并允许人工恢复。项目本地还有一个非持久化选择篮，用于批量复制/转移和沟通板导出；它不是新的筛选状态。项目回收视图同时显式展示 X/reject 与 detached project-use，恢复动作按各自语义执行。全局视图不跟随当前项目变更。

## 模特沟通板

沟通板是只读交流产物，不是现场卡、审美画像或新的筛选状态。用户从当前项目显式选图并决定顺序/短备注；服务端重新校验 Reference 仍属于当前项目、未 detached/淘汰、原图完整。渲染使用原始 Asset 的显示方向并 `contain` 到卡片框，不做破坏性裁切或 AI 重绘。每页最多四张：1–4 张返回单 PNG；更多图片按四张一页生成 PNG 并打包 ZIP。导出只追加 `contact_board.exported` 事件，不改变 K/I/M/X、preflight、review 或 acceptance。

## 制卡状态与门槛

展示阶段：候选 → 角色参考 → 等待/执行分析 → 分析结论或卡片草稿 → 用户确认现场卡。不是一条必须走完的流水线，允许只收藏、只分析、不生成卡。

“制作现场卡”创建单张分析任务，冻结要求、图片哈希与 revision；任务包带一张独立图。支持底层多条任务，但每个结果仍绑定自己的 reference，绝非多图合卡。正常浏览器路径不调用模型 API。相同快照和要求的重复点击复用等待任务，改要求/选择/图片后拒绝过期结果。部分导入更新完成 ID，下次任务包只含未完成项；全部结果导入才完成任务，结果仍只是草稿。

原现场卡策略继续要求：KEEP + field、原图完整、明确可用的真人独立图/动作/清晰度、没有关键未决疑点、明确角色适配（跨角色须允许）、可追溯来源或自有说明、当前项目上下文的完整卡片。用户在草稿检查页明确核对来源、安全与适用性，服务端再次校验后确认。修改图片清空选择/核验/卡，修改来源/选择/偏好/适配撤销确认，修改要求/器材保留旧卡但待复核。AI/搜索包永远不能写确认。

## 回收安全

项目本身的“删除”采用软归档：`Project.archived_at` 让它从正常侧栏/API 列表隐藏，项目引用、任务、笔记、事件及资产关系仍保留；回收入口可恢复。归档项目拒绝正常编辑、候选写入和新任务，防止隐藏项目继续被后台修改。共享 Asset、Global Inspiration 与其他项目引用绝不因项目归档被物理删除。

单张项目淘汰只改变 Reference，保存淘汰前选择和时间；恢复不自动恢复验收。项目间 move/remove 则只把 Reference 标记 detached，不改成 X，也不删除 Asset；恢复 detached 关系也不自动改变原 K/I/M/X。全局移除只改变 Inspiration.active。CLI `cleanup` 默认 dry-run、至少保留 7 天，明确 `--apply` 才删本数据目录的原图及衍生图。

任一未淘汰项目引用、有效全局收藏、笔记引用、未完成分析任务快照都会保护文件（失败任务也需明确取消后才可能释放）。只针对有明确回收记录的足龄资产；没有证据的孤儿不猜测删除。保留资产/来源/事件元数据并标记已清理；重导相同字节后才可恢复。不清理原 Git 历史目录或外部路径，不做定时后台删除，不支持通过网页执行不可逆清理。

## 摄影学习能力地图

`/learning` 使用独立研究产物构建的 `web/learning-atlas.json`，依次展开领域、模块和原子技能。`tools/assemble_photography_research.py` 应用显式聚类、来源资格与作者去重决定；`tools/validate_photography_atlas.py` 检查证据、先修关系和个人状态初值；`tools/build_photography_atlas.py --check` 防止页面数据与研究材料漂移。结构验证不证明摄影结论或用户能力。

`TUTORIALS.json` 保存技能配套材料；`tools/validate_photography_tutorials.py` 检查公开 URL、来源身份、精确技能映射和实际核对深度。推荐与正式研究证据分开，但都参与 bundle 内容指纹。来源分歧通过 `CLUSTER_DECISIONS.conflict_skill_ids` 显式关联技能，不因共享一本教材就跨主题附加；多作者位置保留全部来源。

学习页路由统一控制当前页面、筛选和导航起点，个人筛选写入浏览器历史。练习弹窗固定所属技能，历史导航不会改变保存目标；章节跳转保留技能路由。教程、训练与折叠研究依据采用连续排版，个人记录在桌面侧栏独立滚动，手机改为正常文档流。

`ref_lab/learning_state.py` 在 `data_dir/learning/` 单独保存修订号、本人状态、薄弱/重点、学习日志和原始上传照片。现有 API 中间件负责身份与 CSRF；更新必须匹配修订号，冲突返回 409。JSON 原子替换和进程内共享锁支持当前单进程运行，不宣称多进程写入协调。上传不自动提升掌握状态，不改参考库的 Asset、Reference、人工选择或图片事实。研究封面与专业案例也不能替代私人作品的视觉审阅。

## 摄影学习 V2：独立教学层

`GATEWAYS.json` 不替换技能树：每个认知入口显式关联多个现有 skill ID，独立记录教学来源、原始案例、图像许可及像素复核范围。构建器将课程与 `gateway_sources` 加入同一内容指纹；`validate_learning_gateways.py` 校验关系、章节、观察/对照/迁移活动与未提前使用的新案例。结构通过不等于原理、图像判断或教学效果通过，三类人工/Agent复核另有记录。

案例显示机制与转载许可分开：`source_remote` 的 `images` 引用原站公开的精确媒体地址，`rights.allowed` 不被改成许可；`licensed_remote` 仍要求明确许可。`source_summary` 记录中文转述、来源 ID、阅读定位和核对日期，在图下按需展开以保留观察题的节奏。`ref_lab/learning_media.py` 统一登记七案例的九个媒体地址，供构建校验和仅 `/learning` 文档的 `img-src` 共用；不开放其他 CDN 文件、脚本或 API 网络请求，不代理、下载或服务端缓存图片。失败状态保留要点、署名和原页链接；站内引用不保证离线可用或未来原站持续可达。

`learning-gateways.js` 负责阅读对话框、章节定位、原页焦点/位置和每入口草稿；主 `learning.js` 仍独占路由、身份、共享 revision 和写入协调。草稿只用 sessionStorage 保持同一标签页连续性；显式保存走 `PUT /api/learning-gateways/{id}`。迟到响应绑定发送时的入口，不能覆盖请求中产生的新编辑或其他入口草稿。409 保留本页草稿，明确加载服务器版本后再编辑。

### 简洁笔记与训练

`LEARNING_CONTENT.json` 是独立的静态内容层：`notes` 关联现有 skill ID、来源与真实媒体；`trainings.note_ids` 明确关联依据笔记，反向链接由界面计算。合法训练可引用跨技能笔记；未知、重复或悬空 ID 被 `validate_learning_content.py` 拒绝。新内容参与 bundle 指纹，原研究对象及 gateway 契约保持原样。本轮只深入补充比例专题；距离笔记关联光学/透视诊断的距离部分，不声称提供了桶形/枕形实拍对照。

`LearningContent` 是 `learning.js` 内独立 IIFE，只负责内容渲染、同页切换与教学图查看。私有写入继续由主 IIFE 负责；训练打开原日志对话框时仅预填标题和依据，用户显式保存，日志仍绑定打开时的技能。切换双区不改 hash、不重建个人表单，不提升能力状态。长版来源和原理移到可展开资料区。样式沿用已有 `learning.css`，避免旧运行进程的静态白名单缺少新文件。

`ref_lab/learning_content.py` 经 `preview_router` 接入 `/api/learning-note-media/{media_id}`。只读取此 checkout 的 bundle 登记项与固定 `.local/learning-note-media/` 中 SHA256 命名的 JPEG/PNG；文件哈希、后缀与实际魔数须匹配，目录/文件重解析或路径逃逸拒绝。主应用继承已有认证，独立只读预览仅绑定 loopback，不读取私人状态。图片失效保留文字、署名和回看位置，不开放 `.local`、不重编码原图，不将教学图片混入个人作品。运行中的旧服务不会因静态界面更新自动获得该路由，需受控重启；本轮以独立预览作为完整图片试读入口。

私有 JSON 的可选 `gateways` 字段保存 stage、answers、revealed、last_section，沿用单进程锁、原子替换、认证及 CSRF。旧 skills/日志/照片内容不变；未知历史 ID 留在磁盘但不作为当前可编辑条目。六种认知自评另加 unassessed，不推导原技能状态。数据库和照片资产没有迁移。

## 外部能力边界

BrowserSkill + 本地 Agent 执行，网站是任务与结果系统，不是 BrowserSkill 远程浏览器服务或自动 Agent 调度器。不上传 Cookie，不操作隐藏接口，不猜 CDN 高清地址，不替用户购买订阅。来源状态由每轮真实会话报告，静态来源建议不等于成功采集。保持默认不收费、不公开部署、不重绘人物、不自动操作 Photoshop、不开多人平台。旧 collector/provider 仅兼容入口。


## 未发布 collector 检查点（2026-09-28）

`collector.py` 保留显式、受限的历史可见页面采集，不是默认搜图实现。默认一键入口改为 `agent_collection.py`：配置的 argv → 私有任务包目录 → 本地 Agent → 严格 schema2 结果 → 既有 import 服务。网页不绑定网站或供应商 CLI；未配置就是 blocked，无 headless/固定来源回退。尚无实际供应商适配脚本，不能把可测试的传输层当成外部搜图完成。当前采集任务包升级到 schema 3：Agent 必须逐张打开图片，返回 modality + relative identity preflight；搜索 metadata 明确不能作为视觉证据。

数据库仍为 schema 2，无表迁移。Job 的可选 `active_attempt_id` 表示当前执行所有权，`last_receipt_reference_ids` 表示最后一个包实际校验导入的条目；累计 imported_ids 仅保留历史。`collection.attempt_started/finished` 和 `collection.reported` 追加到既有事件表，历史记录不覆盖。包回执标 completed 但本包无有效导入时，服务端状态仍 blocked。取消、重复启动、旧轮次覆盖分别由事务检查阻止。

Linux 原生子进程、退出/超时/取消与合成包已可回归；Windows 父进程先退出时的后代清理、服务硬崩溃后的恢复仍未完成验证/实现。自动模式为显式 opt-in；手动任务包路径保留。UI 根据返回的 job.status 显示成功/受阻/失败/取消，而非看到 HTTP 200 就宣称完成；迟到回执不关闭别的编辑对话框。

当前已有候选 modality + identity preflight 的协议、持久化、过滤/恢复和回归，但没有证明真实视觉分类准确率；基础摄影质量/近似重复策略、候选排序和审美会话/画像仍未完成。它没有自动 K/I/M/X、强制 ML 模型或 Golden Path。完整目标和未完成项保留在 2026-09-28 任务记录。

## 图库检索扩展（2026-10-02）

`library_browser.py` 提供独立资产查询与导航扩展，`web/library-browser.js` 负责网格和组合条件，原单图工作台继续负责人工选择。三张扩展表只保存人工导航分类、查询定义、项目置顶/访问记录；无旧表回写、无 CAS 变更、无图像事实推断，schema 3 兼容不变。筛选先于分页；计数、结果页和使用关系处于同一 SQLite 读快照。新写入口沿用现有认证、CSRF 与维护模式。详细约定见 [LIBRARY_DISCOVERY.md](LIBRARY_DISCOVERY.md)。


## 保留后的自动摄影分类（2026-10-06）

用户明确授权后，正常 Windows 启动流程默认使用现有 Antigravity 登录，逐张检查已保留图片（K / 有效全局收藏），生成视角、景别、主动作的初步找图标签。既有已保留图片也进入队列；不处理待定或仅候选图片。LAB_AUTO_CLASSIFY=0 可关闭，独立嵌入的 Settings 默认不启动执行器。这里更新了上述“不自动调度 Agent”的范围，仅限用户已授权的摄影分类，不包括自动搜图、制卡或验收。

classification.py 以实际资产 SHA 为任务主键，统一扫描保留关系，不在多个写入入口堆叠触发分支。library_classification_jobs 保存 pending/running/succeeded/failed/cancelled/superseded 状态与 300 秒租约；单张 CLI 最多 180 秒，正常退出释放任务，硬退出后过期租约可恢复。队列不会重新执行已有 annotation；人工注释优先，写回须匹配预期 revision 与当前保留关系。失败暂停队列并显示原因，显式重试保留已完成结果。

Antigravity 只读计划模式在仅含当前图的临时目录运行，查看从校验过的原图生成的 1800px 预览。模型必须留下当前文件 view_file 完成回执并返回合法 JSON，不能以标题或项目上下文代替视觉观察。使用原有子进程树控制结束超时/停止的任务；不会接入单独收费 API。图片会传送给用户现有 Antigravity 模型服务，不对外发布图库。

结果写 library_annotations 并标 actor=ai、producer、asset_sha、evidence，筛选直接使用初步标签；不改变资产字节、K/I/M/X、观察核验、审美画像或现场卡验收。详情页显示模型建议与人工修正来源。编辑时只合并迟到 AI 的未修改字段，另一窗口人工编辑仍受 revision 冲突保护。图库可看排队进度、失败原因及刷新结果。


## 类型与姿态检索契约修正（2026-10-06）
用户追加授权“补齐整个可浏览图库”，替换了仅保留图片才能分类的范围。图库和队列共用 BROWSABLE_REFERENCE / BROWSABLE_ASSET，覆盖待选图、保留及独立收藏，不改 K/I/M/X；淘汰、移出、归档或有效预检过滤的关系不入队。
模型同次看图必须输出既有 Kind 枚举与三个摄影维度；类型作为部分 asset_observations、三个维度作为 library_annotations 同事务保存。部分观察不包含凭空补齐的 review 字段，不生成项目核验/现场卡。类型读取统一按人工优先、同优先级最新记录排序；人工分类修改携带 annotation revision 与 kind observation ID。完成条件为类型观察与摄影分类都存在，旧三项结果补类型，人工三项只补缺失类型。
分类完成后图库按原筛选条件自动刷新。未知图片不会因选了真人cosplay而被当成真人返回；未完成覆盖在结果提示中明确。单张输出无效/文件损坏为 failed，其他任务继续；CLI/连接不可用为 blocked，暂停派发，显式重试，不使用替代标签或回退分析器。
