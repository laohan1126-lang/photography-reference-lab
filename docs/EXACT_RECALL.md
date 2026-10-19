# 指定角色与服装：先找准，再交付

适用于“公孙离·祈雪灵祝”等明确角色/版本任务。不调摄影或审美排序，不写生产K/I/M/X，也不把失败池交给主人评价。

## 可复跑入口

工具为 `tools/exact_recall.py`，本机使用已有依赖的Python：

```powershell
$py='C:/Users/Dell/AppData/Local/Programs/Python/Python312/python.exe'
& $py -B -X utf8 -m tools.exact_recall --help
```

1. 每个任务在仓库`.local/`新建目录，scope.json写character、costume、work与brief，别名需有来源。记录查询/访问上限，不复用旧冻结实验目录。
2. 用已授权BrowserSkill自己的会话搜索。保存正常可见DOM的url、search和cards.text；调用assess。它校验查询绑定，只把文字作为“下一步看哪里”的线索，永远返回confirmed_count=0。
3. `SAMPLE_THEN_CHANGE_SOURCE`表示先看少量疑似结果，不能批量下载到达标。实际视觉样本都为MISMATCH/NEEDS_EVIDENCE时，after_visual_sample返回CHANGE_QUERY_OR_SOURCE；不能以继续下载来假装进展。`INSPECT_TARGET_DETAILS`也只授权继续查看原帖，不是角色确认。

   同时检查平台在结果区显示的实际查询解释。URL/搜索框一致但页面提示“這是我們針對 ali cosplay 找到的內容”，不能当作Arli原词检索成功；assess会返回REVIEW_QUERY_REWRITE。明确“找不到相符Pin”的页面返回EXPLICIT_NO_RESULTS，不把窗帘/书房等推荐入口收成候选。这两个检查只根据已见公开提示，不伪装知道平台内部检索算法。

   Pinterest应比较有依据的中文名、拼音名和国际名，保留游戏/版本上下文。公孙离本轮Gongsun Li比中文短查询有更好的角色方向；官方名Arli可能被平台纠成ali。角色能找到不等于指定皮肤能找到，服装拼音Qixue Lingzhu也不是已经验证有效的译名。可从真实目标帖的多语言文案补充线索，但不得把临时翻译当官方别名。详见本轮语言对照任务记录，不能把单查询失败写成“Pinterest没有此角色”。
4. 从正常搜索卡片点击原发布页。capture只读当前`.note-detail-mask .note-container`中已加载的图片currentSrc，不读bootstrap内部状态、Cookie或隐藏接口，不猜CDN地址。每次默认3张、最多5张小样本，绑定expected page，去除轮播DOM重复。它保存接收字节和UNREVIEWED记录，不自动视觉确认。
5. Agent实际打开每张图片，把actor/producer、asset_sha/opened_sha、context_sha=digest(scope)、kind/identity/costume、分项evidence写入model-reviews.json。非真人、拼图、错误或不确定版本不能进入结果。记录publisher（原帖账号）与attribution_note，不能把发布者直接称为摄影师或出镜者。
6. 合并接收记录为received.json，render生成public/index.html与confirmed.json。只有有效视觉match进入页面；无合格图明确显示0，不增加评分表单。相同SHA只展示一次，同图组仍是同组，不能号称独立拍摄样本。

```powershell
& $py -B -X utf8 -m tools.exact_recall assess --folder <仓库内.local任务目录> --snapshot <可见DOM快照.json> --query '实际查询'
& $py -B -X utf8 -m tools.exact_recall capture --folder <任务目录> --session <自有会话ID> --page <当前已正常打开的原帖canonical页> --limit 3
& $py -B -X utf8 -m tools.exact_recall render --folder <任务目录>
& $py -B -m http.server 18773 --bind 127.0.0.1 --directory <任务目录/public>
```

这是一条Agent执行的有界召回路径：搜索计划、换路和实际看图由Agent执行，程序提供绑定、采样与交付门槛。没有悄悄更改日用服务的LAB_COLLECTION_COMMAND，没有新常驻采集器或新模型。旧collect_adapter和学习实验代码保持冻结；其schema2仍只表示未核验候选。无需本轮用户评分即可完成“只交付已核验目标参考”，但不能从AI自评推导人类准确率或审美收益。

## 验证与限制

`pytest -q tests/test_exact_recall.py --basetemp=.local/<任务>/pytest`检查实际旧故障边界、查询失配、登录停止、未知/错误/拼图不进入结果、SHA/context与安全链接、重复和无评分页面。真实来源/图像另做实际看图核验，测试替身不代表识别准确率。

小红书某些文章直接canonical地址会要求App扫码；遇到该限制停止该条，不猜参数、绕行接口或用缩略图冒充原图。来源链接的持续可访问性不保证。单次采样只读取已加载图，少于limit如实返回；不能宣称整篇所有图片已核验。图像保存于本机仅供个人参考，不改变原作者权利。

本次实际调查和交付见 [任务记录](tasks/2026-10-18-gongsunli-costume-recall.md)。当前Git/Notion仍受上一轮Windows缓存隐私风险暂停约束。
