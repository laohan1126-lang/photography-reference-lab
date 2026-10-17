# 有马加奈搜图结果补入正式图库

## 用户纠正与目标

用户指出：“但是我说喜欢的那张 我在网站没看到 而且我打开以后显示未选择也只有三张啊”。核对确认，上轮把11个候选及7张逐图审查结果只保存在 `.local/search-quality-20261018/`，没有导入正式网站；正式有马加奈项目现有30条 Reference，只有3条 pending。这是交接遗漏。

将上轮已实际打开的7张真人照片按原来源和字节，通过既有项目采集任务与schema3导入接口接入有马加奈项目。用户明确喜欢的确切图片按其原话“如果没被选中这张就是系统有问题的”设置为本角色参考 K；其余新增图片保持 pending。角色身份及原摄影师仍保留实际核验状态；B类迁移参考不算作A类角色匹配。被排除的插画和拼图不导入。

不得更改该项目其余30条既有选择、私人原始字节或数据库结构；只经现有应用API追加本轮资产和Reference。私有图片与数据库不进入Git。完成后读取API确认新增数量、 liked 图片SHA、K/pending状态及已有选择保全。

## 当前证据

- 正式项目：有马加奈 / 我推的孩子，ID `d9344449981d48e39ec24dbe92f93234`。
- 导入前项目Reference：30条，K=10、pending=3、reject=17；用户喜欢图片的SHA256为 `9433480f50310c4a8590bc107f0504ee3d8da0cd4749acaf89fe8aa174c01a87`，此前不在正式Asset或项目Reference中。
- 上轮真实搜图与逐图审查的原包在 `.local/search-quality-20261018/after-review-gate/kana/visual-review.zip`；含7项schema3视觉预检，图片身份均保持 uncertain，A与B发现意图分开。
- 正式数据库现由本机18765服务使用；此任务仅通过现有服务API写入，不直接SQL写库。

## 验收与检查点

- 创建正式采集Job并导入7张合格真人照片；若哈希已在同项目出现，则不覆盖既有Reference或选择。
- 只有上述已明确喜欢图片设为 K，其他新增图片为 pending。
- 通过实际网站API核对该图片的项目Reference、decision、来源发布页与原图SHA，并确认其原图路由可取。
- 导入前后统计与既有选择摘要保存于 `.local/search-quality-20261018/`。
- 后续追加真实导入回执、可见状态、验证和Publisher结果。

## 实际结果

通过正式服务创建采集Job `b577bfb881d642cea503078b2432a5c7`，将上轮7张实际打开的照片包按schema3导入：created=7、existing=0、errors=0。Job为blocked是因为角色身份仍uncertain、原作者未核实；候选实际已经导入且网站可筛出7/7。

用户正例以SHA256 `9433480f50310c4a8590bc107f0504ee3d8da0cd4749acaf89fe8aa174c01a87` 唯一匹配Pin `874965033874150534`，通过现有Reference修订接口设为 K。本轮其他6张保持 pending，7张身份全部 uncertain。没有因发布账号推断原作者。

项目结果：Reference从30增至37；K=10→11，pending=3→9，reject=17保持。用现有服务API重读项目全部X视图后确认原30条决定逐项未改变；本轮Job过滤视图为7张，其中K=1、pending=6。通过 `/api/assets/{sha}/original` 取回Liked图片原字节，86602字节且SHA256与用户反馈记录一致。

隔离Chromium实开网站链接 `http://127.0.0.1:18765/#view=references&project=d9344449981d48e39ec24dbe92f93234&job=b577bfb881d642cea503078b2432a5c7&ref=5cfaab0d9ccc4abc89e7a931907aa5b2`，实际画面显示7/7、末张为原图、K已选中；页面截图和正式API计数回执存于 `.local/search-quality-20261018/website-liked-reference.png` 与 `.local/search-quality-20261018/web-import-verification.json`。因此用户原先看到3张待选是因该批从未进入正式库，当前已补入。
