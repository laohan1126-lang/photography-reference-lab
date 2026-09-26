"""Portable offline shooting packs and analysis bundles. No network assets or hidden publication."""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path
from .db import encode, now
from .models import AnalysisResult, PackInput, CandidatePackage, AnalysisPackage
from .policy import digest
from .service import Library, Problem


OFFLINE_HTML = r"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>离线拍摄包 · 参考实验室</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#111921;color:#edf2f3;font:16px/1.6 system-ui,sans-serif}
header{padding:16px 24px;position:sticky;top:0;background:#17242e;z-index:2;display:flex;gap:12px;flex-wrap:wrap;align-items:center}
button,select{font:inherit;background:#e0bb8c;color:#18212a;border:0;border-radius:7px;padding:8px 14px;cursor:pointer}
main{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(300px,1fr);gap:24px;padding:24px;max-width:1400px;margin:auto}
#photo{width:100%;height:78vh;object-fit:contain;background:#080e12}section{background:#1a2833;padding:20px;border-radius:12px;margin-bottom:14px}
h1{font-size:19px;margin:0 auto 0 0}h2{margin:0 0 10px;font-size:19px}h3{font-size:16px;color:#e0bb8c;margin:14px 0 4px}
p{white-space:pre-wrap;margin:6px 0}small{color:#9caeba}a{color:#e0bb8c}#empty{padding:30px}
@media(max-width:750px){main{display:block;padding:12px}#photo{height:55vh}header{padding:10px}}
</style></head><body><header><h1 id="title"></h1><small id="mode"></small><button id="prev">上一张</button>
<select id="picker" aria-label="选择参考"></select><button id="next">下一张</button></header><main><div><a id="original"><img id="photo" alt="独立参考图"></a><p id="caption"></p></div><div id="guide"></div></main>
<script id="data" type="application/json">__DATA__</script><script>
'use strict';const pack=JSON.parse(document.getElementById('data').textContent),refs=pack.references;let index=0;
const el=id=>document.getElementById(id);el('title').textContent=pack.project.character+' · 离线拍摄包';
el('mode').textContent=(pack.mode==='field'?'已确认现场卡':'灵感参考 · 非现场指令')+' / '+pack.created_at.slice(0,10);
refs.forEach((r,i)=>{const o=document.createElement('option');o.value=i;o.textContent=(i+1)+' · '+r.title;el('picker').append(o)});
function section(title,items){const s=document.createElement('section'),h=document.createElement('h2');h.textContent=title;s.append(h);
for(const [label,text]of items){if(!text||Array.isArray(text)&&!text.length)continue;const t=document.createElement('h3'),p=document.createElement('p');t.textContent=label;p.textContent=Array.isArray(text)?text.map((x,i)=>(i+1)+'. '+x).join('\n'):text;s.append(t,p)}el('guide').append(s)}
function render(){if(!refs.length){el('guide').textContent='此包没有参考。';return}const r=refs[index];el('picker').value=index;
el('photo').src=r.offline_preview;el('original').href=r.offline_original;el('caption').textContent=r.title+' · '+r.asset.width+' × '+r.asset.height+' · 作者：'+(r.source.author||'未记录');el('guide').replaceChildren();
if(pack.mode==='field'&&r.card){const c=r.card;section('现场口令',[['直接说',c.pose.verbal_cues],['摄影师动作',c.pose.photographer_steps],['安全与降级',c.pose.safety+'\n'+c.pose.fallback]]);
section('学习与准备',[['静态摆姿',c.pose.static_steps],['动作引导',c.pose.action_directing],['图中光线证据',c.lighting.visible_evidence],['布光推测（不是原作者布光事实）',c.lighting.interpretation],['现有器材方案',c.lighting.available_gear_plan]]);
section('后期路线：'+c.retouch.route,[['步骤',c.retouch.steps],['拍摄准备',c.retouch.capture_preparation],['AI背景说明',c.retouch.background_prompt]])}
else section('灵感收藏',[['喜欢与借鉴',r.preference],['借鉴维度',r.borrow],['状态','未作为现场卡发布；请勿把历史说明当成已验证事实。']]);
section('来源与追溯',[['发布页',r.source.page_url],['说明',r.source.rights_note],['文件 SHA-256',r.asset_sha]])}
el('prev').onclick=()=>{index=(index-1+refs.length)%refs.length;render()};el('next').onclick=()=>{index=(index+1)%refs.length;render()};el('picker').onchange=e=>{index=+e.target.value;render()};
document.onkeydown=e=>{if(e.target.tagName==='SELECT')return;if(e.key==='ArrowLeft')el('prev').click();if(e.key==='ArrowRight')el('next').click()};render();
</script></body></html>"""


def build_pack(library: Library, project_id: str, request: PackInput) -> Path:
    project = library.project(project_id)
    ids = list(dict.fromkeys(request.reference_ids))
    if not ids:
        with library.db.read() as con:
            rows = con.execute("SELECT id FROM refs WHERE project_id=? AND decision='keep' ORDER BY rowid", (project_id,))
            candidates = [library.reference(row[0]) for row in rows]
        ids = [r["id"] for r in candidates if r["field_ready"]] if request.mode == "field" else [r["id"] for r in candidates if r["lane"] == "inspiration"]
    if not ids: raise Problem(409, "没有符合条件的条目可导出")
    if len(ids) > 200: raise Problem(422, "单个离线包最多 200 张；请拆成多个拍摄包")
    refs, failures = [], []
    for ident in ids:
        ref = library.reference(ident)
        if ref["project_id"] != project_id: raise Problem(404, "Reference does not belong to project")
        if request.mode == "field" and not ref["field_ready"]:
            failures.append({"id": ident, "blockers": ref["blockers"]})
        elif request.mode == "inspiration" and ref["decision"] != "keep":
            failures.append({"id": ident, "reason": "not_selected"})
        elif not ref["asset"] or not library.assets.verify(ref["asset"]):
            failures.append({"id": ident, "reason": "image_integrity_failed"})
        refs.append(ref)
    if failures: raise Problem(409, "导出被阻止；不会默默跳过失效条目", failures)
    if sum(r["asset"]["bytes"] for r in refs) > 500 * 1024 * 1024:
        raise Problem(422, "原图总量超过 500 MiB，请拆包")
    out_dir = library.settings.data_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="shooting-pack-", suffix=".zip", dir=out_dir)
    import os
    os.close(fd)
    path = Path(name)
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            included = set()
            for ref in refs:
                ref["offline_preview"] = f"images/{ref['asset_sha']}-preview.jpg"
                ref["offline_original"] = f"images/{ref['asset_sha']}.{ref['asset']['ext']}"
                for variant, target in (("preview", ref["offline_preview"]), ("original", ref["offline_original"])):
                    if target not in included:
                        archive.write(library.assets.path(ref["asset"], variant), target)
                        included.add(target)
            snapshot = {"schema_version": 1, "created_at": now(), "project": project, "mode": request.mode, "references": refs}
            snapshot["snapshot_sha256"] = digest(snapshot)
            data = encode(snapshot).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            archive.writestr("index.html", OFFLINE_HTML.replace("__DATA__", data))
            archive.writestr("manifest.json", encode(snapshot))
            archive.writestr("README.txt", "解压后双击 index.html。图片与说明已包含在包内，不依赖网络。此包包含私人参考与可能带EXIF的来源文件，请勿自动公开转发。离线包是快照，不回写数据库；撤回服务器资料卡不会撤回已下载文件。\n")
        with library.db.transaction() as con:
            library.db.event(con, project_id, project_id, "pack.exported", {"mode": request.mode, "count": len(refs), "snapshot": snapshot["snapshot_sha256"]})
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def build_job_pack(library: Library, job_id: str) -> Path:
    bundle = library.job_bundle(job_id)
    out_dir = library.settings.data_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="job-bundle-", suffix=".zip", dir=out_dir)
    import os
    os.close(fd)
    path = Path(name)
    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for ref in bundle["references"]:
                if not ref["asset"] or not library.assets.verify(ref["asset"]):
                    raise Problem(409, "任务图片缺失或已损坏")
                target = f"images/{ref['asset_sha']}.{ref['asset']['ext']}"
                archive.write(library.assets.path(ref["asset"]), target)
                ref["bundle_image"] = target
            archive.writestr("job.json", encode(bundle))
            archive.writestr("AGENT_TASK.md", bundle["agent_instructions"])
            archive.writestr("candidate-package.schema.json", encode(CandidatePackage.model_json_schema()))
            archive.writestr("analysis-package.schema.json", encode(AnalysisPackage.model_json_schema()))
            archive.writestr("manifest.example.json", encode({"schema_version": 2, "job_id": job_id,
                "batch_id": "replace-with-stable-batch-id", "candidates": [],
                "execution_report": {"producer": "replace-with-real-agent", "status": "blocked",
                    "summary": "模板未执行，不能当成成功回执", "source_checks": [], "query_log": [], "gaps": ["尚未执行"]}}))
            archive.writestr("analysis-result.schema.json", encode(AnalysisResult.model_json_schema()))
            archive.writestr("README.txt", "阅读 job.json；逐张打开 images/ 中的独立原图。不得凭标题或分类编造动作。analysis-result.schema.json 定义单条 result；返回 analysis.json 格式见 docs/WORKER_PROTOCOL.md。字段不全或状态过期会被拒绝。所有资料卡仍需用户确认。\n")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise
