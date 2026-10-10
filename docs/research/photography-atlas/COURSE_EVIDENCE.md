# PHOTO ATLAS · 第一章证据与验收（2026-10-10）

本记录对应 `sword-perspective-chapter`，审查基线 `b8807fe02f23d75887f464fc53a5ebe9f346582d`。课程的实质内容在 GATEWAYS.json，生成到 web/learning-atlas.json；本页保存来源映射与实际核验范围，不代替教学正文。架构比较见 [COURSE_RECONSTRUCTION.md](COURSE_RECONSTRUCTION.md)。

## 试读入口与关键案例

本轮独立预览：[持剑人物前倾、低机位与头大身小](http://127.0.0.1:18771/learning?course=sword-perspective-chapter)。若预览未运行，在项目目录执行：

```powershell
.venv/Scripts/python.exe -X utf8 tools/preview_learning.py --port 18771 --reference-url http://127.0.0.1:18765/
```

该预览不连接正常资料库，不写主人个人状态。日用服务代码更新后需受控重启，入口为 `/learning?course=sword-perspective-chapter`；本轮未重启或部署日用服务。

先看第一节持剑前倾成片，写观察；第三节比较原地变焦、同焦段换距离、下胸/膝高；第四节回到原成片选一次调整与代价；第六节独立答A/B/C，之后才展开可能解。没有按一种标准身材比例判对错，没有因读完或展开答案自动升级。

## 教学、事实与意见的映射

| 内容性质 | 实际证据 / 阅读范围 | 本章采用什么与边界 |
|---|---|---|
| 专业教学组织 | 五本教材的合法目录/样章；逐本范围见重构报告及站内来源栏 | Valenzuela的顺序学习/参考使用与姿态系统、Hunter等的预测/实验、duChemin实际样章的意图与提问。Freeman只有目录。没有声称通读或复现未读章节练习。 |
| 投影物理模型 | [Banks等，2014](https://www.princeton.edu/~epiazza/papers/Banks%20et%20al%20%282014%29.pdf)，Figure 1B，印刷pp31–32 / PDF pp3–4，定向阅读 | 固定投影中心只变焦与改变视点有不同作用。距离、轴向深度、相机朝向需要区分。有限模型不能倒推单张照片的焦段、距离、原始机位或人物身体尺寸。 |
| 作者实拍演示 | 一灯和一镜的登记帧01:07、02:20；链接及原研究范围见course-yideng | 原地35mm裁切/70mm关系相近、同50mm近/远背景关系不同。数字是视频可见标注，不是本项目测量。姿态未完全锁定，不能当精确量化实验。 |
| 作者经验和表达偏好 | Manny Ortiz登记帧01:48、01:56；course-manny | 下胸/膝高提供对照起点。240p小图与不同姿态不能量头身比，也不推出膝高普遍最优。ROOT本轮只重新查看这些帧，未重看全视频。 |
| 作者实践/主观意图 | [Neil van Niekerk正文](https://neilvn.com/tangents/photographing-wide-angle-portraits/)，正文有关距离、前臂与有意夸张的段落；登记双图DSC_1493-1489重新打开 | 近处手臂与身体关系、退后/调整姿态的经验。夸张是否成立仍要看拍摄意图，作者经验不是统一审美标准。 |
| 光圈与清晰条件 | [Nikon正文](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/understanding-maximum-aperture)有关景深/快门；[Canon EOS D60手册](https://files.canon-europe.com/files/soft24335/Manual/EOSD60_CUG_EN.pdf)印刷p129 | 小f数/大开口通常使景深更浅，收光圈减少进光；焦距比较须限定同距离/同f数。背景模糊与主体景深分开。Canon的“后方通常两倍”不当作通则。 |
| 景深基础修正 | [H. H. Nasse / ZEISS, Depth of Field and Bokeh](https://lenspire.zeiss.com/photo/app/uploads/2022/02/technical-article-depth-of-field-and-bokeh.pdf)，March 2010，实际读p3、pp6–8、p15，未通读45页 | 可接受模糊决定清晰标准；p15明确前1/3后2/3仅在特定条件成立，近距更对称，接近超焦距后方增长。没有把文章数例变成会场参数。 |
| 真实道具/姿态教程 | [COSPLAY MODE日本刀](https://cosplaymode.net/howto/1680/)的前倾与「腰が引けている」段；[武器教程](https://cosplaymode.net/howto/480/)对应下表照片 | 真实人物、剑与姿态的可见关系；不提供受控距离/机高实验。两张髋后撤照片都是反例的不同观察角度。 |
| 项目自行设计 | 本章原创因果解释、逐项权衡、固定位置改变俯仰/近水平升降的操作、大小道具/受限场地方案、A/B/C及反证任务 | 综合多个来源而非一图一卡。尚未做受控实拍，不宣称来自某本教材或被职业现场验证；不同合理意图允许不同答案。 |

## 实际图像复核、署名与使用边界

ROOT在正常连接的Edge Agent Window打开六个精确原图地址，逐图看截图；独立课程审查Agent也查看六图和五个本地原教学帧。以下尺寸来自实际加载的原图。只描述画面可见内容，不能从照片读出EXIF、镜头俯仰、真实距离或后期流程。

| 站内用途 | 精确原图与尺寸 | 可追溯原页 / 观察限制 |
|---|---|---|
| 贯穿案例：前倾持剑 | [nihontou043.jpg](https://cosplaymode.net/wp-content/uploads/2022/06/nihontou043.jpg)，1200×800 | 日本刀教程；脸、前膝、剑、门框构成方向关系。地面/背景模糊成因未核实，不称为某种已知后期。 |
| 姿态反例A：正面 | [nihontou011.jpg](https://cosplaymode.net/wp-content/uploads/2022/06/nihontou011.jpg)，925×1200 | 「刀NGポージング → 腰が引けている」第一张。 |
| 姿态反例B：侧面 | [nihontou012.jpg](https://cosplaymode.net/wp-content/uploads/2022/06/nihontou012.jpg)，1125×1200 | 同一反例段第二张；不是纠正后照片，也不是单变量机位对照。 |
| 新图A：沉着剑士 | [nihontou025.jpg](https://cosplaymode.net/wp-content/uploads/2022/06/nihontou025.jpg)，800×1200 | 日本刀教程；前文未讲。没有完整脚部，不按全身比例测量。 |
| 新图B：另一种道具关系 | [10_MG_3967.jpg](https://cosplaymode.net/wp-content/uploads/2020/06/10_MG_3967.jpg)，900×1125 | 武器教程，白背景长直剑与双手；未知实物长度/重量，不宣称完成大剑实拍验证。 |
| 新图C：动作与剑的遮挡 | [06_MG_3956.jpg](https://cosplaymode.net/wp-content/uploads/2020/06/06_MG_3956.jpg)，900×1125 | 武器教程，黄上衣屈膝动作、剑与手臂；前文未给该图解析。 |

日本刀原页署名：text まめまよ、adviser 龍村自斎、photo 涼子／大関敦。这是文章层级署名，未声称每张分别归属于哪位摄影师。另一武器原页未逐图署名摄影师，保留COSPLAY MODE文章来源，个人摄影署名未知。

五个已登记本地帧：`bili-35-70-same-position-00-01-07`、`bili-50-close-far-00-02-20`、`s2-lower-chest`、`s2-knee-level`、`sd-neil-arm-position-example`。复用 LEARNING_CONTENT 内原哈希、原出处与私人文件，经现有哈希验证路由读取；没有改原字节、下载更高分辨率、升级旧视频阅读范围。新照片使用精确原站HTTPS地址，有限站内展示与中文转述；未获得离线转载许可，不放入Git、安装包或个人图像库。原站失败时保留实质课程、要点和出处。

## 可疑数字与基础事实审计

1. 初查仓库只有Frame & Focal排除记录，没有Deep Research原文。主人随后在本轮补充完整文本；ROOT已据此找到并实际阅读原站低机位文章，对5cm→1.4%、22–37%、鼻6.2%/下巴4.1%逐项核查。网站确有这些说法，但没有足以复核底层研究的定位或拍摄/测量条件；不能成为通用课程数字。报告的光圈倒置、快门/背景、变焦和机高推论也已审计，具体见 [DEEP_RESEARCH_AUDIT.md](DEEP_RESEARCH_AUDIT.md)。底层研究仍未证实，数字不进入本章。
2. [PPA Module 1F](https://wiki.ppa.com/books/photography-certification-guide/page/module-1f-capabilities-of-lenses)将前1/3后2/3用于入门景深说明，还举焦点10英尺、景深9英尺→7–16英尺的分配例子；它缺少作为通则所需的条件。本轮用ZEISS p15独立纠正，强化 TUTORIALS.json 及 tutorials/perspective.json 对该条目的限制，课程给出正确的条件性解释。
3. 初查现存笔记/教程和新正文未见光圈方向倒置；主人后来提供的报告则明确写“光圈过大使背景模糊不足”“缩小光圈增大景深使背景更虚”，已核对为实际错误。区分检查对象，不虚构已存笔记错误。正式课程保留正确f数/开口/清晰关系，并避免将收光圈、背景虚化、改变透视混为一谈。
4. 不从主案例猜“最佳焦段”、机高、头身比、前倾角或百分比改善。既有认知入口的项目理想模型/数例保留原限制，没有移作本章实拍数据。

## 独立审查及实际工程验收

独立诊断、教材定向阅读、事实审计、课程审查和回归由不同Agent执行，ROOT核对来源范围与选图。审查纠正了：把同类反例误读成改善后；没有可操作区分高度/俯仰；视频复核范围表达过宽；一条现场话同时改姿态/剑/距离却声称只改距离。最终指导先保持人物/剑，再由摄影者后退，其他调整分轮检查。

实际执行：

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_library.py tests/test_imports_jobs.py tests/test_workers.py tests/test_operations.py tests/test_personal_library.py tests/test_collection_runner.py --basetemp=.local/course-core-qa
.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_learning_course.py tests/test_learning_course_ui.py tests/test_learning_gateways.py tests/test_learning_gateways_state.py tests/test_learning_gateways_ui.py tests/test_learning_content.py tests/test_learning_content_ui.py tests/test_learning_state.py tests/test_atlas_provenance.py tests/test_learning_ui.py tests/test_photography_tutorials.py --basetemp=.local/course-final-learning
```

核心123 passed；学习/来源/HTTP浏览器86 passed、1 skipped（Windows无法创建symlink），均有现有Starlette TestClient弃用警告。初次集成65 passed、1 failed、1 skipped：旧catalogue兼容测试删去LEARNING_CONTENT但带入了要求登记媒体的新课程；fixture修正为真正旧三入口后通过。新增媒体校验回归还实际复现缺失source时KeyError，再修复为明确错误报告。最终小范围检查记录追加于任务文件。

HTTP Chromium用桌面1440×1000与手机390×844检查课程直链、陌生query、三张新图/默认折叠解析、草稿关闭重开、远程/本地图片失败回退、技能导航与无自动状态写入。模拟图片失败的测试不是照片准确性证据。

ROOT另外通过BrowserSkill实际连接Edge，桌面与iPhone14模拟390×844逐页检查真实网络图片、原教学帧、正文、目录与答题框；DOM未横向溢出。照片实际可见，不以“img标签存在”代替加载。私人截图在 `.local/atlas-course-*.png`，不提交Git。标签页内临时答案与解析操作不写正常资料库。

这些结果支持可读、可操作及边界完整，不证明用户已学会。新课只做一章；未修改 SKILL_TREE、LEARNING_CONTENT、主人图片或学习状态。最后定向回归9 passed，构建一致性、三项JS语法、diff检查通过；命令与具体版本见任务记录。未完成：主人独立答题/现场复拍、受控大剑与短匕首对照、被引用百分比的底层原研究验证、整树逐项语义去重、日用服务升级后的完整工作流。Claude Code/Antigravity实时Hook兼容未测；WSL_NOT_COVERED。
