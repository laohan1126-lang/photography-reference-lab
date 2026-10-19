"""Task-scoped recall: inspect source relevance, then expose only visual matches.

The frozen experiment collectors remain historical. Text routes discovery; it
never confirms a character or costume. This module never writes the live library.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import parse_qs, urlsplit

import httpx
from PIL import Image

from tools.learning_v1 import ROOT, digest
from tools.learning_v1_human import atomic_write, json_bytes

XHS_NOTE_JS = r"""(() => {
 const root = document.querySelector('.note-detail-mask .note-container');
 if (!root) return {error:'visible_note_container_missing'};
 const text = root.innerText;
 const login = Array.from(document.querySelectorAll('[role="dialog"], .login-container, .login-box'))
   .some(x => x.getBoundingClientRect().width && /登录|登入|扫码/.test(x.innerText));
 if (login) return {error:'login_required'};
 const seen = new Set();
 const images = Array.from(root.querySelectorAll('.swiper-slide:not(.swiper-slide-duplicate) img'))
   .filter(x => x.naturalWidth >= 400 && x.naturalHeight >= 400)
   .map(x => ({url:x.currentSrc || x.src,width:x.naturalWidth,height:x.naturalHeight}))
   .filter(x => !seen.has(x.url) && seen.add(x.url));
 return {page_url:location.origin+location.pathname,text,images};
})()"""


def save(path: Path, data: object):
    atomic_write(path, json_bytes(data))


def load(path: Path):
    return json.loads(path.read_text('utf-8-sig'))


def assess_search(snapshot: dict, query: str, scope: dict) -> dict:
    """A URL and search-box match establish provenance, not result relevance."""
    parsed = urlsplit(snapshot.get('url', ''))
    params = parse_qs(parsed.query)
    actual = (params.get('q') or params.get('keyword') or [''])[0]
    if actual != query or snapshot.get('search') != query:
        return {'action':'STOP_STALE_QUERY', 'confirmed_count':0}
    if snapshot.get('login_required'):
        return {'action':'STOP_LOGIN_REQUIRED', 'confirmed_count':0}
    visible = snapshot.get('visibleMain') or snapshot.get('visibleText') or ''
    if any(text in visible for text in ('找不到與這個搜尋條件相符的 Pin', 'No Pins found', 'No results found')):
        return {'action':'CHANGE_QUERY_OR_SOURCE', 'confirmed_count':0, 'result_state':'EXPLICIT_NO_RESULTS'}
    rewrite = re.search(r'這是我們針對\s*(.*?)\s*找到的內容', visible)
    if rewrite and rewrite.group(1).casefold() != query.casefold():
        return {'action':'REVIEW_QUERY_REWRITE', 'confirmed_count':0,
                'requested_query':query, 'effective_query':rewrite.group(1),
                'note':'Search box and URL match, but the platform visibly rewrote the query.'}
    texts = [c.get('text', '') for c in snapshot.get('cards', [])]
    hits = sum(any(a.casefold() in text.casefold() for a in scope.get('character_aliases', [scope['character']]))
               and any(a.casefold() in text.casefold() for a in scope.get('costume_aliases', [scope['costume']]))
               for text in texts)
    return {'action':'INSPECT_TARGET_DETAILS' if hits else 'SAMPLE_THEN_CHANGE_SOURCE',
            'scope_text_hits':hits, 'sample_count':len(texts), 'confirmed_count':0,
            'note':'Text is discovery routing only; missing text is not a visual mismatch.'}


def after_visual_sample(states: list[str]) -> str:
    if not states:
        return 'NEEDS_VISUAL_SAMPLE'
    return 'CONTINUE_TARGET_SOURCE' if 'CONFIRMED' in states else 'CHANGE_QUERY_OR_SOURCE'


def capture_note(bsk: str, session: str, folder: Path, expected_page: str, limit: int = 3,
                 errors: list | None = None) -> list[dict]:
    """Read only currently rendered note DOM. No bootstrap state, cookies or API.

    A single unusable slide must not discard slides already received from the
    same note. When ``errors`` is supplied, per-image failures are recorded and
    the remaining slides are still attempted; page/login/binding errors still stop.
    """
    result = subprocess.run([bsk,'evaluate','--session',session,'--json',XHS_NOTE_JS],
                            capture_output=True,text=True,encoding='utf8',timeout=30,check=True)
    envelope = json.loads(result.stdout)
    data = envelope.get('value', {})
    if envelope.get('ok') is not True or not isinstance(data,dict) or data.get('error'):
        raise ValueError('Note unavailable or login required')
    page = data.get('page_url','')
    if page != expected_page or not re.fullmatch(r'https://www\.xiaohongshu\.com/explore/[a-f0-9]{24}', page):
        raise ValueError('Note page binding mismatch')
    rows = []
    for index,image in enumerate(data.get('images', [])[:limit],1):
        try:
            url = image['url']; parsed = urlsplit(url)
            if parsed.scheme != 'https' or not (parsed.hostname or '').endswith('.xhscdn.com'):
                raise ValueError('Untrusted image host')
            response = httpx.get(url, timeout=20, follow_redirects=False)
            response.raise_for_status()
            content = response.content
            if len(content) > 20*1024*1024:
                raise ValueError('Image too large')
            sha = hashlib.sha256(content).hexdigest()
            import io
            with Image.open(io.BytesIO(content)) as im:
                im.load(); width,height = im.size; fmt = im.format
            if (width,height) != (image['width'],image['height']):
                raise ValueError('Received dimensions differ from the rendered image')
            ext = {'JPEG':'jpg','PNG':'png','WEBP':'webp','AVIF':'avif'}.get(fmt)
            if ext is None:
                raise ValueError('Unsupported original image type')
            target = folder/'images'/f'{sha}.{ext}'
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
                raise ValueError('Immutable file conflict')
            if not target.exists():
                with target.open('xb') as stream: stream.write(content)
            rows.append({'asset_sha':sha,'original_path':str(target.resolve()),'page_url':page,
                         'image_url':url,'width':width,'height':height,'source_text':data['text'],
                         'image_index':index,'visual_state':'UNREVIEWED'})
        except (ValueError,OSError,httpx.HTTPError) as exc:
            if errors is None:raise
            errors.append({'page_url':page,'image_index':index,
                           'observed_url':str(image.get('url',''))[:1000],
                           'error':type(exc).__name__+': '+str(exc)[:200]})
    return rows


def confirmed_results(records: list[dict], reviews: list[dict], scope: dict) -> list[dict]:
    by_sha = {r['asset_sha']:r for r in records}
    output=[]; seen=set()
    for review in reviews:
        sha=review.get('asset_sha');r=by_sha.get(sha)
        if not r or sha in seen: continue
        if (review.get('opened_sha')!=sha or review.get('context_sha')!=digest(scope)
                or not review.get('producer') or review.get('actor')!='ai'):
            continue
        if not all(review.get(k)=='match' for k in ('identity','costume')):
            continue
        if review.get('kind')!='cosplay_photo' or not all(review.get('evidence',{}).get(k) for k in ('kind','identity','costume')):
            continue
        path=Path(r['original_path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError('Reviewed image changed')
        seen.add(sha);output.append({**r,'model_review':review})
    return output


def render(folder: Path, records: list[dict], reviews: list[dict], scope: dict):
    selected=confirmed_results(records,reviews,scope)
    public=folder/'public';public.mkdir(exist_ok=True)
    figures=[]
    for i,r in enumerate(selected,1):
        page_url=urlsplit(r['page_url'])
        if page_url.scheme not in ('https','http') or not page_url.hostname or page_url.username or page_url.password:
            raise ValueError('Unsafe source URL')
        source=Path(r['original_path']);target=public/source.name
        if not target.exists(): target.write_bytes(source.read_bytes())
        elif hashlib.sha256(target.read_bytes()).hexdigest()!=r['asset_sha']: raise ValueError('Public copy conflict')
        v=r['model_review']
        figures.append(f'<article><h2>{i:02d} · {html.escape(v["reference_use"])}</h2><img src="{target.name}" alt="已逐图核对的公孙离祈雪灵祝摄影"><p>{html.escape(v["visible_evidence"])}</p><p>{html.escape(v["shooting_note"])}</p><p>发布者：{html.escape(r.get("publisher","未知"))} · {html.escape(r.get("attribution_note","原作者身份未独立核验"))}</p><a href="{html.escape(r["page_url"],quote=True)}" target="_blank" rel="noreferrer">查看实际来源</a></article>')
    body=''.join(figures) or '<p>当前没有通过角色与版本核验的图片；不以错误图片凑数。</p>'
    title=html.escape(scope['character']+' · '+scope['costume']+' · 场照参考')
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>body{{margin:0;background:#f2efe8;color:#292b26;font:17px/1.7 system-ui}}main{{max-width:1000px;padding:28px;margin:auto}}article{{padding:24px 0;border-top:1px solid #bdb9ad}}h1{{font-size:27px}}h2{{font-size:21px}}img{{display:block;max-width:100%;max-height:85vh;margin:auto}}a{{color:#235e48}}p{{max-width:800px}}</style><main><h1>{title}</h1><p>本次找回 {len(selected)} 张，已由Agent逐图核对角色与服装。原失败批次无需评价，此页只供看参考，没有评分任务。</p><p>这是模型视觉核验，不代替你的审美选择。图片保留收到的原始字节，只用于个人参考；发布者与出镜、摄影署名按来源分别记录。</p>{body}</main></html>'
    atomic_write(public/'index.html',page.encode('utf8'))
    save(folder/'confirmed.json',selected)
    return {'confirmed':len(selected),'received':len(records),'entry':str(public/'index.html')}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',choices=['assess','capture','render'])
    ap.add_argument('--folder',type=Path,required=True)
    ap.add_argument('--session');ap.add_argument('--page');ap.add_argument('--limit',type=int,default=3)
    ap.add_argument('--snapshot',type=Path);ap.add_argument('--query')
    ap.add_argument('--bsk',default=str(Path.home()/'.local/bin/bsk.exe'))
    args=ap.parse_args();folder=args.folder.resolve()
    if not folder.is_relative_to(ROOT/'.local'): raise ValueError('Keep experiment inside repository .local')
    if args.action=='assess':
        result=assess_search(load(args.snapshot),args.query,load(folder/'scope.json'))
        save(folder/'last-search-assessment.json',result);print(json.dumps(result,ensure_ascii=False))
    elif args.action=='capture':
        if not 1<=args.limit<=5:raise ValueError('Inspect only a small source sample')
        rows=capture_note(args.bsk,args.session,folder,args.page,args.limit)
        name=urlsplit(args.page).path.rsplit('/',1)[1]
        save(folder/f'note-{name}.json',rows);print(json.dumps({'received':len(rows),'note':name}))
    else:
        print(json.dumps(render(folder,load(folder/'received.json'),load(folder/'model-reviews.json'),load(folder/'scope.json')),ensure_ascii=False))


if __name__=='__main__':main()
