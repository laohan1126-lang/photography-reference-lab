# Deep Research报告 · 原文到课程的独立审计

2026-10-10，主人在本轮补充完整《攝影專業判斷力模型》文本，包含两个学习原型与精确百分比。早期仓库检查没有该原文；现在已按实际收到的文本继续核查，不能继续报告“原文缺失”。报告中的[77]没有配套参考文献表，部分研究未给题名/作者/链接。本审计区分：报告原句已收到、网站上有同样说法、底层研究得到验证，三者不是同一证据。

## 精确数字的追溯结果

ROOT实际打开并阅读 [Frame & Focal的低机位文章](https://frameandfocal.com/shooting-techniques/low-angle-portrait-photos)，署名Marcus Webb，2026-08-30。读取导言、The Physics of Scale Distortion及相关论据/参数段，检查文章链接与引文；不是仅核搜索片段。

| 报告主张 | 原站是否找到 | 本轮结论 |
|---|---|---|
| 每降低相机5cm，画面人物高度增加约1.4% | 找到相同数值，原站还限定8×10输出 | 无距离、人物姿态、光轴、焦距/裁切、基准高度与高度测量协议；不能推广为每次降低相机的规律。拒绝作为课程数值依据。 |
| 低机位让人高22–37% | 原站导言称15–30cm机高，提到Journal of Visual Communication, 2022 | 无可定位研究题名、作者、DOI或数据。也未定义画框占比与感知身高的测量区别。原站存在说法，底层研究与可复现性未验证；不采用。 |
| 鼻延长6.2%、下巴缩短4.1% | 原站10cm机高段有前者和“chin recedes”后者 | 报告还把后缩改成缩短。未给面部朝向、距离、拍摄/感知指标与样本，不能从单一绝对机高推所有面部形态。拒绝精确比例和统一诊断。 |
| 低机位普遍增加威严/气势 | 有作者主张与更多精确心理指标 | 只能保留“可能用于某种表达”的创作选项；本章不把文化、神经或商业参数当作已证实规则，也不据此替主人判断审美。 |

对该页提到的期刊年份和Nikon实验室眼动描述进行了定向检索，没有定位到足以验证这些百分比的原始论文/数据；这不是证明任何潜在研究不存在。原页自身缺少可复核研究定位。没有必要为教学而替它补造实验。

### 为什么5cm→1.4%不能是通用物理规律

一个反例已足以否定无条件通则：使用简化针孔模型，光轴保持水平，平面主体全部位于同一轴向深度Z，相机不改变焦距或裁切，只改变高度h。物点垂直投影为 `v = f(Y-h)/Z`，主体上下端差为 `f(Y_top-Y_bottom)/Z`，与h无关。在都留在画框内的条件下，改变h只改变该平面主体的画面位置，投影高度不因此增加。

这是假设清楚的项目几何反例，不是本项目拍过的人体实验。真实人物有前后深度，蹲下后经常同时抬光轴、变焦/裁切、改变到头和脚的距离；这些联动可以改变遮挡、比例和感受，需要实际画面与拍摄条件判断。模型依据见 [Banks等的投影/观看分析](https://www.princeton.edu/~epiazza/papers/Banks%20et%20al%20%282014%29.pdf)，本轮定向读Figure 1B及印刷pp31–32。

## 原型中的基础事实与教学推论

| 报告原型/推论 | 问题 | 正式课程采用的修正 |
|---|---|---|
| 光圈过大使背景模糊不足；缩小光圈增大景深使背景更虚 | 将光圈和虚化方向颠倒，又混淆主体景深与背景模糊 | 同焦距、对焦/拍摄距离等条件下，小f数/较大开口通常使景深更浅，背景离焦模糊通常增加；收光圈通常扩展主体清晰范围。角色/背景分离仍不等于越虚越好。依据[Nikon正文](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/understanding-maximum-aperture)、[Canon手册p129](https://files.canon-europe.com/files/soft24335/Manual/EOSD60_CUG_EN.pdf)、[ZEISS p3、pp6–8、p15](https://lenspire.zeiss.com/photo/app/uploads/2022/02/technical-article-depth-of-field-and-bokeh.pdf)。 |
| 背景太亮时用ND或降快门 | 如果“降快门”指降低快门速度/延长时间，会增加曝光；ND同时减少主体与背景进光，并不单独修复二者亮度比 | 减少环境曝光可缩短快门时间、降低ISO或收光圈，并考虑人物动作、闪光同步和主体曝光；补光/改变光线关系解决亮度比。ND可在希望保持光圈/同步条件时使用，但需相应处理主体。 |
| 提高机位必然纳入更多天空、比例回正 | 忽略镜头朝向、构图与身体深度；提高视点并保持朝向/重新取景是不同操作 | 分开观察高度与俯仰，预测地面/背景覆盖和遮挡；不承诺一定更多天空或自然比例。 |
| 换稍长焦段便减少透视夸张 | 未分开视点移动与变焦 | 固定视点的变焦主要改变视角/画面范围；后退再匹配构图才改变近远深度关系。畸变/边缘拉伸另行辨析。 |
| 低机位使远端目标被拉长 | 混淆近远放大与方向缩短 | 简化投影中更近的部位通常更大；倾向光轴的身体方向可能缩短。姿态、遮挡、光轴方向都要看实际画面。 |
| 只有手动模式才能完全控制画面效果 | 把一种有效工作方法提升为必要条件，且锁参数不等于移动/光线变化后曝光恒定 | 用手动锁设置是一种控制流程；曝光/对焦模式应按变化与任务选择，不用模式名称判定职业能力。 |
| 作者未指明的“可选方案、立即换衣、下一步调整”等全当真实事件 | 重建出的合理方案不等于作者实际决策 | 一手原文明确的操作和项目推演分别标识，不将推演写成原作者对白或真实失败修复。 |

报告中这两处景深/光圈倒置是新收到原文的实际错误；此前检查已有笔记未发现倒置。二者的检查对象和时间区分记录。PPA前1/3后2/3的非通则问题另见 [COURSE_EVIDENCE.md](COURSE_EVIDENCE.md)，已经修正正式资料条目的限制。

## 独立来源复查与限制

两位独立研究Agent先检查 SOURCE_MAP/raw，未找到以下案例与三项教育材料记录（PPA critique条目例外）；以下是本轮补查，不能假称复核了已有原始研究档案。没有将新发现批量注入247技能或课程案例库。

| 报告案例/论据 | 一手阅读与判定 |
|---|---|
| Austen Blakemore男孩门口人像 | 实读[作者BTS全文](https://weddingphotographynottingham.co.uk/blog/2019/6/21/portrait-photography-behind-the-scenes)，未逐张打开其图片。Corey、阴天门口、人脸测光后拨入手动曝光、后方两条柔光箱、试拍微调及移动需要重新开始确有作者描述。可以作为该次工作流叙述，不升级为spot测光/AE锁定或所有现场都必须重来的规律。 |
| WorkingProof棚拍“真实案例” | 实读[协作BTS文章](https://www.workingproof.ca/blog/behind-the-scenes-the-collaborative-process-of-a-fashion-photo-shoot-in-the-studio)、[Studio Hacks](https://www.workingproof.ca/blog/studio-hacks-how-create-different-looks-using-minimal-props)及[表情文章](https://www.workingproof.ca/blog/the-role-of-expression-in-portrait-photography-capturing-emotion-and-personality)全文。是一般流程/营销建议，没有可定位项目、人物、照片序列与镜头。“浪漫用长焦”“立即换衣/灯的实际纠错”未获原文支持，不当真实过程案例。 |
| CosplayReal黄昏停车楼变机库 | [原站指南](https://www.cosplayreal.com/fr/blogs/cosplay-guides/finding-better-cosplay-photoshoot-locations-scouting-guide)正文的搜索工具提取内容确有顶层停车楼、蓝后光/橙前光故事；直接原站open超时，访问深度只认已返回的正文。缺摄影师、角色、照片/前后对照、地点日期或现场记录，只能证实网站讲了这个故事，无法验证实际拍摄。零场租也不等于器材/交通全零成本。不能成为本站真实照片案例。 |
| Brian Utesch观摩建立心像 | 实读[LinkedIn作者原文](https://www.linkedin.com/pulse/road-expertise-principles-building-mastery-ux-research-brian-utesch-ueuue)与[Medium转载](https://medium.com/design-bootcamp/on-the-road-to-expertise-principles-for-building-mastery-in-photography-and-ux-research-5cb5d7247256)全文。作者确有观看多题材作品、积累mental patterns的第一人称建议；不是效果研究，其职业经历在本次材料中仍是作者自述，未独立认证。 |
| PPA同行评审者进步最快 | 实读[Kira Derryberry的Critique Is Your Friend](https://www.ppa.com/ppmag/articles/presidents-message-critique-is-your-friend)、[Merit Image Review](https://www.ppa.com/credentials/merit-image-review)、反馈推广与2019客户研究文章可访问正文。前两者支持个人经验/反馈制度，未给进步速度比较；标题带study的客户研究也不是学习效果研究。不能写成“PPA研究发现进步最快”。 |
| 摄影AI/AR研究约97%准确度 | 独立Agent实读[Scientific Reports论文](https://doi.org/10.1038/s41598-025-24415-8)的摘要、方法/数据描述、DRNN、结果表、pilot与结论；未读原始数据或复现。Table4的97.18%是DRNN模型Accuracy，针对作者操作化的图像/显著性/质量标签，非学生能力测验，也不能自动称为专家构图判定准确率。另有30人pilot前后评分，证据对象不同；对照、标注/测试集与外推细节有限。不证明本站反馈或专业现场迁移有效。 |
| 刻意练习 | 定向读[Ericsson等1993论文PDF](https://review.firstround.com/content/files/images/blogs/freakonomics/pdf/deliberatepractice-psychologicalreview.pdf)摘要与练习特征/比较活动段，PDF pp4–6，印刷约366–369，未通读；[APA DOI](https://doi.org/10.1037/0033-295X.100.3.363)可定位。任务匹配基础、及时有信息反馈、针对弱点和重复监测有一手依据。是跨领域框架与音乐研究，不是摄影现场判断/本站学习效果测验，也不要求反馈必须由AI自动给出。 |
| 认知学徒制 | 1989原始章有书目但PDF访问失败，没有冒称读过。实读作者Collins/Brown/Holum的[1991 American Educator原文](https://www.aft.org/ae/winter1991/collins_brown_holum)，重点是传统/认知学徒制、六种方法、排序与结尾限制。显化思考、真实任务、支架渐撤及多情境与报告大体一致；原文不是摄影效果实验，也提醒不是通用教学模板。 |

课程已采用核验的教材样章、投影/景深一手材料与实际打开的COSPLAY MODE真人人像。理论可以指导项目练习，作者经验可以提供思路；模型精度、营销故事、未定位统计和项目推演不能冒充本章的学习收益或真实操作证据。

本次不修改主人提供的报告原文，不扩展第二章，不把报告的8单元组织直接变成另一套能力地图。教学目标可保留，事实、数字、案例过程与系统有效性仍逐项按证据判断。
