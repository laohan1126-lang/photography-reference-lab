# 摄影能力候选：独立原子性与重复审计

本审计只读根目录候选文件，审计记录写入本worktree。逐项遍历7份文件、221条候选；完整ID清单在 `atomicity_audit.json` 的 `reviewed_files` 中。

## 建议合并或调整

| 处理 | 保留 ID | 合并或相关项 | 判断 |
|---|---|---|---|
| merge | `posing-arm-torso-separation` | 合并：`cosplay-c04-arm-torso-separation` | 两项都控制手臂与躯干在画面轮廓中的间隙，观测指标和直接调整（挪手臂/转躯干）相同。Cosplay项提供应用语境与同意/不以身材为标准的边界，不构成独立控制变量。 |
| merge | `posing-intent-elicitation` | 合并：`cosplay-c02-align-shot-intent` | 拍前确认角色理解/目标照片、让扮演者纠正摄影师复述，是同一协作变量：共同目标是否被准确理解。 |
| merge | `posing-instruction-clarity` | 合并：`cosplay-c03-specific-pose-cues` | 两项都把抽象评价翻译成可执行、可复现的身体提示；c03的一次只变一个变量可作为更强的验收设计。 |
| merge | `posing-body-angle-to-camera` | 合并：`perspective-skill-body-angle` | 二者控制躯干相对镜头的转角，直接观测肩宽、躯干轮廓和脸部可见面；属于同变量跨领域复述。 |
| merge | `composition-gaze-action-room` | 合并：`mot-14` | 均控制视线或运动方向一侧的画面空间与边缘挤压；核心视觉变量是方向留白。mot-14主要把该规则移到运动主体/视频取景，并不形成完全不同的静帧控制项。 |
| merge | `composition-subject-context-scale` | 合并：`perspective-skill-environment-context` | 均选择人物相对画框大小及环境信息占比，目标与主要验收（主体/环境职责、信息保留）基本相同。 |
| merge | `perspective-skill-lean-depth-control` | 合并：`perspective-skill-pose-distance-subject-goal` | 均控制头部、躯干相对镜头的前后距离；髋后移/上身前倾是实现方式，按意图选择是同项的决策端。 |
| merge | `perspective-skill-wide-near-depth` | 合并：`perspective-skill-foreground-hand-scale` | 两者均控制身体/肢体/道具与镜头的近远距离差造成的比例夸张；手脚只是高风险应用点。 |
| demote_to_module | `mot-09` | 关联、但保留边界：`mot-10`, `mot-11` | mot-09同时要求诊断动作可预测性并在预对焦与连续追焦中二选一，是决策模块；mot-10与mot-11是两个相反、各自可训练的对焦执行技能，不应再把父项作为第三个重复L3。 |
| demote_to_module | `cosplay-c01-character-pose-translation` | 关联、但保留边界：`posing-character-appropriate-action` | c01一次列出站姿方向、步幅、重心、肩姿、动作幅度多个独立变量，达不到单一L3；posing-character-appropriate-action更窄，只控制动作幅度与角色意图的对应。 |
| demote_to_module | `cosplay-c05-pose-variation` | 关联、但保留边界：`posing-weight-transfer`, `posing-body-angle-to-camera`, `posing-directed-small-movement` | 候选要求分别改变躯干转向、关节弯曲和动作幅度，三项独立操控；且现有posing候选已覆盖承重、身体转角和短步/转向。 |
| merge | `posing-body-face-expression-alignment` | 合并：`cosplay-c14-expression-message-match` | 都检查姿势/身体语言与面部表情是否支持相同情绪或信息；只是c14以角色场景为语境。 |
| split_or_demote | `cosplay-c10-wig-costume-flow` | 关联、但保留边界：`cosplay-c11-costume-visibility-check` | c10混合运动轨迹（起点/方向/终点、引导视线）与露出脸/服装细节；后者是静态呈现可见度检查，已由c11单独覆盖，且“运动引导视线”和“服装展示”可分别失败。 |
| demote_to_module | `posing-feet-upward-sequence` | 关联、但保留边界：`posing-weight-transfer`, `posing-body-angle-to-camera`, `posing-purposeful-hand-placement`, `posing-head-gaze-selection` | 从脚到脸的检查顺序是多项技能的流程，不是一个独立可控变量；候选本身覆盖脚、髋肩、手臂、头、视线和表情。 |
| demote_or_clarify | `composition-visual-weight-diagnosis` | 关联、但保留边界：`composition-asymmetric-balance` | 视觉重量诊断同时列面积、明暗、色彩、纹理、清晰度、位置、孤立程度等因素，是诊断清单而非单一操控；不与不对称平衡合并，因为后者是使用诊断结果调整布局。 |
| split_or_clarify | `composition-crop-intent` | — | 当前技能处理有意/偶然边界截断，不足以支持单独的膝关节或其他关节截断规则；输出里的“关节截断判断”属于用户任务清单，但候选来源没有确立哪处截断应避免。 |
| clarify_scope | `composition-tangent-check` | 关联、但保留边界：`cosplay-c12-subject-set-overlap` | 相切检查是主体轮廓与背景线接触的特定视觉缺陷；c12是诊断重叠后分别移动摄影者、主体或场景物件的干预选择。结果有关联但控制步骤不同，暂不合并。 |
| clarify_scope | `cosplay-c06-large-prop-pose-variants` | 合并：`cosplay-c07-japanese-sword-character-pose` | 两项都组织人物与大型道具的静态空间关系；c07是日本刀与角色参考的特例。除非c07有独立的持握/身体动作变量和直接来源，否则更像c06的受限案例而非新L3。 |
| module_candidate | `posing-person-specific-adjustment` | — | 按个体舒适度调整姿势是跨姿势技能的个体化原则，可能同时改变承重、手、头、表情等不同变量，粒度更像模块级准则。 |
| module_candidate | `posing-seated-variation` | — | 单项同时改变躯干、手臂和头部，且验收关注连续成片的总变化，无法定位失败来自哪个变量。 |
| clarify_acceptance | `composition-leading-line-target` | — | “快速指出”“不需要讲解”“主体先被识别”“符合预设”属于可观察方向，但受观看者、呈现时长和预先意图影响。 |
| module_candidate | `light-006` | 关联、但保留边界：`light-005`, `light-007` | light-006把灯距对光质、主体亮度、脸部近远侧差与背景亮度的多种结果并列，和相邻两个候选重复涵盖表观光源尺寸/软硬及背景衰减。 |
| keep_distinct | `composition-focus-background-separation` | 关联、但保留边界：`perspective-skill-depth-of-field-control` | 前者验收主体与背景的构图可读性，并在需要时避免过度虚化；后者控制光圈、焦距、对焦距离决定清晰范围。结果相连但“目标/评价”与“技术手段”不同。 |

## 逐项处理与验收建议

- **posing-arm-torso-separation — merge**：合并全部来源；保留cosplay造型下的间隙测试和“按角色意图保留重叠”的条件，练习仍标记项目设计。 验收：两者验收均可观察；合并后以轮廓前后对照和角色意图为检查项。
- **posing-intent-elicitation — merge**：保留cosplay项关于场景参考、姿势方向和服装重点的来源及话术练习，作为通用意图确认的Cosplay分支。 验收：双方一句话复述和扮演者修正均可观察；避免将“符合角色”定义为摄影者单方判分。
- **posing-instruction-clarity — merge**：合并来源与例子；保留左右方向消歧及身体部位示范。与posing-small-adjustments区分：此项测指令能否被理解执行，后者测迭代时是否选择小幅度更改。 验收：“第一次能执行或主动澄清”可观察；建议加一项复述/现场执行，不要求每条指令必需相同。
- **posing-body-angle-to-camera — merge**：合并视角/比例方面的来源及固定相机下的角度对照练习；保留 posing 的可执行口令和“服装信息不被遮挡”的检查。不要把镜头/摄影者方位变化混入演员转角。 验收：正面/侧转可重复；画面宽度、轮廓和服装可见面前后可比。
- **composition-gaze-action-room — merge**：一条技能保留静态凝视练习和移动主体/横竖画幅练习两个应用分支；保留各自证据，明确快门/路径选择仍由运动技能负责。 验收：先记录视线/轨迹方向，再检查方向留白和是否撞边；运动分支额外检查主体移动后是否出框。
- **composition-subject-context-scale — merge**：合并环境人像/全身/紧凑肖像证据；保留perspective来源中视点和场地限制作为练习条件。焦段/摄影距离选择仍独立留在lens-working-distance等技能。 验收：用至少三种主体占幅版本，逐项标出需要的环境线索是否保留；不要与景别术语记忆混作同一验收。
- **perspective-skill-lean-depth-control — merge**：保留不同身体姿态/主体舒适度的来源与练习；写明前倾不是唯一实现方式，避免把特定摄影师方法升格为普遍法则。 验收：固定机位拍两种头身距离关系，观察比例并由主体确认可舒适复现。
- **perspective-skill-wide-near-depth — merge**：合并大手、大脚、武器等近处道具案例和cosplay专用练习；保留“移动相机与改变姿势不是同一变量”的对照步骤。 验收：固定镜头比较部位前后距离，再单独比较视点变化；目标比例是否出现可在画面中检查。
- **mot-09 — demote_to_module**：把mot-09留作模块入口/决策流程或前置节点；mot-10保存预对焦来源与已知路径练习，mot-11保存连续AF来源、遮挡误追案例和准确率验收。不要把二者证据相互借作同一方法。 验收：mot-10、mot-11各自的命中比例需预先定义样片数/焦点判定规则；mot-09只验收场景判断及选择理由。
- **cosplay-c01-character-pose-translation — demote_to_module**：将c01作为角色意图到姿势变量的模块流程，不保留为技能叶节点；各具体变量继续由重心、身体转角、步幅/移动等原子项承载。动作幅度项合并双方关于角色性格/场景依据的来源。 验收：动作幅度技能可以观察比较克制/动态两个版本；角色偏好需记为本次共同确认，不能作为通用评分。
- **cosplay-c05-pose-variation — demote_to_module**：保留c05为练习编排/模块说明，而不是再新增L3；其“安全舒适且每版单变量”的练习原则可挂在这些原子技能下。不要合并成一项混合变量训练。 验收：原c05的三变量姿势差异可作覆盖测试，但须按单变量版本分别验收。
- **posing-body-face-expression-alignment — merge**：并入角色意图确认与扮演者自评；保留拍摄者判断和当事人感受为不同证据，不将个人反馈概括成普适表情法则。posing-character-mood-variation保留为“生成多组情绪版本”，与单帧一致性检查不同。 验收：需能指出身体/面部各一条可见线索及其冲突/一致之处；当事人舒适感单列为协作反馈。
- **cosplay-c10-wig-costume-flow — split_or_demote**：把c10限定为假发/衣料运动轨迹与快门时机/方向的视觉设计；把遮挡服装特征的验收并入c11。保留c09作为助手协作和触发时机，不能与视觉轨迹设计互相替代。 验收：c10检查方向/终点和运动痕迹；c11逐项确认预先约定的服装细节在测试构图中可见。
- **posing-feet-upward-sequence — demote_to_module**：作为拍摄前检查清单/练习顺序，链接到现有原子项，不单独重复相同证据和验收。 验收：流程完成率可观察，但“没有互相抵消的僵硬方向”需拆为各身体关系的具体画面检查。
- **composition-visual-weight-diagnosis — demote_or_clarify**：诊断项可保留为模块/检查步骤；若作为L3，需限为“预测首要注意区域并记录一个主要权重来源”。不对称平衡保留布局选择与观者对照来源。 验收：“预测至少两个观者注视位置”应写清观察任务、展示时长和记录方式；不要用未定义的“快速”作阈值。
- **composition-crop-intent — split_or_clarify**：保留一般性裁切意图技能，记录具体关节裁切原则的资料缺口；不得把一般边缘/裁切来源外推成膝盖规则。 验收：盲看者区分刻意/偶然可观察；需预先说明样本来源及判断问题。
- **composition-tangent-check — clarify_scope**：把c12限定为单变量定位干预的工作流；tangent-check限定为“接触但未明确相交/分离”的诊断。共享来源仅在实际支持的命题上引用。 验收：c12单次只移动一个因素；tangent候选需示例和复核表明确区分交叉、相切、轮廓重叠。
- **cosplay-c06-large-prop-pose-variants — clarify_scope**：将c07的来源与练习作为c06的“日本刀静态肖像案例”，明示不推广到其他武器或实际操作；安全边界、扮演者同意仍保留。 验收：分别验收人物轮廓、道具轮廓、角色参考匹配和舒适稳定；“符合角色”由双方本次确认。
- **posing-person-specific-adjustment — module_candidate**：保留为整个摆姿模块的适配约束；具体可训练叶节点保持在被改变的姿势变量上。 验收：被摄者舒适反馈可记录，但“更符合角色”需有双方目标和实际前后版本，不能成为摄影者主观验收。
- **posing-seated-variation — module_candidate**：作为坐姿练习序列；链接到身体转角、手臂间距/手势、头部与眼神等原子项。 验收：逐版固定其他变量，分别记录躯干或手臂变化；“无需反复重新进入状态”应作为舒适流程反馈而非技能掌握阈值。
- **composition-leading-line-target — clarify_acceptance**：不新增来源；验收时固定盲看者提示、显示尺寸/时长、目标对象和记录方式。对一位摄影者的偏好不作普遍审美结论。 验收：明确“请指出第一眼落点/线条终点”的任务并记录选择；没有盲看者时仅做作者自检并标明。
- **light-006 — module_candidate**：不要机械合并所有灯距技能：light-005保留软硬/相对光源尺寸，light-007保留主体至背景的受光衰减；light-006若保留则作为“灯距变化时隔离不同效应”的实验模块，而非独立L3。 验收：单次测试固定灯功率和其他变量，分别记录阴影边界、脸部曝光和背景曝光；现有混合验收需拆分。
- **composition-focus-background-separation — keep_distinct**：前者仅引用景深作为手段，不重复教授DoF技术；后者不声称虚化必然改善构图。 验收：分别验收人物/背景可读性和清晰范围技术结果。

## 覆盖范围

- `composition_candidates.json`：逐项检查 28 条；完整ID在JSON清单中。
- `cosplay_candidates.json`：逐项检查 15 条；完整ID在JSON清单中。
- `light_candidates.json`：逐项检查 40 条；完整ID在JSON清单中。
- `motion_candidates.json`：逐项检查 34 条；完整ID在JSON清单中。
- `perspective_candidates.json`：逐项检查 27 条；完整ID在JSON清单中。
- `posing_candidates.json`：逐项检查 38 条；完整ID在JSON清单中。
- `post_candidates.json`：逐项检查 39 条；完整ID在JSON清单中。

审阅依据是候选文本中的技能名、能力、练习、验收和跨scope重叠。light与post的79项也全部遍历；当前未发现与上述控制点同等级的跨域重复。编辑阶段、结果诊断与技术手段可以保持独立，但描述应明确边界。此审计不新增摄影结论，也不改动根候选文件。
