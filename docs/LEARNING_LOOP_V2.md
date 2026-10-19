# Learning Loop V2：有界视觉证据与场照对照

本工具只读正式库，私有实验在仓库 `.local/learning-v2/`。旧V1输入、预测、个人评价与结论保持不变，candidate2不启用。当前实现没有接入日用服务或修改正式K/I/M/X。

## 实际改变

新增 `tools/learning_v2.py` 的 `evidence_state` 是本轮唯一共用机制边界：核对实际字节SHA、opened_sha、任务context SHA、模型来源与分项可见依据。分别输出AI三态、有效三态、人工身份来源和冲突原因。真人类型、角色和服装版本分别判断；服装无要求才允许not_required。unknown保持待补证，明确反证为MISMATCH，身份/服装证据齐全才CONFIRMED。CONFIRMED是模型预测状态，不代表人类真值或授权验收。

人工证据只可解决身份疑点，不能把拼图改成独立摄影，不能替代指定服装版本证据；AI和人工身份相反时保留冲突。调用方必须从实际人工快照提取逐SHA标签并记录source_snapshot_sha，不接受K/X作为审美标签。本次实际人工来源为上一轮只读提交，未把它算为AI识别成功。

模型负责逐图观察、类型/角色/版本推断、机位/景别/姿态/光线/环境/手势字段与不确定原因。确定性代码只负责绑定检查、状态合成、同池稳定排序、预算、冻结、标签保存和指标；没有执行参数训练。

## 冻结排序

场照任务由用户指定“王者荣耀 公孙离 祈雪灵祝 场照”。仅对CONFIRMED且至少3个摄影维度已知的图片计算本次任务信息匹配数：可见现场环境、持伞/道具关系、身体取景、可复现姿态、可描述机位和光线。每项1分，没有个人审美分。非全身照不扣分，纯背景不形成永久负规则；相同分数沿用原始次序。未确认保留，放在已确认之后；明确不匹配保留到末尾，均可人工复核。

同一候选池同时冻结original、existing_rule与task_rank，人工按SHA升序每图只评价一次。最多12候选，不根据新排序挑选有利测试子集；超过12直接停止。与旧历史SHA/统一dHash近图重合时整轮标为STOP_HISTORY_OVERLAP_NOT_PROVEN。不同摄影师/拍摄组仍未独立证实，不能宣传为跨来源泛化。

人工判断三个维度：角色/版本/真人独立摄影是否正确，摄影是否可用，自己是否喜欢。不预填，不代选。页面只用真实回环HTTP，草稿原子保存，提交生成只读快照并自动计算指标；不提供需要file://提交的假入口。

NDCG@5使用整个固定池的IDCG，喜欢/一般/不喜欢为2/1/0、gain=2^rel-1；少于5张或相关标签缺失返回N/A。V1原函数以每路top5自身生成IDCG，其冻结结果不改，V2绝不能与其数字直接横比。错误角色或版本前五数、摄影可用数、喜欢数、误收/误拒和待补证比例分别报告。人工未知不按0；无人工真值不计算识别准确率。相同排序或不足1张Top5可用收益为NO_MEANINGFUL_GAIN，摄影提高但审美退步单独标识，样本不足NOT_PROVEN。

## 复现与继续

在本仓库运行（本机已安装依赖的Python）：

```powershell
$py = 'C:/Users/Dell/AppData/Local/Programs/Python/Python312/python.exe'
& $py -B -X utf8 -m tools.learning_v2 check-freeze
& $py -B -X utf8 -m tools.learning_v2 report
& $py -B -X utf8 -m tools.learning_v2 serve --port 18773
```

入口是服务打印的 `http://127.0.0.1:<port>/`。`evaluation.json` 为只写一次的排序绑定；report反复运行只重新计算已有标签，不重排、不调参。提交后重新启动服务可恢复只读结果。新任务必须另建隔离目录和先冻结，当前目录的search/evaluate只允许一次；失败证据不可覆盖，未启动联网的依赖导入失败不计作一次真实查询。

现成局部回归：

```powershell
$env:PYTHONPATH=(Get-Location).Path
pytest -q tests/test_learning_v2.py --basetemp=.local/learning-v2/new-test-run
```

测试基于合成边界，不代表图像识别准确率；真实图像观察和人工评价另存私有目录。没有计时的人类基线时，人工筛选成本节约为NOT_PROVEN；不会从看图数量或程序测试推导节约。

## 公开参照与安全

露比诊断参照：[动画官网](https://ichigoproduction.com/Season1/chara/ruby.html)。公孙离版本参照：[游戏官方英雄页，点祈雪灵祝](https://pvp.qq.com/web201605/herodetail/199.shtml)，[官方账号皮肤设计帖](https://www.taptap.cn/moment/107211884662358966)。官网的实际皮肤图片与官方文案分别核对；描述不能自动成为候选图片证据。Pinterest Pin仅表示可追溯平台来源，不冒充原作者已验证。

本轮发现896ec94把11个Windows缓存和4个测试产物带入既有历史。已添加针对新未跟踪产物的ignore，但ignore不能移除已跟踪文件或清理历史；未删除任何用户文件。隐私风险未完全排除前停止push和Notion，保留本地修改及Publisher延期证据；不擅自重写历史。正式交付必须逐路径白名单，禁止git add -A。具体当前状态见[任务记录](tasks/2026-10-18-learning-loop-v2-evidence.md)。
