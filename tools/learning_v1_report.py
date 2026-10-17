"""Local static read-only review pages and honest experiment reports."""
from __future__ import annotations

from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import random
from urllib.parse import quote

from tools.learning_v1 import (EXPERIMENT, FEATURES, ROOT, SEED, check_freeze,
                               load_json, rank_pool, reviewed_search, save_json,
                               source_group)

STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f5f2ed;color:#202a30;font:16px/1.7 system-ui,'Microsoft YaHei',sans-serif}
main{max-width:1160px;margin:auto;padding:36px 24px 72px}h1{font-size:32px;line-height:1.3;margin:12px 0 18px}h2{margin-top:36px}
p{max-width:86ch}a{color:#31586b;overflow-wrap:anywhere}nav{display:flex;gap:20px;flex-wrap:wrap;margin:18px 0 30px}
.lead{background:#fff;padding:22px 26px;border-left:4px solid #42636d}.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}figure{background:#fff;margin:0 0 22px;border:1px solid #ddd8d0;border-radius:8px;overflow:hidden}
figure img{display:block;width:100%;height:520px;object-fit:contain;background:#e9e7e3}figcaption{padding:16px;overflow-wrap:anywhere}
small,.muted{color:#606b72}details{padding:12px 0}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}table{border-collapse:collapse;width:100%;background:#fff}td,th{text-align:left;padding:10px;border-bottom:1px solid #ddd;vertical-align:top}
@media(max-width:600px){main{padding:22px 12px 50px}h1{font-size:25px}.columns{gap:10px}figure img{height:300px}figcaption{padding:10px;font-size:13px}.columns h2{font-size:20px}}
"""


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def document(title: str, content: str) -> str:
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' \
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' file: data:; style-src \'unsafe-inline\'; connect-src \'none\'; form-action \'none\'">' \
           f'<title>{escape(title)}</title><style>{STYLE}</style></head><body><main>{content}</main></body></html>'


def image_card(record: dict, ordinal: int, label: str, *, blind: bool = False) -> str:
    relative = os.path.relpath(record["original_path"], EXPERIMENT).replace("\\", "/")
    src = quote(relative, safe="/:")
    caption = f'<strong>{ordinal:02d} · {escape(label)}</strong>'
    if not blind:
        source = (record.get("source") or {}).get("page_url") or next(iter(record.get("source_pages", [])), "")
        if source.startswith(("https://", "http://")):
            caption += f'<p><a href="{escape(source)}" target="_blank" rel="noopener noreferrer">原发布页</a></p>'
        notes = record.get("visual", {}).get("evidence", [])
        caption += '<p>' + escape('；'.join(notes)) + '</p>'
        caption += '<small>' + escape(record.get("visual", {}).get("kind", "unknown")) + ' · 身份/服装结论见来源记录</small>'
        caption += '<details><summary>来源与观察记录</summary><pre>' + escape(json.dumps(record, ensure_ascii=False, indent=2)) + '</pre></details>'
    return f'<figure><a href="{src}" target="_blank"><img src="{src}" alt="{escape(label)} 原始图片" loading="lazy"></a><figcaption>{caption}</figcaption></figure>'


def blind_page(predictions: dict, all_records: list[dict]) -> dict:
    strategies = ["baseline1", "candidate2"]
    random.Random(SEED).shuffle(strategies)
    labels = {r["asset_sha"]: f'R{index+1:02d}' for index, r in enumerate(all_records)}
    mapping = {name: method for name, method in zip(("A", "B"), strategies)}
    save_json(EXPERIMENT / "blind-internal-mapping.json", {"seed": SEED, "methods": mapping, "labels": labels})
    content = '<a href="index.html">返回实验总览</a><h1>星野露比 · 留出盲评</h1>'
    content += '<div class="lead"><p>比较 A 与 B：哪一列前面的照片更值得你保留、借鉴？也可以判断两者没有差别，或两者都不好。</p>'
    content += '<p>两列使用同一个候选池和同一套图片。排名由冻结的程序输出；未人工重排。这里只浏览，不保存 K/I/M/X，也不会启动生成。</p>'
    content += '<p>R 编号对应同一张原图。角色和服装证据不足的候选仍待核验，照片出现不等于已经通过验收。</p></div><div class="columns">'
    for name in ("A", "B"):
        ranked = predictions[mapping[name]]
        content += f'<section><h2>序列 {name}</h2>'
        content += ''.join(image_card(r, i+1, labels[r["asset_sha"]], blind=True) for i, r in enumerate(ranked))
        content += '</section>'
    content += '</div><h2>原始候选及来源</h2><p>这里保留所有原始候选，包括重合后退出留出计分的图片；不影响上方两列排名。</p><div class="cards">'
    content += ''.join(image_card(r, i+1, labels[r["asset_sha"]]) for i, r in enumerate(all_records)) + '</div>'
    (EXPERIMENT / "ruby-blind-review.html").write_text(document("星野露比留出盲评", content), encoding="utf-8")
    arrival = '<a href="ruby-blind-review.html">返回盲评</a><h1>原入库顺序基线</h1><p>相同候选池，不做偏好排序；不以本页次序作为真人审美评分。</p><div class="cards">'
    arrival += ''.join(image_card(r, i+1, labels[r["asset_sha"]]) for i, r in enumerate(predictions["baseline0"])) + '</div>'
    (EXPERIMENT / "ruby-arrival-order.html").write_text(document("原入库顺序", arrival), encoding="utf-8")
    return {"page": "ruby-blind-review.html", "same_candidate_sha_set": set(r["asset_sha"] for r in predictions["baseline1"]) == set(r["asset_sha"] for r in predictions["candidate2"]),
            "ranking_equal": [r["asset_sha"] for r in predictions["baseline1"]] == [r["asset_sha"] for r in predictions["candidate2"]]}


def audit_markdown(audit: dict) -> str:
    return f'''# Learning Loop V1 样本审计

这份统计来自一致性 SQLite 快照。原图、日用数据库及人工决定没有用作可写实验输入。

| 口径 | 实际数量 | 能说明什么 |
|---|---:|---|
| 独立图片 SHA | {audit['independent_asset_shas']} | 不等于有这么多训练标签 |
| 角色引用 / 跨项目额外引用 | {audit['reference_rows']} / {audit['cross_project_extra_uses']} | 同一张图不会重复计为独立样本 |
| 明确人工来源的会话操作 / 独立 SHA | {audit['explicit_origin_session_actions']} / {audit['explicit_origin_session_unique_shas']} | 去除了重复操作计数 |
| 当前选择和会话来源可核对的 K/X 图片 | {audit['session_or_reference_supported_project_use_shas']} | 是项目用途监督，不能直接当喜欢/讨厌 |
| 人工原文反馈 | {audit['human_text_feedback_count']} | 逐条保留，规则原因与审美批评分开 |
| 明确喜欢的原图 | {audit['explicit_aesthetic_positive_shas']} | 仅用作训练端正例，不再给自己做测试 |
| 结构化明确审美负例 | {audit['structured_aesthetic_negative_shas']} | 不代表没有文字批评，见 label-caveats.json |
| 原库已有图像绑定视觉特征 | {audit['image_bound_annotation_count']} | 全部是 AI 观察，不是人工真值 |
| K/X 与原有特征的重合 | {audit['supported_project_use_shas_with_visual_features']} | 数量看似足够，输入和标签实际上尚未连上 |
| 人工 Dot 待筛选择 | {audit['human_study_count']} | 与角色 K/X 独立，不重复升级成审美评分 |
| 有具体发布页的图片 | {audit['known_post_source_shas']} | 发布页不一定是原摄影师/原拍摄组 |
| 已验证原图 SHA | {audit['integrity_verified']} | 所有接收字节均与身份一致 |
| 保守分组 | {audit['groups']['group_count']} | 同角色任务、同来源、近图和未知来源保守连通，不是真实拍摄组数量 |

原始决定分布：{json.dumps(audit['raw_decisions'], ensure_ascii=False)}。有明确当前来源的决定：{json.dumps(audit['explicit_origin_decisions'], ensure_ascii=False)}。

项目 {audit['project_count']} 个，其中活跃 {audit['active_project_count']} 个。声明角色清单和服装版本保留在 JSON。含“测试”的项目不进入学习目标。events 中 actor=human 的记录含测试和可由接口写入的记录，不能只凭这个字段把全部点击升级为可靠标签。

## 训练资格与补证

本轮另外实际打开 16 张按“角色 × K/X，各取最前两个 SHA”预选的原图，并重看唯一明确喜欢的照片，共 17 张。只补描述性视觉特征，不增加虚构的喜欢标签。两条原文明示的负面审美评价保留为带范围的文字记录；默认 false 的复选框没有被重写。

单个明确正例不足以形成可检验的二分类审美模型。结果为 **NOT_TRAINABLE**；执行的替代方法是固定等权特征的正例检索。没有梯度更新，没有把默认画像数字当标签。

一个实际反例是：带“无全身姿态参考”原因的原图，头部和两只鞋均可见。保留 X 选择，但该原因不能当作“画面裁掉身体”的视觉真值。另有人工 K 对应盔甲特写和近白背景照片，因此不能学习“非全身/白底一律不要”。详见 label-caveats.json。

初次审计把无引用资产的字典查询写成了会新增键的操作，导致额外引用数出现负值。首轮文件保留为 dataset-audit-initial.json；已在同一快照上修正，正确额外引用为 {audit['cross_project_extra_uses']}。没有重新抓取日用数据掩盖差异。
'''


def render_all() -> dict:
    check_freeze()
    audit = load_json(EXPERIMENT / "dataset-audit.json")
    offline = load_json(EXPERIMENT / "offline-evaluation.json")
    holdout = load_json(EXPERIMENT / "ruby-evaluation.json")
    predictions = load_json(EXPERIMENT / "ruby-predictions.json")
    all_ruby = load_json(EXPERIMENT / "ruby-pool.json")
    blind = blind_page(predictions, all_ruby)
    (EXPERIMENT / "dataset-audit.md").write_text(audit_markdown(audit), encoding="utf-8")
    version_rows = []
    version_content = '<a href="index.html">返回实验总览</a><h1>指定版本 · 实际检索与逐图观察</h1><p>以下保留所有候选和失败，不用摄影式外观代替角色或服装验证。来源标题、人工选择与本轮 AI 观察分别保留。</p>'
    model = load_json(EXPERIMENT / "model.json")
    for key, name in (("zhaojun", "王昭君 · 长夜焕生"), ("tohru", "托尔 · 婚纱")):
        pool = reviewed_search(key)
        manifest = load_json(EXPERIMENT / "search" / key / "manifest.json")
        replay = {s: rank_pool(pool, s, model) for s in ("baseline0", "baseline1", "candidate2")}
        save_json(EXPERIMENT / "search" / key / "same-pool-replay.json", replay)
        source_extra = 1 if key == "zhaojun" else 0
        summary = {"task": name, "search_queries": manifest["query_count_including_prior"] + source_extra,
                   "images_opened": len(pool), "types": dict(Counter(r["visual"]["kind"] for r in pool)),
                   "costume_match": sum(r["visual"]["costume"] == "match" and r["visual"]["kind"] == "cosplay_photo" for r in pool),
                   "costume_mismatch": sum(r["visual"]["costume"] == "mismatch" for r in pool),
                   "identity_or_version_unknown": sum(r["visual"]["identity"] == "uncertain" or r["visual"]["costume"] == "uncertain" for r in pool),
                   "fully_verified_exact_matches": sum(r["rule_state"] == "candidate" for r in replay["baseline1"]),
                   "aesthetic_benefit": "NOT_PROVEN", "recall": {"value": None, "reason": "No exhaustive labelled result universe"}}
        version_rows.append(summary)
        version_content += f'<h2>{escape(name)}</h2><p>{escape(json.dumps(summary, ensure_ascii=False))}</p><div class="cards">'
        version_content += ''.join(image_card(r, i+1, r["id"]) for i, r in enumerate(pool)) + '</div>'
    save_json(EXPERIMENT / "specified-version-evaluation.json", version_rows)
    (EXPERIMENT / "specified-version-review.html").write_text(document("指定版本检索", version_content), encoding="utf-8")
    summary = {"outcome": "NOT_PROVEN", "engineering_experiment": "PARTIAL", "aesthetic_training": "NOT_TRAINABLE",
               "prototype_count": 1, "production_preference_sorting": "UNCHANGED", "specified_versions": version_rows,
               "ruby": holdout, "blind_comparison": blind}
    save_json(EXPERIMENT / "result-summary.json", summary)
    content = '<small>PHOTOGRAPHY REFERENCE LAB / LEARNING LOOP V1</small><h1>这轮学到了什么，哪些还没有被证明</h1>'
    content += '<div class="lead"><p><strong>结论：审美提升 NOT_PROVEN，二分类训练 NOT_TRAINABLE。</strong></p><p>完成真实数据审计、任务范围绑定的查询计划、正例检索、分组重放和冻结后露比测试。现有日用画像、K/I/M/X 和默认排序保持原样。</p></div>'
    content += '<nav><a href="ruby-blind-review.html">进入露比盲评</a><a href="specified-version-review.html">指定版本候选</a><a href="ruby-arrival-order.html">入库顺序基线</a><a href="dataset-audit.md">样本审计</a><a href="technical-retrospective.md">技术复盘与复现</a></nav>'
    content += f'<h2>实际样本</h2><p>{audit["independent_asset_shas"]} 张独立原图，{audit["explicit_origin_session_unique_shas"]} 张有明确人工会话来源，{audit["session_or_reference_supported_project_use_shas"]} 张形成可核对的 K/X 用途标签。原有视觉特征与这些用途标签的重合为 0。本轮实际补看 17 张，唯一明确喜欢的照片只留在训练端。</p>'
    content += f'<h2>露比留出</h2><p>实际收到并逐图检查 {holdout["received_count"]} 张；排除可检测到的原库重合后，{holdout["holdout_eligible_count"]} 张进入同池对照。所有冻结文件的哈希仍一致，尚无本轮真人审美评分。</p>'
    content += '<h2>同组隔离和消融</h2><p>规则门槛与视觉观察由三种策略共享。差别是入库顺序、按证据状态排序、以及再加入单个正例的相似度。参数没有通过数据拟合；K/X 的代理指标不能证明审美提升。</p><pre>'
    content += escape(json.dumps({"folds": offline["folds"], "rule_evaluation": offline["rule_evaluation"], "ablations": offline["ablations"]}, ensure_ascii=False, indent=2)) + '</pre>'
    content += '<h2>需要保留的失败</h2><p>指定服装匹配尚未证明；小红书实际显示登录遮罩；少量旧反馈文字与可见画面存在冲突；未知来源无法证明真实拍摄组独立。完整图、原文、查询日志和失败记录均留在本地实验目录。</p>'
    (EXPERIMENT / "index.html").write_text(document("Learning Loop V1 实验结果", content), encoding="utf-8")
    return {"index": str(EXPERIMENT / "index.html"), "blind_review": str(EXPERIMENT / "ruby-blind-review.html"),
            "outcome": summary["outcome"], "blind": blind}
