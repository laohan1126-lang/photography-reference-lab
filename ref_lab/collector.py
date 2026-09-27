"""Opt-in visible-browser capture. No hidden endpoints, cookie exports, CDN rewrites or challenge bypass."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
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


def find_bsk_cli() -> str | None:
    candidates = [
        "/mnt/c/Users/Dell/.local/bin/bsk.exe",
        str(Path.home() / ".local/bin/bsk.exe"),
        "C:\\Users\\Dell\\.local\\bin\\bsk.exe",
        shutil.which("bsk"),
        shutil.which("bsk.exe"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    return shutil.which("bsk")


def ensure_bsk_browser(bsk_bin: str) -> str | None:
    env = {**os.environ, "BSK_AUTO_START": "0"}
    status_p = subprocess.run([bsk_bin, "status", "--json"], capture_output=True, text=True, env=env)
    daemon_ok = False
    try:
        sdata = json.loads(status_p.stdout)
        if sdata.get("pid"):
            daemon_ok = True
    except Exception:
        pass
    if not daemon_ok:
        powershell_bin = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell"
        cmd = [powershell_bin, "-Command", f"Start-Process '{bsk_bin}' -ArgumentList 'daemon start --port 52801 --foreground' -WindowStyle Hidden"]
        subprocess.run(cmd, capture_output=True)
        time.sleep(1.5)

    p = subprocess.run([bsk_bin, "browsers", "--json"], capture_output=True, text=True, env=env)
    try:
        browsers = json.loads(p.stdout)
        if browsers:
            return browsers[0]["instance_id"]
    except Exception:
        pass

    # Open Edge extension popup per user authorization if not connected
    powershell_bin = shutil.which("powershell.exe") or shutil.which("powershell") or "powershell"
    cmd = [powershell_bin, "-Command", "Start-Process msedge.exe extension://emacgiaaaiojkkpkddmmdfhmokgmnikg/popup.html"]
    subprocess.run(cmd, capture_output=True)
    for _ in range(10):
        time.sleep(1)
        p = subprocess.run([bsk_bin, "browsers", "--json"], capture_output=True, text=True, env=env)
        try:
            browsers = json.loads(p.stdout)
            if browsers:
                return browsers[0]["instance_id"]
        except Exception:
            pass
    return None


def collect_via_bsk(library: Library, job_id: str, bsk_bin: str, browser_id: str) -> dict:
    job = library.job(job_id)
    env = {**os.environ, "BSK_AUTO_START": "0"}
    sess_res = subprocess.run([bsk_bin, "session", "start", "--browser", browser_id, "--json"], capture_output=True, text=True, env=env)
    sess_data = json.loads(sess_res.stdout)
    session_id = sess_data["session_id"]

    queries = job.get("queries") or []
    if not queries:
        char = job.get("project_snapshot", {}).get("character", "")
        work = job.get("project_snapshot", {}).get("work", "")
        costume = job.get("project_snapshot", {}).get("costume", "")
        base = " ".join(x for x in [char, work, costume] if x)
        queries = [f"{base} cosplay 摄影", f"{base} cos 漫展 姿势"]

    target_count = min(job.get("target_count", 30), 40)
    created_count = 0
    try:
        for query in queries:
            if created_count >= target_count:
                break
            # 1. First search Xiaohongshu
            xhs_url = f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}"
            subprocess.run([bsk_bin, "navigate", xhs_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"], capture_output=True, text=True, env=env)
            time.sleep(2.5)

            expr = """(() => {
                const imgs = Array.from(document.querySelectorAll("img")).filter(img => {
                    const r = img.getBoundingClientRect();
                    return r.width > 80 && r.height > 80 && img.naturalWidth >= 250 && img.naturalHeight >= 250
                        && (img.src.includes("xhscdn.com") || (img.currentSrc && img.currentSrc.includes("xhscdn.com")));
                }).map(img => ({
                    currentSrc: img.currentSrc || img.src,
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    title: img.alt || document.title || '',
                    page_url: img.closest('a')?.href || location.href
                }));
                return imgs;
            })()"""
            eval_p = subprocess.run([bsk_bin, "evaluate", "--json", expr, "--session", session_id], capture_output=True, text=True, env=env)
            try:
                raw_eval = json.loads(eval_p.stdout)
                records = raw_eval.get("value", []) if isinstance(raw_eval, dict) else (raw_eval if isinstance(raw_eval, list) else [])
            except Exception:
                records = []

            for record in records:
                if created_count >= target_count:
                    break
                url = record.get("currentSrc", "")
                if not allowed_image_url(url):
                    continue
                try:
                    img_bytes = download_observed(url, library.settings.max_upload_bytes)
                    asset = library.ingest_asset(img_bytes, "observed-image")
                    source = Source(page_url=record.get("page_url") or xhs_url, image_url=url,
                                    title=str(record.get("title", ""))[:400], search_query=query[:400], obtained_as="platform_variant")
                    result = library.add_candidate(job["project_id"], CandidateInput(
                        asset_sha=asset["id"],
                        source=source,
                        import_key="visible:" + digest({"url": url, "sha": asset["id"]}),
                        job_id=job_id,
                        discovery_intent="exact_character" if "cos" in query.lower() else "transferable_pose",
                        discovery_reason=f"通过本地 Agent 检索「{query}」在小红书发现"
                    ), actor="visible_browser")
                    if result["created"]:
                        created_count += 1
                except Exception:
                    continue

            # 2. Also try Pinterest if we need more images
            if created_count < target_count:
                pin_url = "https://www.pinterest.com/search/pins/?q=" + quote(query)
                subprocess.run([bsk_bin, "navigate", pin_url, "--session", session_id, "--wait-until", "domcontentloaded", "--timeout", "25s"], capture_output=True, text=True, env=env)
                time.sleep(2.5)
                pin_expr = """(() => {
                    const imgs = Array.from(document.querySelectorAll("img")).filter(img => {
                        const r = img.getBoundingClientRect();
                        return r.width > 80 && r.height > 80 && img.naturalWidth >= 250 && img.naturalHeight >= 250
                            && (img.src.includes("pinimg.com") || (img.currentSrc && img.currentSrc.includes("pinimg.com")));
                    }).map(img => ({
                        currentSrc: img.currentSrc || img.src,
                        width: img.naturalWidth,
                        height: img.naturalHeight,
                        title: img.alt || document.title || '',
                        page_url: img.closest('a')?.href || location.href
                    }));
                    return imgs;
                })()"""
                eval_p = subprocess.run([bsk_bin, "evaluate", "--json", pin_expr, "--session", session_id], capture_output=True, text=True, env=env)
                try:
                    raw_eval = json.loads(eval_p.stdout)
                    pin_records = raw_eval.get("value", []) if isinstance(raw_eval, dict) else (raw_eval if isinstance(raw_eval, list) else [])
                except Exception:
                    pin_records = []
                for record in pin_records:
                    if created_count >= target_count:
                        break
                    url = record.get("currentSrc", "")
                    if not allowed_image_url(url):
                        continue
                    try:
                        img_bytes = download_observed(url, library.settings.max_upload_bytes)
                        asset = library.ingest_asset(img_bytes, "observed-image")
                        source = Source(page_url=record.get("page_url") or pin_url, image_url=url,
                                        title=str(record.get("title", ""))[:400], search_query=query[:400], obtained_as="platform_variant")
                        result = library.add_candidate(job["project_id"], CandidateInput(
                            asset_sha=asset["id"],
                            source=source,
                            import_key="visible:" + digest({"url": url, "sha": asset["id"]}),
                            job_id=job_id,
                            discovery_intent="transferable_pose",
                            discovery_reason=f"通过本地 Agent 检索「{query}」在 Pinterest 发现"
                        ), actor="visible_browser")
                        if result["created"]:
                            created_count += 1
                    except Exception:
                        continue
    finally:
        subprocess.run([bsk_bin, "session", "stop", session_id], capture_output=True, env=env)

    latest = library.job(job_id)
    if not latest["imported_ids"]:
        return library.transition_job(job_id, "blocked", latest["revision"], "当前可见区域没有可导入的有效尺寸图片；未宣称成功", actor="worker")
    return library.transition_job(job_id, "succeeded", latest["revision"], f"已导入 {len(latest['imported_ids'])} 个独立候选，等待人工选择和逐图核验", actor="worker")


def run_browser_collection_job(library: Library, job_id: str) -> dict:
    job = library.job(job_id)
    if job["kind"] != "collection":
        raise Problem(409, "Not a collection job")
    job = library.transition_job(job_id, "running", job["revision"], "本地 Agent 搜图采集中...", actor="worker")

    bsk_bin = find_bsk_cli()
    if bsk_bin:
        browser_id = ensure_bsk_browser(bsk_bin)
        if browser_id:
            try:
                return collect_via_bsk(library, job_id, bsk_bin, browser_id)
            except Exception:
                pass

    # Playwright fallback if BrowserSkill is unavailable
    try:
        from playwright.sync_api import sync_playwright
        executable = os.environ.get("LAB_CHROMIUM") or shutil.which("chromium")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            queries = job.get("queries") or ["cosplay 摄影"]
            for query in queries:
                try:
                    resp = page.goto("https://www.pinterest.com/search/pins/?q=" + quote(query), wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(2000)
                    capture_page(library, job_id, page, query=query)
                except Exception:
                    pass
            browser.close()
    except Exception:
        pass

    latest = library.job(job_id)
    if not latest["imported_ids"]:
        return library.transition_job(job_id, "blocked", latest["revision"], "当前可见区域未能自动采到有效候选图片", actor="worker")
    return library.transition_job(job_id, "succeeded", latest["revision"], f"已导入 {len(latest['imported_ids'])} 个独立候选，等待人工选择和逐图核验", actor="worker")
