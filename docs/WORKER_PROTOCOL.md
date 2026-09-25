# 本地 Agent / 执行器协议

## 通用约束

网站先建立任务。下载任务 ZIP 后，阅读 `job.json` 中的完整项目、brief、notes 和版本快照。采集任务的初始 queries 只是起点，需按自由要求自行扩展。不能因搜索“cosplay”就把返回的器材或场地归入人物姿势。

每张图单独打开，不以九宫格、标题或旧 observed_pose 代替实际图像。保留原发布页与作者；图片直链仅是下载出处，不能冒充发布页。停止访问受阻页面，不导出 Cookie、不调用隐藏接口、不改写/猜测 CDN 尺寸路径。

API 可用 `Authorization: Bearer <本机口令>`，口令仅由本地环境提供。浏览器用 HttpOnly 会话及 CSRF，不把管理员口令写进前端或 JSON 包。

## 候选包

ZIP 根目录 `manifest.json`，配套独立图片目录。例如：

```json
{
  "schema_version": 1,
  "batch_id": "2026-09-25-manual-a",
  "candidates": [
    {
      "id": "source-post-01-image-01",
      "file": "images/reference-01.jpg",
      "title": "待检查的候选标题",
      "source": {
        "page_url": "https://example.org/posts/reference-01",
        "image_url": "https://example.org/images/reference-01.jpg",
        "author": "已记录的作者",
        "title": "原发布页标题",
        "search_query": "本次检索词",
        "search_category": "仅检索意图，不是图片类型",
        "rights": "unknown",
        "rights_note": "",
        "source_confirmed": false,
        "obtained_as": "as_received"
      }
    }
  ]
}
```

网址是结构示例，不是可下载素材。导入时可以在网站选择对应 collection job；也可向 `POST /api/projects/{id}/imports/candidates` 发送 multipart `file` 和可选 `job_id`。

导入永远创建待选候选，不因为包里自称高质量而设 KEEP 或 verified；来源确认也会清零。ZIP 路径、大小、数量、实际格式和解码尺寸会被检查。超过单个上传 64 MiB / 单图 20 MiB 请拆包；每批总解压量限制 200 MiB，最多 2000 个 ZIP 项。重复包返回 existing；部分失败返回逐项 errors，而不是伪造整体成功。

## 分析包与返回结果

只分析用户 KEEP 的条目。任务 ZIP 包含：

- `job.json`：项目要求、引用 ID、创建时 revision、asset_sha 和每张图的 `bundle_image`。
- `images/`：逐张独立来源文件。
- `analysis-result.schema.json`：单条 `result` 的完整 JSON Schema。

按 Schema 返回完整 review 与 card；不能确定的布光写作推测，动作不清或图片不相关时 card 为 null。review 的 observations 必须描述看得见的内容，而不是从搜索标签复制。critical_uncertainties 不能为了通过验收而清空。

导入 JSON 的外层结构：

```json
{
  "schema_version": 1,
  "job_id": "从 job.json 读取真实 ID",
  "items": [
    {
      "reference_id": "真实 Reference ID",
      "expected_revision": 3,
      "producer": "执行器名称 / 模型 / 本轮标识",
      "result": {
        "review": {
          "asset_sha": "任务图片实际 SHA-256",
          "kind": "unknown",
          "visible_person": false,
          "pose_readable": false,
          "single_image": false,
          "sufficiently_clear": false,
          "character_match": "unknown",
          "observations": ["需替换成实际打开图片后确认的内容"],
          "critical_uncertainties": ["尚未完成逐图观察"]
        },
        "card": null
      }
    }
  ]
}
```

示例故意是未通过状态，不能原样当成有效核验。完整 card 字段见生成的 Schema，或者运行 `python -m ref_lab schema`。

网站“导入分析结果”逐条校验图片哈希、项目、版本和任务快照。错误条目不覆盖已有结果；成功条目也只是草稿。任务 completed_ids 记录成功导入的核验结果，**包括“不适合作为资料卡”的分析结论**，不等于全部变成可用现场卡。用户仍需核对来源及最终资料卡。

## 口令与资料卡内容

pose 要包含可直接说出口的短句、静态摆姿、动作引导、摄影师动作、安全边界和降级方法。方向需明确是人物左右还是画面左右；不要求被摄者忍痛扭转。

lighting 分 visible_evidence、interpretation、confidence、available_gear_plan。推测不是原作者设备参数；按项目现有器材给可尝试方案，不默认添加多灯或复杂场地。

retouch 为 none / cleanup / composite。composite 必须包含拍摄准备与 background_prompt：视角、地平线、光位、人物位置和留白匹配实拍人物。保持人物原片；没有必要时不换背景。本系统不会自动生成背景或调用 Photoshop。

## 本机采集与付费分析命令

```bash
python -m ref_lab collect --job JOB_ID --cdp http://127.0.0.1:9222 --search
python -m ref_lab analyze --job JOB_ID --confirm-external-images
```

CDP 只支持本机地址，调试端口不要暴露公网。付费分析需自行配置 `OPENAI_API_KEY` 与可用、支持图片和结构化结果的 `LAB_ANALYSIS_MODEL`，并确认有权向外部 API 发送这些参考图。命令不会凭 ChatGPT Pro 登录自动取得 API 权限。未配置、受阻或失败时如实保留 blocked/failed，不伪造结果。

Notion 任务摘要同步：配置 `NOTION_API_TOKEN` 和已向 integration 授权的 `NOTION_PARENT_PAGE_ID`，再执行 `python -m ref_lab sync-notion --task docs/tasks/任务.md --commit 实际提交SHA`。重复同一摘要不会重复创建；网络结果不明时停止自动重试，需先检查 Notion，防止重复页面。
