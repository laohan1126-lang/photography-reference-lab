"""Private, revisioned learning notes stored separately from the photo library.

The lock registry coordinates router instances in this process. The current
runtime is single-process; this module does not claim cross-process locking.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

MAX_PHOTO_BYTES = 12 * 1024 * 1024
MAX_PHOTO_PIXELS = 40_000_000
MAX_LOG_CHARS = 8000
MAX_NOTES_CHARS = 12000
STATUSES = {"unassessed", "unstarted", "learning", "practicing", "field_verified", "mastered"}
GATEWAY_STAGES = {"unassessed", "unseen", "terms", "principles", "analysis", "transfer", "field"}
GATEWAY_ANSWER_KEYS = {"observation", "comparison", "transfer", "confusion"}
GATEWAY_REVEALED_KEYS = {"observation", "comparison", "transfer"}
GATEWAY_SECTIONS = {"problem", "observe", "principle", "contrast", "boundary", "transfer", "reflect", "sources"}
MAX_GATEWAY_ANSWER_CHARS = 8000
GATEWAY_FIELDS = {"stage", "answers", "revealed", "last_section"}
IMAGE_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
PHOTO_NAME = re.compile(r"([0-9a-f]{64})\.(jpg|png|webp)\Z")

_locks_guard = threading.Lock()
_locks: dict[str, threading.RLock] = {}


def _lock_for(path: Path) -> threading.RLock:
    key = os.path.normcase(str(path.resolve()))
    with _locks_guard:
        return _locks.setdefault(key, threading.RLock())


def _fail(status: int, message: str) -> None:
    raise HTTPException(status_code=status, detail=message)


def _load_skills(web_dir: Path) -> set[str]:
    atlas = web_dir / "learning-atlas.json"
    try:
        data = json.loads(atlas.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail(503, "摄影学习研究数据尚未加载")
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail(503, "摄影学习研究数据不可读取")
    skills = data.get("skills") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1 or not isinstance(skills, list)):
        _fail(503, "摄影学习研究数据格式无效")
    ids: set[str] = set()
    for item in skills:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            _fail(503, "摄影学习技能白名单格式无效")
        if item["id"] in ids:
            _fail(503, "摄影学习技能白名单含重复 ID")
        ids.add(item["id"])
    return ids


def _load_gateways(web_dir: Path) -> set[str] | None:
    """Return the gateway allowlist, or None for a pre-gateway atlas."""
    atlas = web_dir / "learning-atlas.json"
    try:
        data = json.loads(atlas.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail(503, "摄影学习研究数据尚未加载")
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail(503, "摄影学习研究数据不可读取")
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != 1 or not isinstance(data.get("skills"), list)):
        _fail(503, "摄影学习研究数据格式无效")
    if "gateways" not in data:
        return None
    gateways = data["gateways"]
    if not isinstance(gateways, list):
        _fail(503, "摄影学习网关白名单格式无效")
    ids: set[str] = set()
    for item in gateways:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            _fail(503, "摄影学习网关白名单格式无效")
        if item["id"] in ids:
            _fail(503, "摄影学习网关白名单含重复 ID")
        ids.add(item["id"])
    return ids


def _blank() -> dict[str, Any]:
    return {"revision": 0, "skills": {}}


def _validate_gateway_record(gateway_id: Any, record: Any) -> bool:
    if (not isinstance(gateway_id, str) or not gateway_id or not isinstance(record, dict)
            or set(record) != GATEWAY_FIELDS):
        return False
    if not isinstance(record["stage"], str) or record["stage"] not in GATEWAY_STAGES:
        return False
    answers = record["answers"]
    if (not isinstance(answers, dict)
            or any(not isinstance(key, str) or key not in GATEWAY_ANSWER_KEYS for key in answers)
            or any(not isinstance(value, str) or len(value) > MAX_GATEWAY_ANSWER_CHARS
                   for value in answers.values())):
        return False
    revealed = record["revealed"]
    if (not isinstance(revealed, list) or any(not isinstance(item, str) or item not in GATEWAY_REVEALED_KEYS
                                               for item in revealed)
            or len(set(revealed)) != len(revealed)):
        return False
    return isinstance(record["last_section"], str) and record["last_section"] in GATEWAY_SECTIONS


def _read_state(path: Path) -> dict[str, Any]:
    if path.parent.is_symlink():
        _fail(503, "学习记录目录无效")
    if not path.exists():
        return _blank()
    if path.is_symlink() or not path.is_file():
        _fail(503, "学习记录存储路径无效")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail(503, "学习记录无法读取")
    if (not isinstance(value, dict) or type(value.get("revision")) is not int
            or value["revision"] < 0 or not isinstance(value.get("skills"), dict)):
        _fail(503, "学习记录格式无效")
    for skill_id, record in value["skills"].items():
        if (not isinstance(skill_id, str) or not isinstance(record, dict)
                or not isinstance(record.get("logs", []), list)
                or not isinstance(record.get("photos", []), list)
                or ("status" in record and (not isinstance(record["status"], str)
                                             or record["status"] not in STATUSES))
                or any(key in record and type(record[key]) is not bool for key in ("weak", "focus"))
                or ("notes" in record and not isinstance(record["notes"], str))):
            _fail(503, "学习记录格式无效")
    if "gateways" in value:
        if not isinstance(value["gateways"], dict):
            _fail(503, "学习网关记录格式无效")
        for gateway_id, record in value["gateways"].items():
            if not _validate_gateway_record(gateway_id, record):
                _fail(503, "学习网关记录格式无效")
    return value


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        _fail(503, "学习记录目录无效")
    fd, temporary = tempfile.mkstemp(prefix=".learning-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _expected(body: dict[str, Any], state: dict[str, Any]) -> None:
    revision = body.get("expected_revision")
    if type(revision) is not int or revision < 0:
        _fail(422, "expected_revision 必须是非负整数")
    if revision != state["revision"]:
        _fail(409, "学习记录已被其他页面更新，请刷新后重试")


def _skill_state(state: dict[str, Any], skill_id: str) -> dict[str, Any]:
    record = state["skills"].setdefault(skill_id, {})
    record.setdefault("status", "unassessed")
    record.setdefault("weak", False)
    record.setdefault("focus", False)
    record.setdefault("logs", [])
    record.setdefault("photos", [])
    return record


def _skill(skill_ids: set[str], skill_id: str) -> None:
    if skill_id not in skill_ids:
        _fail(404, "未知的摄影学习技能")


def _gateway(gateway_ids: set[str] | None, gateway_id: str) -> None:
    if gateway_ids is None or gateway_id not in gateway_ids:
        _fail(404, "未知的摄影学习网关")


def _validate_gateway(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict) or "expected_revision" not in body:
        _fail(422, "请求必须包含 expected_revision")
    if (set(body) - (GATEWAY_FIELDS | {"expected_revision"})
            or not (set(body) & GATEWAY_FIELDS)):
        _fail(422, "仅允许更新 stage、answers、revealed 或 last_section")
    result: dict[str, Any] = {}
    if "stage" in body:
        if not isinstance(body["stage"], str) or body["stage"] not in GATEWAY_STAGES:
            _fail(422, "stage 值无效")
        result["stage"] = body["stage"]
    if "answers" in body:
        answers = body["answers"]
        if (not isinstance(answers, dict)
                or any(not isinstance(key, str) or key not in GATEWAY_ANSWER_KEYS for key in answers)
                or any(not isinstance(value, str) or len(value) > MAX_GATEWAY_ANSWER_CHARS
                       for value in answers.values())):
            _fail(422, "answers 格式无效")
        result["answers"] = answers
    if "revealed" in body:
        revealed = body["revealed"]
        if (not isinstance(revealed, list)
                or any(not isinstance(item, str) or item not in GATEWAY_REVEALED_KEYS for item in revealed)
                or len(set(revealed)) != len(revealed)):
            _fail(422, "revealed 必须是 observation、comparison、transfer 的无重复列表")
        result["revealed"] = revealed
    if "last_section" in body:
        if not isinstance(body["last_section"], str) or body["last_section"] not in GATEWAY_SECTIONS:
            _fail(422, "last_section 值无效")
        result["last_section"] = body["last_section"]
    return result


def _gateway_state(state: dict[str, Any], gateway_id: str) -> dict[str, Any]:
    record = state.setdefault("gateways", {}).setdefault(gateway_id, {})
    record.setdefault("stage", "unassessed")
    record.setdefault("answers", {})
    record.setdefault("revealed", [])
    record.setdefault("last_section", "problem")
    return record


def _validate_profile(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict) or "expected_revision" not in body:
        _fail(422, "请求必须包含 expected_revision")
    allowed = {"expected_revision", "status", "weak", "focus", "notes"}
    if set(body) - allowed or not (set(body) & (allowed - {"expected_revision"})):
        _fail(422, "仅允许更新 status、weak、focus 或 notes")
    result: dict[str, Any] = {}
    if "status" in body:
        if not isinstance(body["status"], str) or body["status"] not in STATUSES:
            _fail(422, "status 值无效")
        result["status"] = body["status"]
    for key in ("weak", "focus"):
        if key in body:
            if type(body[key]) is not bool:
                _fail(422, f"{key} 必须是布尔值")
            result[key] = body[key]
    if "notes" in body:
        if not isinstance(body["notes"], str) or len(body["notes"]) > MAX_NOTES_CHARS:
            _fail(422, f"notes 必须是 {MAX_NOTES_CHARS} 字以内的文本")
        result["notes"] = body["notes"]
    return result


def router(web_dir: Path, data_dir: Path) -> APIRouter:
    """Create routes over private JSON storage; caller's /api middleware owns auth/CSRF."""
    web_dir, data_dir = Path(web_dir), Path(data_dir)
    learning_dir = data_dir / "learning"
    state_path = learning_dir / "learning-state.json"
    state_lock = _lock_for(state_path)
    routes = APIRouter()

    @routes.get("/api/learning-state")
    def get_state():
        skill_ids = _load_skills(web_dir)
        gateway_ids = _load_gateways(web_dir)
        with state_lock:
            state = _read_state(state_path)
            # Unknown old IDs are never exposed after the canonical tree changes.
            state["skills"] = {key: value for key, value in state["skills"].items() if key in skill_ids}
            # Keep the exact legacy response shape until a gateway catalogue or
            # persisted gateway data exists. Unknown persisted records stay on disk.
            if gateway_ids is not None or "gateways" in state:
                state["gateways"] = {key: value for key, value in state.get("gateways", {}).items()
                                     if gateway_ids is not None and key in gateway_ids}
            return state

    @routes.put("/api/learning-state/{skill_id}")
    def put_skill(skill_id: str, body: dict[str, Any]):
        skill_ids = _load_skills(web_dir)
        _skill(skill_ids, skill_id)
        updates = _validate_profile(body)
        with state_lock:
            state = _read_state(state_path)
            _expected(body, state)
            record = _skill_state(state, skill_id)
            record.update(updates)
            state["revision"] += 1
            _write_state(state_path, state)
            return state

    @routes.put("/api/learning-gateways/{gateway_id}")
    def put_gateway(gateway_id: str, body: dict[str, Any]):
        gateway_ids = _load_gateways(web_dir)
        skill_ids = _load_skills(web_dir)
        _gateway(gateway_ids, gateway_id)
        updates = _validate_gateway(body)
        with state_lock:
            state = _read_state(state_path)
            _expected(body, state)
            record = _gateway_state(state, gateway_id)
            record.update(updates)
            state["revision"] += 1
            _write_state(state_path, state)
            # Return the shared state using the currently allowlisted IDs only;
            # the persisted unknown records remain untouched.
            state["skills"] = {key: value for key, value in state["skills"].items() if key in skill_ids}
            state["gateways"] = {key: value for key, value in state["gateways"].items()
                                 if key in gateway_ids}
            return state

    @routes.post("/api/learning-state/{skill_id}/logs", status_code=201)
    def add_log(skill_id: str, body: dict[str, Any]):
        skill_ids = _load_skills(web_dir)
        _skill(skill_ids, skill_id)
        allowed = {"expected_revision", "text", "photo_ids"}
        if set(body) - allowed or "expected_revision" not in body or not isinstance(body.get("text"), str):
            _fail(422, "日志需要 expected_revision 和 text")
        text = body["text"].strip()
        if not text or len(text) > MAX_LOG_CHARS:
            _fail(422, f"text 必须是 1 至 {MAX_LOG_CHARS} 字")
        photo_ids = body.get("photo_ids", [])
        if (not isinstance(photo_ids, list) or any(not isinstance(item, str) for item in photo_ids)
                or len(set(photo_ids)) != len(photo_ids)):
            _fail(422, "photo_ids 必须是无重复的字符串列表")
        with state_lock:
            state = _read_state(state_path)
            _expected(body, state)
            record = _skill_state(state, skill_id)
            existing_photos = {p.get("id") for p in record["photos"] if isinstance(p, dict)}
            if not set(photo_ids) <= existing_photos:
                _fail(422, "日志只能引用本技能中已保存的照片")
            record["logs"].append({"id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(),
                                   "text": text, **({"photo_ids": photo_ids} if photo_ids else {})})
            state["revision"] += 1
            _write_state(state_path, state)
            return state

    @routes.post("/api/learning-state/{skill_id}/photos", status_code=201)
    async def add_photo(skill_id: str, expected_revision: int = Form(...), caption: str = Form(""),
                        file: UploadFile = File(...)):
        skill_ids = _load_skills(web_dir)
        _skill(skill_ids, skill_id)
        if len(caption) > 1000:
            _fail(422, "caption 不能超过1000字")
        raw = await file.read(MAX_PHOTO_BYTES + 1)
        if not raw or len(raw) > MAX_PHOTO_BYTES:
            _fail(413 if len(raw) > MAX_PHOTO_BYTES else 422, "图片必须非空且不超过12 MiB")
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in IMAGE_FORMATS:
                    _fail(415, "仅支持 JPEG、PNG 或 WebP 图片")
                if image.width <= 0 or image.height <= 0 or image.width * image.height > MAX_PHOTO_PIXELS:
                    _fail(413, "图片尺寸超过允许范围")
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                if image.width * image.height > MAX_PHOTO_PIXELS:
                    _fail(413, "图片尺寸超过允许范围")
                extension = IMAGE_FORMATS[image.format]
        except HTTPException:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            _fail(415, "文件不是可解码的图片")
        digest = hashlib.sha256(raw).hexdigest()
        filename = f"{digest}.{extension}"
        photos_dir = learning_dir / "photos"
        with state_lock:
            if learning_dir.is_symlink() or photos_dir.is_symlink():
                _fail(503, "照片存储目录无效")
            state = _read_state(state_path)
            _expected({"expected_revision": expected_revision}, state)
            record = _skill_state(state, skill_id)
            photo_id = uuid.uuid4().hex
            photos_dir.mkdir(parents=True, exist_ok=True)
            target = photos_dir / filename
            if target.exists() and (target.is_symlink() or not target.is_file()):
                _fail(503, "照片存储路径无效")
            if not target.exists():
                fd, temporary = tempfile.mkstemp(prefix=".learning-photo-", suffix=".tmp", dir=photos_dir)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, target)
                finally:
                    try:
                        os.unlink(temporary)
                    except FileNotFoundError:
                        pass
            record["photos"].append({"id": photo_id, "src": f"/api/learning-photos/{filename}", "caption": caption})
            state["revision"] += 1
            _write_state(state_path, state)
            return state

    @routes.get("/api/learning-photos/{filename}")
    def get_photo(filename: str):
        if not PHOTO_NAME.fullmatch(filename):
            _fail(404, "照片不存在")
        photos_dir = learning_dir / "photos"
        target = photos_dir / filename
        try:
            if (learning_dir.is_symlink() or photos_dir.is_symlink()
                    or target.is_symlink() or not target.is_file()
                    or target.resolve().parent != photos_dir.resolve()):
                _fail(404, "照片不存在")
        except OSError:
            _fail(404, "照片不存在")
        response = FileResponse(target, media_type={"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[filename.rsplit(".", 1)[1]],
                               headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
        return response

    return routes
