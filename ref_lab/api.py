"""Private website + typed API. Start with `python -m ref_lab serve`."""
from __future__ import annotations

import hmac
import json
import os
import time
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
from collections import defaultdict, deque
from urllib.parse import urlsplit
from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError
from starlette.background import BackgroundTask
from starlette.middleware.trustedhost import TrustedHostMiddleware
from . import __version__
from .config import Settings
from .learning_preview import STATIC_FILES as LEARNING_STATIC_FILES, preview_router
from .learning_state import router as learning_state_router
from .learning_media import SOURCE_IMAGE_CSP
from .export import build_job_pack, build_pack, build_contact_board
from .imports import import_candidates, import_notion, import_analyses as import_analysis_results
from .models import (AnalysisImport, AnalysisResult, CandidateInput, Card, CardInput, JobInput, JobResult,
                     NoteEdit, NoteInput, PackInput, ProjectEdit, ProjectInput, ReferenceEdit, ReflectionInput,
                     RevisionInput, ReviewInput, Source, Strict, VisualReview, InspirationInput, InspirationEdit, InspirationUse, AcceptanceInput, CollectionReport,
                     CandidatePreflightInput, PreflightOverrideInput,
                     IdentityContextInput, ConfirmSummaryInput, RollbackProfileInput, PreflightScanInput,
                     ReferenceTransferInput, ContactBoardInput, ArchiveInspirationInput, StudyCandidateEdit)

from .security import BodyLimitMiddleware, COOKIE, csrf_for, make_session, valid_session
from .service import Library, Problem


class Login(Strict):
    token: str


class MaintenanceInput(Strict):
    enabled: bool


def create_app(settings: Settings | None = None, *, classifier=None) -> FastAPI:
    settings = settings or Settings.from_env()
    library = Library(settings)
    @asynccontextmanager
    async def lifespan(app):
        worker = app.state.classification_worker
        if settings.auto_classify:
            worker.start()
        try:
            yield
        finally:
            if settings.auto_classify:
                await asyncio.to_thread(worker.stop)

    app = FastAPI(title="Photography Reference Lab", version=__version__, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.library = library
    app.state.settings = settings
    maintenance_file = settings.data_dir / "maintenance"
    origin = settings.public_origin.rstrip("/")
    origin_url = urlsplit(origin)
    allowed_hosts = [h for h in {origin_url.hostname, "localhost", "127.0.0.1", "::1", "ref.koshikorato.top", "c2c-photography-reference-lab.koshikorato.top"} if h]
    allowed_origins = {origin, "http://localhost:18765", "http://127.0.0.1:18765", "https://ref.koshikorato.top", "https://c2c-photography-reference-lab.koshikorato.top"}
    if origin_url.hostname in {"127.0.0.1", "localhost", "::1"}:
        for host in ("localhost", "127.0.0.1"):
            allowed_origins.add(f"{origin_url.scheme}://{host}" + (f":{origin_url.port}" if origin_url.port else ""))
    attempts: dict[str, deque] = defaultdict(deque)

    @app.exception_handler(Problem)
    async def problem_handler(request: Request, exc: Problem):
        return JSONResponse({"message": exc.message, "details": exc.details}, status_code=exc.status)

    @app.exception_handler(ValueError)
    async def value_handler(request: Request, exc: ValueError):
        return JSONResponse({"message": str(exc)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = [{"field": list(e["loc"]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse({"message": "提交字段不完整或格式不正确", "details": errors}, status_code=422)

    @app.middleware("http")
    async def access_control(request: Request, call_next):
        path = request.url.path
        session = request.cookies.get(COOKIE, "")
        bearer = request.headers.get("authorization", "")
        bearer_ok = bearer.startswith("Bearer ") and hmac.compare_digest(bearer[7:], settings.token)
        session_ok = valid_session(settings.token, session)
        request.state.authenticated = settings.no_auth or bearer_ok or session_ok
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            supplied_origin = request.headers.get("origin")
            if supplied_origin and supplied_origin not in allowed_origins:
                return JSONResponse({"message": "Cross-origin writes are not allowed"}, 403)
        if path.startswith("/api/") and path != "/api/session":
            if not request.state.authenticated:
                return JSONResponse({"message": "请先解锁私人参考库"}, 401)
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not bearer_ok and not settings.no_auth:
                if not hmac.compare_digest(request.headers.get("x-lab-csrf", ""), csrf_for(settings.token, session)):
                    return JSONResponse({"message": "CSRF check failed; refresh and retry"}, 403)
            if (maintenance_file.exists() and path != "/api/maintenance"
                    and (request.method not in {"GET", "HEAD", "OPTIONS"}
                         or path.endswith("/screening-sessions/current") or path == "/api/profile")):
                return JSONResponse({"message": "资料库正在受控维护，暂时只读；请稍后重试。"}, 503)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        # Only the teaching document references reviewed source photos and Commons.
        # The private reference app and all executable/network directives stay local.
        image_sources = "'self' data: blob:"
        if path == "/learning":
            image_sources += " " + SOURCE_IMAGE_CSP
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            f"img-src {image_sources}; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Cache-Control"] = "private, no-store" if path.startswith("/api/") else "no-cache"
        return response

    app.add_middleware(BodyLimitMiddleware, limit=settings.max_body_bytes)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(set(allowed_hosts)))

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/runtime")
    def runtime_info():
        # Read the connection, not merely the launcher configuration.
        with library.db.read() as con:
            database = next(r[2] for r in con.execute("PRAGMA database_list") if r[1] == "main")
            return {"pid": os.getpid(), "source": str(Path(__file__).resolve()),
                    "database": database, "data_dir": str(settings.data_dir.resolve()),
                    "schema": con.execute("PRAGMA user_version").fetchone()[0],
                    "maintenance": maintenance_file.exists(),
                    "foreign_key_errors": len(con.execute("PRAGMA foreign_key_check").fetchall()),
                    "counts": {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                               for t in ("projects", "assets", "refs", "inspirations", "study_candidates", "events")}}

    @app.post("/api/maintenance")
    def maintenance(data: MaintenanceInput):
        # Persist across restart and directory copying; this fences new HTTP writes.
        # Existing workers/CLI must still be drained before a stopped-service snapshot.
        if data.enabled:
            maintenance_file.write_text("Controlled adoption: HTTP writes paused.\n", encoding="utf-8")
        else:
            maintenance_file.unlink(missing_ok=True)
        return {"maintenance": maintenance_file.exists()}

    @app.get("/api/session")
    def session_info(request: Request):
        session = request.cookies.get(COOKIE, "")
        if settings.no_auth:
            if not session:
                session = make_session(settings.token)
            response = JSONResponse({
                "authenticated": True,
                "csrf": csrf_for(settings.token, session),
                "version": __version__,
                "no_auth": True
            })
            response.set_cookie(COOKIE, session, httponly=True, secure=request.url.scheme == "https" or origin_url.scheme == "https", samesite="strict", max_age=86400 * 30)
            return response
        return {"authenticated": request.state.authenticated,
                "csrf": csrf_for(settings.token, session) if request.state.authenticated else "",
                "version": __version__,
                "no_auth": False}

    @app.post("/api/session")
    def login(data: Login, request: Request):
        key = request.client.host if request.client else "unknown"
        recent = attempts[key]
        current = time.monotonic()
        while recent and recent[0] < current - 60: recent.popleft()
        if len(recent) >= 8: raise Problem(429, "解锁尝试过于频繁，请稍后重试")
        if not hmac.compare_digest(data.token, settings.token):
            recent.append(current)
            raise Problem(401, "访问口令不正确")
        recent.clear()
        session = make_session(settings.token)
        response = JSONResponse({"authenticated": True, "csrf": csrf_for(settings.token, session)})
        response.set_cookie(COOKIE, session, httponly=True, secure=request.url.scheme == "https" or origin_url.scheme == "https", samesite="strict", max_age=86400 * 30)
        return response

    @app.delete("/api/session")
    def logout(request: Request):
        if not request.state.authenticated: raise Problem(401, "Not authenticated")
        session = request.cookies.get(COOKIE, "")
        if not hmac.compare_digest(request.headers.get("x-lab-csrf", ""), csrf_for(settings.token, session)):
            raise Problem(403, "CSRF check failed")
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(COOKIE)
        return response

    @app.get("/api/capabilities")
    def capabilities():
        return {"collection": "agent_browserskill_package", "analysis": "agent_package",
                "independent_api_required": False,
                "collection_adapter_configured": bool(os.environ.get("LAB_COLLECTION_COMMAND", "").strip()),
                "collection_adapter_verified": False,
                "notion": "markdown_csv_import_and_optional_task_sync", "offline": "downloadable_zip",
                "visibility": "private", "automatic_background_search": False}

    @app.get("/api/contracts")
    def contracts():
        return {"visual_review": VisualReview.model_json_schema(), "card": Card.model_json_schema(),
                "analysis_result": AnalysisResult.model_json_schema(), "candidate": CandidateInput.model_json_schema(),
                "candidate_preflight": CandidatePreflightInput.model_json_schema()}

    @app.get("/api/projects")
    def projects(archived: bool = False): return library.projects(archived=archived)

    @app.post("/api/projects", status_code=201)
    def create_project(data: ProjectInput): return library.create_project(data)

    @app.get("/api/projects/{project_id}")
    def project(project_id: str): return library.project(project_id)

    @app.put("/api/projects/{project_id}")
    def edit_project(project_id: str, data: ProjectEdit):
        return library.edit_project(project_id, ProjectInput(**data.model_dump(exclude={"expected_revision"})), data.expected_revision)

    @app.delete("/api/projects/{project_id}")
    def archive_project(project_id: str, data: RevisionInput):
        return library.archive_project(project_id, data.expected_revision)

    @app.post("/api/projects/{project_id}/restore")
    def restore_project(project_id: str, data: RevisionInput):
        return library.restore_project(project_id, data.expected_revision)

    @app.get("/api/projects/{project_id}/stats")
    def stats(project_id: str): return library.stats(project_id)

    @app.get("/api/projects/{project_id}/references")
    def references(project_id: str, limit: int = Query(60, ge=1, le=200), offset: int = Query(0, ge=0),
                   q: str = Query("", max_length=400), decision: str = "", state: str = "", lane: str = "", kind: str = "",
                   include_rejected: bool = False, view_filtered: bool = False, view_recycle: bool = False,
                   job_id: str = "", focus_id: str = "", preflight_status: str = ""):
        return library.references(project_id, limit=limit, offset=offset, query=q, decision=decision, state=state, lane=lane, kind=kind,
                                  include_rejected=include_rejected, view_filtered=view_filtered, view_recycle=view_recycle,
                                  job_id=job_id, focus_id=focus_id, preflight_status=preflight_status)

    @app.get("/api/projects/{project_id}/identity-context")
    def get_identity_context(project_id: str):
        return library.identity_context(project_id)

    @app.post("/api/projects/{project_id}/identity-context")
    def update_identity_context(project_id: str, data: IdentityContextInput):
        return library.update_identity_context(project_id, data)

    @app.get("/api/projects/{project_id}/preflights")
    def list_preflights(project_id: str, status: str = ""):
        return library.preflights(project_id, status=status)

    @app.post("/api/projects/{project_id}/preflight-scan")
    def scan_project_preflight(project_id: str, data: PreflightScanInput | None = None):
        force = data.force if data else False
        return library.scan_project_preflight(project_id, force=force)

    @app.post("/api/projects/{project_id}/references", status_code=201)
    def candidate(project_id: str, data: CandidateInput): return library.add_candidate(project_id, data, actor="human")

    @app.post("/api/projects/{project_id}/references/transfer")
    def transfer_references(project_id: str, data: ReferenceTransferInput):
        return library.transfer_references(project_id, data)

    @app.post("/api/projects/{project_id}/contact-board")
    def contact_board(project_id: str, data: ContactBoardInput):
        path = build_contact_board(library, project_id, data)
        filename = "contact-board.png" if path.suffix.lower() == ".png" else "contact-board-pages.zip"
        media_type = "image/png" if path.suffix.lower() == ".png" else "application/zip"
        return FileResponse(path, media_type=media_type, filename=filename,
                            background=BackgroundTask(path.unlink, missing_ok=True))


    @app.get("/api/references/{reference_id}")
    def reference(reference_id: str): return library.reference(reference_id)

    @app.patch("/api/references/{reference_id}")
    def edit_reference(reference_id: str, data: ReferenceEdit): return library.edit_reference(reference_id, data)

    @app.post("/api/references/{reference_id}/preflight")
    def candidate_preflight(reference_id: str, data: CandidatePreflightInput):
        return library.apply_candidate_preflight(reference_id, data.preflight, data.expected_revision, data.producer)

    @app.post("/api/references/{reference_id}/preflight-override")
    def candidate_preflight_override(reference_id: str, data: PreflightOverrideInput):
        return library.override_candidate_preflight(reference_id, data.expected_revision)

    @app.post("/api/references/{reference_id}/review")
    def review(reference_id: str, data: ReviewInput):
        return library.review_reference(reference_id, data.review, data.expected_revision)

    @app.post("/api/references/{reference_id}/card")
    def card(reference_id: str, data: CardInput):
        return library.save_card(reference_id, data.card, data.expected_revision)

    @app.post("/api/references/{reference_id}/accept")
    def accept(reference_id: str, data: AcceptanceInput):
        return library.accept_card(reference_id, data.expected_revision, source=data.source, allow_cross_domain=data.allow_cross_domain)

    @app.post("/api/references/{reference_id}/analysis")
    def analysis(reference_id: str, data: AnalysisImport):
        return library.apply_analysis(reference_id, data.result, data.expected_revision, data.producer)

    @app.post("/api/references/{reference_id}/reflection")
    def reflection(reference_id: str, data: ReflectionInput): return library.reflect(reference_id, data.model_dump())

    @app.get("/api/references/{reference_id}/similar")
    def similar(reference_id: str):
        ref = library.reference(reference_id)
        return library.duplicates(ref["project_id"], reference_id)

    @app.post("/api/assets/{sha}/reveal")
    def reveal_asset(sha: str):
        asset = library.asset(sha)
        file_path = library.assets.path(asset, "original")
        if not file_path.is_file():
            raise Problem(404, "图片文件在本地不存在")
        import os
        import subprocess
        import sys
        folder = str(file_path.parent).replace("/", "\\")
        filename = file_path.name
        if sys.platform == "win32":
            try:
                os.startfile(folder)
            except Exception:
                try:
                    subprocess.Popen(f'explorer.exe "{folder}"')
                except Exception:
                    pass
        return {"revealed": True, "path": str(file_path), "folder": folder, "filename": filename}

    @app.post("/api/references/{reference_id}/reveal")
    def reveal_reference(reference_id: str):
        ref = library.reference(reference_id)
        target_path = None
        if ref.get("archive_path") and Path(ref["archive_path"]).is_file():
            target_path = Path(ref["archive_path"])
        elif ref.get("asset_sha"):
            asset = library.asset(ref["asset_sha"])
            target_path = library.assets.path(asset, "original")
        if not target_path or not target_path.is_file():
            raise Problem(404, "图片文件在本地不存在")
        import os
        import subprocess
        import sys
        folder = str(target_path.parent).replace("/", "\\")
        filename = target_path.name
        if sys.platform == "win32":
            try:
                os.startfile(folder)
            except Exception:
                try:
                    subprocess.Popen(f'explorer.exe "{folder}"')
                except Exception:
                    pass
        return {"revealed": True, "path": str(target_path), "folder": folder, "filename": filename}

    @app.post("/api/projects/{project_id}/reveal-export")
    def reveal_project_export(project_id: str):
        from .archiver import get_project_archive_dir, sync_project_confirmed_archive
        proj = library.project(project_id)
        target = get_project_archive_dir(settings.data_dir, proj)
        target.mkdir(parents=True, exist_ok=True)
        try:
            sync_project_confirmed_archive(library, project_id)
        except Exception:
            pass
        import os
        import sys
        if sys.platform == "win32":
            try:
                os.startfile(str(target))
            except Exception:
                import subprocess
                p = str(target).replace("/", "\\")
                subprocess.Popen(f'explorer.exe "{p}"', shell=True)
        return {"revealed": True, "path": str(target)}

    @app.post("/api/projects/{project_id}/sync-archive")
    def sync_project_archive(project_id: str):
        from .archiver import sync_project_confirmed_archive
        return sync_project_confirmed_archive(library, project_id)

    @app.post("/api/assets", status_code=201)
    def upload(file: UploadFile = File(...)):
        return library.ingest_asset(file.file.read(settings.max_upload_bytes + 1), file.filename or "")

    @app.post("/api/references/{reference_id}/replace")
    def replace(reference_id: str, expected_revision: int = Form(...), file: UploadFile = File(...)):
        asset = library.ingest_asset(file.file.read(settings.max_upload_bytes + 1), file.filename or "")
        return library.replace_asset(reference_id, asset["id"], expected_revision)

    @app.get("/api/assets/{sha}/context")
    def asset_context(sha: str): return library.asset_context(sha)

    @app.post("/api/references/{reference_id}/restore")
    def restore(reference_id: str, data: RevisionInput):
        return library.restore_reference(reference_id, data.expected_revision)

    @app.post("/api/references/{reference_id}/restore-project-use")
    def restore_project_use(reference_id: str, data: RevisionInput):
        return library.restore_detached_reference(reference_id, data.expected_revision)

    @app.post("/api/references/{reference_id}/restore-preflight")
    def restore_preflight(reference_id: str, data: RevisionInput):
        return library.restore_preflight_candidate(reference_id, data.expected_revision)

    @app.post("/api/references/{reference_id}/make-transferable")
    def make_transferable(reference_id: str, data: RevisionInput):
        return library.make_transferable_candidate(reference_id, data.expected_revision)


    @app.post("/api/references/{reference_id}/inspiration")
    def save_inspiration(reference_id: str, data: RevisionInput):
        return library.save_reference_inspiration(reference_id, data.expected_revision)

    @app.post("/api/references/{reference_id}/archive-inspiration")
    def archive_inspiration(reference_id: str, data: ArchiveInspirationInput):
        return library.archive_reference_to_inspiration(
            reference_id, data.expected_revision, preference=data.preference, borrow=data.borrow
        )

    @app.get("/api/inspirations")
    def inspirations(limit: int = Query(60, ge=1, le=200), offset: int = Query(0, ge=0),
                     q: str = Query("", max_length=400), recycled: bool = False):
        return library.inspirations(limit=limit, offset=offset, query=q, recycled=recycled)

    @app.post("/api/inspirations", status_code=201)
    def create_inspiration(data: InspirationInput): return library.create_inspiration(data)

    @app.get("/api/inspirations/{inspiration_id}")
    def inspiration(inspiration_id: str): return library.inspiration(inspiration_id)

    @app.patch("/api/inspirations/{inspiration_id}")
    def edit_inspiration(inspiration_id: str, data: InspirationEdit): return library.edit_inspiration(inspiration_id, data)

    @app.post("/api/inspirations/{inspiration_id}/use")
    def use_inspiration(inspiration_id: str, data: InspirationUse):
        return library.use_inspiration(inspiration_id, data.project_id, data.expected_revision)

    @app.get("/api/study-candidates")
    def study_candidates(limit: int = Query(60, ge=1, le=200), offset: int = Query(0, ge=0),
                         q: str = Query("", max_length=400),
                         status: str = Query("", pattern="^(|pending|priority|ordinary|skip)$"),
                         topic: str = Query("", pattern="^(|动作|光线|构图|环境|道具)$")):
        return library.study_candidates(limit=limit, offset=offset, query=q, status=status, topic=topic)

    @app.get("/api/study-candidates/{candidate_id}")
    def study_candidate(candidate_id: str):
        return library.study_candidate(candidate_id)

    @app.patch("/api/study-candidates/{candidate_id}")
    def edit_study_candidate(candidate_id: str, data: StudyCandidateEdit):
        return library.edit_study_candidate(candidate_id, data)

    @app.post("/api/imports/notion")
    def import_global_notes(file: UploadFile = File(...)):
        return import_notion(library, None, file.file.read(settings.max_body_bytes + 1))

    @app.get("/api/notes")
    def all_notes(): return library.notes()

    @app.post("/api/notes", status_code=201)
    def create_global_note(data: NoteInput): return library.add_note(None, data)

    @app.get("/api/jobs")
    def all_jobs(): return library.jobs()

    @app.post("/api/jobs/{job_id}/report")
    def collection_report(job_id: str, data: CollectionReport): return library.record_collection_report(job_id, data)

    @app.get("/api/assets/{sha}/{variant}")
    def image(sha: str, variant: str):
        asset = library.asset(sha)
        file = library.assets.path(asset, variant)
        if not file.is_file(): raise Problem(404, "Image file is missing; run doctor")
        return FileResponse(file, media_type=asset["mime"] if variant == "original" else "image/jpeg")

    @app.post("/api/projects/{project_id}/imports/candidates")
    def import_package(project_id: str, file: UploadFile = File(...), job_id: str = Form("")):
        return import_candidates(library, project_id, file.file.read(settings.max_body_bytes + 1), job_id)

    @app.post("/api/projects/{project_id}/imports/notion")
    def import_notes(project_id: str, file: UploadFile = File(...)):
        return import_notion(library, project_id, file.file.read(settings.max_body_bytes + 1))

    @app.post("/api/projects/{project_id}/imports/analyses")
    def import_analyses(project_id: str, file: UploadFile = File(...), job_id: str = Form("")):
        return import_analysis_results(library, project_id, file.file.read(8 * 1024 * 1024 + 1), job_id)

    @app.get("/api/projects/{project_id}/notes")
    def notes(project_id: str): return library.notes(project_id)

    @app.post("/api/projects/{project_id}/notes", status_code=201)
    def add_note(project_id: str, data: NoteInput): return library.add_note(project_id, data)

    @app.put("/api/notes/{note_id}")
    def edit_note(note_id: str, data: NoteEdit):
        return library.edit_note(note_id, data.title, data.body, data.expected_revision)

    @app.get("/api/projects/{project_id}/events")
    def events(project_id: str, after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return library.events(project_id, after, limit)

    @app.post("/api/projects/{project_id}/jobs", status_code=201)
    def create_job(project_id: str, data: JobInput): return library.create_job(project_id, data)

    @app.get("/api/projects/{project_id}/jobs")
    def jobs(project_id: str): return library.jobs(project_id)

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str): return library.job(job_id)

    @app.get("/api/jobs/{job_id}/bundle")
    def bundle(job_id: str): return library.job_bundle(job_id)

    @app.get("/api/jobs/{job_id}/download")
    def job_download(job_id: str):
        path = build_job_pack(library, job_id)
        return FileResponse(path, media_type="application/zip", filename=f"job-{job_id[:8]}.zip", background=BackgroundTask(path.unlink, missing_ok=True))

    @app.post("/api/jobs/{job_id}/run-antigravity")
    def run_antigravity(job_id: str):
        job = library.job(job_id)
        if job["kind"] == "analysis":
            from .providers import AntigravityAnalyzer, run_analysis_job
            analyzer = AntigravityAnalyzer()
            return run_analysis_job(library, job_id, analyzer)
        elif job["kind"] == "collection":
            from .collector import run_browser_collection_job
            return run_browser_collection_job(library, job_id)
        raise Problem(400, f"未知任务类型: {job['kind']}")

    @app.post("/api/jobs/{job_id}/status")
    def job_status(job_id: str, data: JobResult):
        return library.transition_job(job_id, data.status, data.expected_revision, data.detail)

    @app.get("/api/projects/{project_id}/screening-sessions/current")
    def current_screening_session(project_id: str):
        return library.current_screening_session(project_id)

    @app.get("/api/projects/{project_id}/screening-sessions")
    def screening_sessions(project_id: str):
        return library.screening_sessions(project_id)

    @app.post("/api/screening-sessions/{session_id}/finish")
    def finish_session(session_id: str):
        return library.finish_screening_session(session_id)

    @app.post("/api/screening-sessions/{session_id}/confirm")
    def confirm_session(session_id: str, data: ConfirmSummaryInput):
        return library.confirm_screening_summary(session_id, data.accepted_hypotheses, data.apply_to_profile)

    @app.get("/api/profile")
    def aesthetic_profile():
        return library.aesthetic_profile()

    @app.get("/api/profile/history")
    def profile_history():
        return library.profile_history()

    @app.post("/api/profile/rollback")
    def rollback_profile(data: RollbackProfileInput):
        return library.rollback_profile(data.target_version)

    @app.post("/api/skills/curator/refine")
    def refine_curator_skill():
        return library.refine_curator_skill()


    @app.post("/api/projects/{project_id}/pack")
    def shooting_pack(project_id: str, data: PackInput):
        path = build_pack(library, project_id, data)
        return FileResponse(path, media_type="application/zip", filename=f"{data.mode}-shooting-pack.zip", background=BackgroundTask(path.unlink, missing_ok=True))

    from .library_browser import install_browser_routes
    install_browser_routes(app)
    from .classification import ClassificationQueue, ClassificationWorker, AntigravityClassifier
    classification_queue = ClassificationQueue(app.state.library_browser)
    worker = ClassificationWorker(classification_queue, classifier or AntigravityClassifier(settings.classification_model))
    app.state.classification_queue = classification_queue
    app.state.classification_worker = worker

    @app.get("/api/library/classification")
    def classification_status():
        return {**classification_queue.status(), "enabled": settings.auto_classify, "worker_error": worker.error}

    @app.post("/api/library/classification/retry")
    def retry_classification():
        return {"retried": classification_queue.retry_failed()}

    @app.get("/api/library/assets/{sha}/classification")
    def asset_classification(sha: str):
        library.asset(sha)
        with library.db.read() as con:
            annotation = app.state.library_browser.classification_snapshot(con, sha)
        return {"annotation": annotation, **classification_queue.item_status(sha)}


    @app.get("/")
    def home(): return FileResponse(settings.web_dir / "index.html", media_type="text/html")

    @app.get("/static/{filename}")
    def static(filename: str):
        if filename not in {"app.js", "styles.css", "library-browser.js"} | LEARNING_STATIC_FILES: raise Problem(404, "Static file not found")
        return FileResponse(settings.web_dir / filename, headers={"Cache-Control": "no-cache, must-revalidate"})

    app.include_router(preview_router(settings.web_dir))
    app.include_router(learning_state_router(settings.web_dir, settings.data_dir))
    return app
