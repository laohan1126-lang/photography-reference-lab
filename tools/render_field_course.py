"""Export a field-guide course JSON to Markdown for offline reading.

The JSON stays the only teaching source: this tool reads it, checks it against the same
contract the site enforces, and prints what a reader would see — the operations, the real
comparison pictures, the video navigation and one closed source record. It never writes
lesson prose of its own, invents a step, or turns a rejected payload into a document.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_learning_gateways import FIELD_GUIDE, validate_gateways
from ref_lab.action_directing_media import ACTION_DIRECTING_SOURCE_CASE_MEDIA

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs/research/photography-atlas"
DEFAULT_SOURCES = RESEARCH / "GATEWAYS.json"
DEFAULT_TREE = RESEARCH / "SKILL_TREE.json"
DEFAULT_CONTENT = RESEARCH / "LEARNING_CONTENT.json"
DEFAULT_OUTPUT = ROOT / ".local/field-course.md"

BASIS_LABEL = {
    "visible_marker": "画面里能直接看见的停止点",
    "source_measured": "来源实测的停止点",
    "practice_start": "建议练习起点（不是作者实测）",
}
RELATION_LABEL = {
    "same_session": "同一次拍摄内",
    "illustrative": "姿态与拍法参照",
}


def clock(value) -> str:
    total = int(value)
    return f"{total // 60:02d}:{total % 60:02d}"


def read_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} not found at {path}. Nothing is rendered.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} at {path} is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} at {path} must contain a JSON object.")
    return value


def timed_url(url: str, seconds) -> str:
    """A deep link to the original source page. No embed, no proxy, no download."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return ""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "t"]
    query.append(("t", f"{int(seconds)}s"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def find_course(catalog: dict, course_id: str | None) -> dict:
    gateways = catalog.get("gateways")
    if not isinstance(gateways, list):
        raise ValueError("Course payload requires a gateways list.")
    if course_id:
        for gateway in gateways:
            if isinstance(gateway, dict) and gateway.get("id") == course_id:
                return gateway
        raise ValueError(f"No course named {course_id!r} in the payload.")
    courses = [g for g in gateways if isinstance(g, dict) and g.get("course_format") == FIELD_GUIDE]
    if len(courses) != 1:
        raise ValueError(
            "Name one course with --course-id: the payload holds "
            f"{len(courses)} field-guide course(s)."
        )
    return courses[0]


def render(course: dict, sources: dict, media: dict | None = None) -> str:
    media = media or {}
    lines = [f"# {course['title']}", ""]
    meta = " · ".join(str(value) for value in (course.get("author"), course.get("reading_depth")) if value)
    if meta:
        lines += [meta, ""]
    if course.get("outcome"):
        lines += [course["outcome"], ""]
    if course.get("prior_knowledge"):
        lines += [f"*先修：{course['prior_knowledge']}*", ""]

    def case_markdown(case: dict) -> list[str]:
        out = [f"**{case['title']}** — {case['author']} · {case['caption']}", ""]
        images = case.get("images") or []
        for image in images:
            if isinstance(image, dict) and image.get("src"):
                out += [f"![{image.get('alt', '')}]({image['src']})", ""]
            elif isinstance(image, dict) and image.get('media_id') in media:
                frame = media[image['media_id']]
                out += [f"已核验视频帧：{image.get('label') or frame.get('position', '')} · {frame.get('alt', '')}",
                        f"[回看原视频画面]({case.get('url', '')})（本地阅读器内显示登记原帧）", ""]
        out += [f"原案例与图像出处：{case.get('url', '')}", ""]
        record = []
        summary = case.get("source_summary")
        if isinstance(summary, dict) and summary.get("text"):
            record += [summary["text"], "",
                       f"原文定位：{summary.get('locator', '')} · 核对于 {summary.get('checked_at', '')}", ""]
        evidence = case.get("evidence")
        if isinstance(evidence, dict):
            for layer in ("observation", "quote", "explanation", "advice"):
                value = evidence.get(layer)
                if isinstance(value, dict) and isinstance(value.get("text"), str) and value["text"].strip():
                    record += [f"- **{layer}**：{value['text'].strip()}"]
            if record:
                record.append("")
        review = case.get("review")
        if isinstance(review, dict) and review.get("detail"):
            record += [f"- 图像核验范围：{review['detail']}", ""]
        rights = case.get("rights")
        if isinstance(rights, dict) and rights.get("statement"):
            record += [f"- 使用与限制：{rights['statement']} {rights.get('url', '')}", ""]
        if record:
            out += ["<details>", "<summary>来源与研究记录</summary>", ""] + record + ["</details>", ""]
        return out

    def recipe_markdown(block: dict) -> list[str]:
        target, comparison, check = block["target"], block["comparison"], block["check"]
        out = [f"### {block['instruction']}", ""]
        out += [f"- **要解决的问题**：{block['problem']}",
                f"- **先准备什么**：{block['setup']}", ""]
        out += [f"**做到这里就停 · {BASIS_LABEL.get(target['basis'], target['basis'])}**", "", target["text"], ""]
        if target["basis"] == "source_measured":
            source = sources.get(target.get("source_id"), {})
            out += [f"原文定位：{target.get('locator', '')} · 出处：{source.get('url', '')}", ""]
            out += [f"- {condition}" for condition in target.get("conditions", [])]
            out += [""]
        elif target["basis"] == "practice_start":
            out += ["这是本课程提出的练习起点，不是作者实测的数值；拍出来以后以你自己的照片为准。", ""]
        out += [f"**实际对照照片 · {RELATION_LABEL.get(comparison['relation'], comparison['relation'])}**", ""]
        out += ["；".join(comparison.get("conditions", [])), ""]
        by_id = {case.get("id"): case for case in course.get("cases", [])}
        for case_id in comparison.get("case_ids", []):
            case = by_id.get(case_id)
            if case:
                out += case_markdown(case)
        out += [f"**看什么**：{comparison['look_for']}", ""]
        out += ["**怎么算做到**", "", check["success"], "",
                f"**没做到怎么办**：{check['if_failed']}", "",
                f"**代价**：{block['cost']}", "", block["why"], ""]
        cited = [sources.get(i, {}) for i in block.get("source_ids", [])]
        links = [f"- {s.get('title', '')} — {s.get('url', '')}" for s in cited if s.get("url")]
        if links:
            out += ["本条依据：", ""] + links + [""]
        return out

    def video_markdown(block: dict) -> list[str]:
        source = sources.get(block["source_id"], {})
        url = source.get("url", "")
        span = f"{clock(block['start_seconds'])}–{clock(block['end_seconds'])}"
        out = [f"### {source.get('title', block['source_id'])} · {span}", "",
               "按时间点回看老师的动作，再用停点检查自己的下一张。", ""]
        for step in block["steps"]:
            link = timed_url(url, step["start_seconds"])
            label = f"{clock(step['start_seconds'])}–{clock(step['end_seconds'])}"
            out += [f"- {f'[{label}]({link})' if link else label} · **{step['stage']}** — {step['summary']}"]
        inspection = block.get("inspection", {})
        out += ["", '<details>', '<summary>片段核对范围</summary>', '',
                f"{inspection.get('detail', '')} · 核对于 {inspection.get('checked_at', '')}", '', '</details>', '']
        return out

    def activity_markdown(block: dict) -> list[str]:
        """The two blocks a field course already renders: the question is asked in the
        open, and the analysis stays folded until the reader has tried it."""
        if block["type"] == "exercise":
            return [f"#### {block['title']}", "", block["prompt"], ""]
        out = ["<details>", f"<summary>{block['title']}</summary>", ""]
        out += [f"{paragraph}\n" for paragraph in block["paragraphs"]]
        cited = [sources.get(i, {}) for i in block.get("source_ids", [])]
        links = [f"- {s.get('title', '')} — {s.get('url', '')}" for s in cited if s.get("url")]
        if links:
            out += ["分析依据：", ""] + links + [""]
        return out + ["</details>", ""]

    for index, section in enumerate(course.get("sections", []), start=1):
        lines += [f"## {index:02d} {section['title']}", ""]
        for block in section.get("blocks", []):
            kind = block.get("type")
            if kind == "paragraph":
                lines += [block["text"], ""]
            elif kind == "heading":
                lines += [f"### {block['text']}", ""]
            elif kind == "list":
                lines += [f"- {item}" for item in block["items"]] + [""]
            elif kind == "comparison":
                for row in block["rows"]:
                    lines += [f"- 第一眼可能会问：{row['novice']}", f"  - 再往下观察：{row['expert']}",
                              f"  - 追问：{row['question']}", ""]
            elif kind == "tradeoffs":
                for row in block["rows"]:
                    lines += [f"- **{row['action']}** — 预计变化：{row['effect']}；代价：{row['cost']}；"
                              f"怎样检查：{row['test']}", ""]
            elif kind == "case":
                case = next((c for c in course.get("cases", []) if c.get("id") == block["case_id"]), None)
                if case:
                    lines += case_markdown(case)
            elif kind == "case_pair":
                for case_id in block["case_ids"]:
                    case = next((c for c in course.get("cases", []) if c.get("id") == case_id), None)
                    if case:
                        lines += case_markdown(case)
            elif kind == "exercise" or kind == "reveal":
                lines += activity_markdown(block)
            elif kind == "field_recipe":
                lines += recipe_markdown(block)
            elif kind == "video_sequence":
                lines += video_markdown(block)

    listed = [sources.get(i, {}) for i in course.get("source_ids", [])]
    if listed:
        lines += ["<details>", "<summary>来源与研究记录</summary>", ""]
        for source in listed:
            lines += [f"**{source.get('title', '')}** — {source.get('author', '')}",
                      f"{source.get('url', '')} · {source.get('reading_depth', '')} · 核对于 {source.get('checked_at', '')}",
                      "", f"- 定位：{source.get('locator', '')}", f"- 支持什么：{source.get('support', '')}",
                      f"- 边界：{source.get('limitation', '')}", ""]
        lines += ["</details>", ""]
    return "\n".join(lines).rstrip() + "\n"


def export(course_file: Path, course_id: str | None, sources_file: Path, tree_file: Path,
           content_file: Path | None = None) -> str:
    payload = read_json(course_file, "Field-guide course payload")
    base = read_json(sources_file, "Gateway source catalogue")
    tree = read_json(tree_file, "Skill tree")
    content = read_json(content_file, "Learning content") if content_file and content_file.is_file() else None
    errors = validate_gateways(
        {**payload, "schema_version": 1, "sources": payload.get("sources", base.get("sources", []))},
        tree, content, extra_source_media=ACTION_DIRECTING_SOURCE_CASE_MEDIA)
    if errors:
        raise ValueError("Field-guide course integrity failed: " + "; ".join(errors[:20]))
    course = find_course(payload, course_id)
    if course.get("course_format") != FIELD_GUIDE:
        raise ValueError(f"{course.get('id')} is not a {FIELD_GUIDE} course.")
    known = {s.get("id"): s for s in base.get("sources", []) if isinstance(s, dict)}
    known.update({s.get("id"): s for s in payload.get("sources", []) if isinstance(s, dict)})
    missing = {i for i in course.get("source_ids", []) if i not in known}
    if missing:
        raise ValueError(f"Course sources are not in the catalogue: {sorted(missing)}")
    return render(course, known, {m['id']: m for m in (content or {}).get('media', [])})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("course", type=Path, help="Field-guide course JSON object to export.")
    parser.add_argument("--course-id", default=None, help="Course ID; required when the file holds several.")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="GATEWAYS.json holding source records.")
    parser.add_argument("--tree", type=Path, default=DEFAULT_TREE, help="SKILL_TREE.json for skill mapping.")
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT, help="LEARNING_CONTENT.json, when present.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Markdown output path.")
    args = parser.parse_args()
    try:
        markdown = export(args.course, args.course_id, args.sources, args.tree, args.content)
    except ValueError as error:
        print(f"FAIL: {error}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"WROTE: {args.output} ({len(markdown)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
