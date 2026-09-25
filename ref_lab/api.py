"""Private website + typed API. Start with `python -m ref_lab serve`."""
from __future__ import annotations

import hmac
import json
import os
import time
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
from .export import build_job_pack, build_pack
from .imports import import_candidates, import_notion
from .models import (AnalysisImport, AnalysisResult, CandidateInput, Card, CardInput, JobInput, JobResult,
                     NoteEdit, NoteInput, PackInput, ProjectEdit, ProjectInput, ReferenceEdit, ReflectionInput,
                     RevisionInput, ReviewInput, Source, Strict, VisualReview)
from .security import BodyLimitMiddleware, COOKIE, csrf_for, make_session, valid_session
from .service import Library, Problem


class Login(Strict):
    token: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    library = Library(settings)
    app = FastAPI(title="Photography Reference Lab", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.library = library
    app.state.settings = settings
    origin = settings.public_origin.rstrip("/")
    origin_url = urlsplit(origin)
    allowed_hosts = [origin_url.hostname]
    allowed_origins = {origin}
    if origin_url.hostname in {"127.0.0.1", "localhost", "::1"}:
        allowed_hosts += ["localhost", "127.0.0.1", "::1"]
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
        request.state.authenticated = bearer_ok or session_ok
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            supplied_origin = request.headers.get("origin")
            if supplied_origin and supplied_origin not in allowed_origins:
                return JSONResponse({"message": "Cross-origin writes are not allowed"}, 403)
        if path.startswith("/api/") and path != "/api/session":
            if not request.state.authenticated:
                return JSONResponse({"message": "请先解锁私人参考库"}, 401)
            if request.method not in {"GET", "HEAD", "OPTIONS"} and not bearer_ok:
                if not hmac.compare_digest(request.headers.get("x-lab-csrf", ""), csrf_for(settings.token, session)):
                    return JSONResponse({"message": "CSRF check failed; refresh and retry"}, 403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "private, no-store" if path.startswith("/api/") else "no-cache"
        return response

    app.add_middleware(BodyLimitMiddleware, limit=settings.max_body_bytes)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(set(allowed_hosts)))

    @app.get("/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/session")
    def session_info(request: Request):
        return {"authenticated": request.state.authenticated,
                "csrf": csrf_for(settings.token, request.cookies.get(COOKIE, "")) if request.state.authenticated else "",
                "version": __version__}

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
        response.set_cookie(COOKIE, session, httponly=True, secure=origin_url.scheme == "https", samesite="strict", max_age=86400)
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
        return {"collection": "local_browser_or_package", "analysis": "optional_local_worker",
                "openai_configured": bool(os.environ.get("OPENAI_API_KEY") and os.environ.get("LAB_ANALYSIS_MODEL")),
                "notion": "markdown_csv_import_and_optional_task_sync", "offline": "downloadable_zip",
                "visibility": "private", "automatic_background_search": False}

    @app.get("/api/contracts")
    def contracts():
        return {"visual_review": VisualReview.model_json_schema(), "card": Card.model_json_schema(),
                "analysis_result": AnalysisResult.model_json_schema(), "candidate": CandidateInput.model_json_schema()}

    @app.get("/api/projects")
    def projects(): return library.projects()

    @app.post("/api/projects", status_code=201)
    def create_project(data: ProjectInput): return library.create_project(data)

    @app.get("/api/projects/{project_id}")
    def project(project_id: str): return library.project(project_id)

    @app.put("/api/projects/{project_id}")
    def edit_project(project_id: str, data: ProjectEdit):
        return library.edit_project(project_id, ProjectInput(**data.model_dump(exclude={"expected_revision"})), data.expected_revision)

    @app.get("/api/projects/{project_id}/stats")
    def stats(project_id: str): return library.stats(project_id)

    @app.get("/api/projects/{project_id}/references")
    def references(project_id: str, limit: int = Query(60, ge=1, le=200), offset: int = Query(0, ge=0),
                   q: str = Query("", max_length=400), decision: str = "", state: str = "", lane: str = "", kind: str = ""):
        return library.references(project_id, limit=limit, offset=offset, query=q, decision=decision, state=state, lane=lane, kind=kind)

    @app.post("/api/projects/{project_id}/references", status_code=201)
    def candidate(project_id: str, data: CandidateInput): return library.add_candidate(project_id, data, actor="human")

    @app.get("/api/references/{reference_id}")
    def reference(reference_id: str): return library.reference(reference_id)

    @app.patch("/api/references/{reference_id}")
    def edit_reference(reference_id: str, data: ReferenceEdit): return library.edit_reference(reference_id, data)

    @app.post("/api/references/{reference_id}/review")
    def review(reference_id: str, data: ReviewInput):
        return library.review_reference(reference_id, data.review, data.expected_revision)

    @app.post("/api/references/{reference_id}/card")
    def card(reference_id: str, data: CardInput):
        return library.save_card(reference_id, data.card, data.expected_revision)

    @app.post("/api/references/{reference_id}/accept")
    def accept(reference_id: str, data: RevisionInput): return library.accept_card(reference_id, data.expected_revision)

    @app.post("/api/references/{reference_id}/analysis")
    def analysis(reference_id: str, data: AnalysisImport):
        return library.apply_analysis(reference_id, data.result, data.expected_revision, data.producer)

    @app.post("/api/references/{reference_id}/reflection")
    def reflection(reference_id: str, data: ReflectionInput): return library.reflect(reference_id, data.model_dump())

    @app.get("/api/references/{reference_id}/similar")
    def similar(reference_id: str):
        ref = library.reference(reference_id)
        return library.duplicates(ref["project_id"], reference_id)

    @app.post("/api/assets", status_code=201)
    def upload(file: UploadFile = File(...)):
        return library.ingest_asset(file.file.read(settings.max_upload_bytes + 1), file.filename or "")

    @app.post("/api/references/{reference_id}/replace")
    def replace(reference_id: str, expected_revision: int = Form(...), file: UploadFile = File(...)):
        asset = library.ingest_asset(file.file.read(settings.max_upload_bytes + 1), file.filename or "")
        return library.replace_asset(reference_id, asset["id"], expected_revision)

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
    def import_analyses(project_id: str, file: UploadFile = File(...)):
        raw = file.file.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024: raise Problem(413, "Analysis JSON exceeds 8 MiB")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("items"), list) or len(payload["items"]) > 200:
            raise Problem(422, "Expected schema_version=1 and up to 200 analysis items")
        report = {"imported": [], "errors": []}
        library.project(project_id)
        for index, item in enumerate(payload["items"]):
            try:
                reference_id = item["reference_id"]
                ref = library.reference(reference_id)
                if ref["project_id"] != project_id: raise Problem(409, "Wrong project")
                data = AnalysisImport.model_validate({key: value for key, value in item.items() if key != "reference_id"})
                library.apply_analysis(reference_id, data.result, data.expected_revision, data.producer, str(payload.get("job_id", "")))
                report["imported"].append(reference_id)
            except (Problem, ValueError, KeyError, TypeError) as exc:
                report["errors"].append({"index": index, "error": str(exc)})
        return report

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

    @app.post("/api/jobs/{job_id}/status")
    def job_status(job_id: str, data: JobResult):
        return library.transition_job(job_id, data.status, data.expected_revision, data.detail)

    @app.post("/api/projects/{project_id}/pack")
    def shooting_pack(project_id: str, data: PackInput):
        path = build_pack(library, project_id, data)
        return FileResponse(path, media_type="application/zip", filename=f"{data.mode}-shooting-pack.zip", background=BackgroundTask(path.unlink, missing_ok=True))

    @app.get("/")
    def home(): return FileResponse(settings.web_dir / "index.html", media_type="text/html")

    @app.get("/static/{filename}")
    def static(filename: str):
        if filename not in {"app.js", "styles.css"}: raise Problem(404, "Static file not found")
        return FileResponse(settings.web_dir / filename)

    return app
