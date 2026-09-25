# 图片采集快速流程

## 诊断依据

用户报告：约 30 张图片用了 4 小时仍未完成，约为 7.5 张/小时。现有批次记录了约 210 张结果卡、31 篇笔记、113 张逐图分析、50 张候选下载和 36 张最终保留；36 张文件合计约 5.8 MiB。下载内容很小，且历史批次使用 currentSrc 直链、没有截图回退，所以主要时间更可能花在浏览、逐张分析、截图 RPC 重试和重复整理，而非传输字节数。旧记录没有分阶段计时，这是基于现有数据的判断，不是已测得的耗时占比。

## 下次采集步骤

1. 先按目标类别列出缺口，只搜索缺口类别。每个搜索词先快速看约 12 张结果卡；没有明显相关笔记或候选图就换词，不要把低产搜索词刷到几十张。已有明显过量类别时停止扩充。
2. 只打开主题明确相关的笔记。打开后一次记录笔记标题、作者、页面 URL 和搜索词；逐张浏览时只把明显可能保留的图片记为候选，记录原图序号、页面 IMG 的精确 currentSrc 和 naturalWidth/naturalHeight。不要在浏览器会话里写姿势、机位和布光长分析，也不要为了分析每张图调用截图。
3. 每 3–5 篇笔记，把候选逐行追加到 staging/candidates.jsonl，然后运行：

       python3 scripts/download_candidates.py

   下载器只对已观察到的 currentSrc 发普通 HTTPS GET；并发数固定为 4，每张限制 16 MiB，校验 WebP 容器和实际像素尺寸与记录值一致，成功后原子写入 images/ 并追加 staging/download-results.jsonl。只有与结果日志校验匹配的文件才会在重跑时跳过；没有检查点的同名文件会报冲突，避免把旧图算到新候选上。相同 URL 只记为重复项，前提是原下载成功且实际尺寸也匹配；否则重复项会记为失败。
4. 确认每个候选已下载后再离线筛选、去重和写摄影分析。每批使用独立 JSON 文件，避免覆盖已有记录；例如将新批次保存为 staging/manifest-next.json，再从 JSON 生成 Markdown：

       python3 scripts/render_manifest.py --input staging/manifest-next.json --output staging/manifest-next.md

   Markdown 是派生视图，不要分别手工维护两份。

## 候选记录字段

每行一个 JSON 对象，id 在整个 workspace 内唯一，例如 xhs-005-01。URL 必须从正常可见的小红书笔记和主图属性原样复制；以下地址仅展示字段形状，不能直接下载：

    {"batch_id":"2026-09-24-demo","id":"xhs-005-01","source_url":"https://www.xiaohongshu.com/explore/REPLACE","source_note_title":"笔记标题","source_author":"作者","search_keyword":"搜索词","image_index":1,"currentSrc":"https://example.invalid/REPLACE","natural_width":1080,"natural_height":1620}

不要改写、拼接或探测 CDN URL。不要保存或使用 Cookie、登录令牌或带凭据的 URL；遇到验证码、风险提示、403/404/429 或扫码门槛就保留已取得的候选并停止受阻页面，不要绕过。

## 目标和计时

- 第一阶段：30 张有效候选完成下载和 WebP 校验，活跃采集时间不超过 45 分钟。
- 完成筛选、摄影分析和 manifest 后：30 张可用成片不超过 90 分钟。
- 正常采集每张图片的截图 RPC 次数为 0；同一候选重跑不重复下载。
- 来源标题和作者至少 95% 在首次打开笔记时记录。
- 下载器和 Markdown 渲染器会把 `stage`、`batch_id(s)`、开始/结束时间、耗时、处理数量和状态追加到 `staging/batch-timings.jsonl`；下载行还包含成功/跳过/重复/失败数量、字节数和每秒完成数。浏览和离线筛选结束时，也向该文件追加一行相同时间字段的记录，并填入搜索卡、打开笔记、候选图或最终保留数。例如：

      {"stage":"browse","batch_id":"2026-09-24-demo","started_at":"2026-09-24T09:00:00+08:00","finished_at":"2026-09-24T09:18:00+08:00","elapsed_seconds":1080,"result_cards":24,"notes_opened":5,"images_analyzed":12,"candidate_count":10}
      {"stage":"curation","batch_id":"2026-09-24-demo","started_at":"2026-09-24T09:35:00+08:00","finished_at":"2026-09-24T09:52:00+08:00","elapsed_seconds":1020,"records_reviewed":10,"final_assets":8}

  首批按实测数据修正 3–5× 提速估计；当前还没有新批次数据证明该估计。
