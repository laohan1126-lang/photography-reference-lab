"""Opt-in visible-browser capture. No hidden endpoints, cookie exports, CDN rewrites or challenge bypass."""
from __future__ import annotations

from urllib.parse import urlsplit, quote
import httpx
from .models import CandidateInput, Source
from .policy import digest
from .service import Library, Problem

CDN_DOMAINS = ("pinimg.com", "xhscdn.com")
VISIBLE_IMAGES = """() => Array.from(document.images).filter(img => {
 const r=img.getBoundingClientRect(),s=getComputedStyle(img);
 return r.width>100 && r.height>100 && r.bottom>0 && r.top<innerHeight && r.right>0 && r.left<innerWidth
 && s.visibility!=='hidden' && s.display!=='none' && img.naturalWidth>=400 && img.naturalHeight>=400;
}).map(img=>({currentSrc:img.currentSrc,width:img.naturalWidth,height:img.naturalHeight,
 title:img.alt||'',page_url:img.closest('a')?.href||location.href}))"""


def allowed_image_url(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return (parsed.scheme == "https" and not parsed.username and not parsed.password and parsed.port in {None, 443}
            and any(host == suffix or host.endswith("." + suffix) for suffix in CDN_DOMAINS))


def download_observed(url: str, limit: int, *, transport=None) -> bytes:
    if not allowed_image_url(url): raise ValueError("只下载明确允许的平台 CDN 上实际观察到的 HTTPS 图片")
    with httpx.Client(timeout=25, follow_redirects=False, transport=transport, trust_env=False) as client:
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise Problem(409, f"来源 HTTP {response.status_code}；停止受阻页面，不绕过验证")
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > limit: raise ValueError("Image exceeds download limit")
            return bytes(data)


def capture_page(library: Library, job_id: str, page, *, query: str = "", maximum: int = 30, transport=None) -> dict:
    job = library.job(job_id)
    report = {"created": 0, "existing": 0, "ignored": 0}
    page_url = page.url
    host = (urlsplit(page_url).hostname or "").lower()
    if not any(host == domain or host.endswith("." + domain) for domain in ("pinterest.com", "xiaohongshu.com")):
        raise ValueError("当前页面必须是 Pinterest 或小红书的正常可见页面")
    for record in page.evaluate(VISIBLE_IMAGES)[:maximum]:
        url = record.get("currentSrc", "")
        if not allowed_image_url(url):
            report["ignored"] += 1
            continue
        image = download_observed(url, library.settings.max_upload_bytes, transport=transport)
        asset = library.ingest_asset(image, "observed-image")
        # EXIF rotation can swap dimensions, so compare sorted dimensions.
        if sorted((asset["width"], asset["height"])) != sorted((record["width"], record["height"])):
            raise Problem(409, "下载图片与页面观察尺寸不符；不猜测其他 CDN 地址")
        source = Source(page_url=record.get("page_url") or page_url, image_url=url,
                        title=str(record.get("title", ""))[:400], search_query=query[:400], obtained_as="platform_variant")
        result = library.add_candidate(job["project_id"], CandidateInput(asset_sha=asset["id"], source=source,
                    import_key="visible:" + digest({"url": url, "sha": asset["id"]}), job_id=job_id), actor="visible_browser")
        report["created" if result["created"] else "existing"] += 1
    return report


def collect_job(library: Library, job_id: str, cdp_url: str, *, search: bool = False) -> dict:
    parsed = urlsplit(cdp_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
        raise ValueError("CDP 仅连接你本机的 HTTP 调试端口；不要暴露此端口到公网")
    from playwright.sync_api import sync_playwright
    job = library.job(job_id)
    if job["kind"] != "collection": raise Problem(409, "Not a collection job")
    job = library.transition_job(job_id, "running", job["revision"], "本地可见浏览器采集；遇到门槛即停止", actor="worker")
    reports = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(cdp_url, timeout=15000)
            if not browser.contexts or not browser.contexts[0].pages:
                raise Problem(409, "没有可接管的正常浏览器页面")
            page = browser.contexts[0].pages[-1]
            queries = job["queries"] if search else [""]
            for query in queries:
                if search:
                    response = page.goto("https://www.pinterest.com/search/pins/?q=" + quote(query), wait_until="domcontentloaded", timeout=30000)
                    if response and response.status >= 400:
                        raise Problem(409, f"页面返回 HTTP {response.status}；保留已采集部分并停止")
                    page.wait_for_timeout(1200)
                # This is only a stop check; it never solves a challenge or obtains credentials.
                if page.locator('input[type="password"], iframe[src*="captcha"]').count():
                    raise Problem(409, "遇到登录或验证门槛；请人工处理后再明确重启任务")
                reports.append(capture_page(library, job_id, page, query=query))
            # Do not close the user's browser. Playwright disconnects when its context exits.
        latest = library.job(job_id)
        if not latest["imported_ids"]:
            return library.transition_job(job_id, "blocked", latest["revision"], "当前可见区域没有可导入的有效尺寸图片；未宣称成功", actor="worker")
        return library.transition_job(job_id, "succeeded", latest["revision"], f"已导入 {len(latest['imported_ids'])} 个独立候选，等待人工选择和逐图核验", actor="worker")
    except Exception as exc:
        latest = library.job(job_id)
        if latest["status"] == "running":
            detail = str(exc) if isinstance(exc, (ValueError, Problem)) else "浏览器或网络失败；已导入候选保留，未绕过访问门槛"
            library.transition_job(job_id, "blocked", latest["revision"], detail[:1000], actor="worker")
        raise
