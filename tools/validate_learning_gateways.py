"""Validate teaching provenance/relationships, never certify instructional quality."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse
from ref_lab.learning_media import SOURCE_CASE_MEDIA

CHAPTERS = ('problem', 'observe', 'principle', 'contrast', 'boundary', 'transfer', 'reflect', 'sources')
ACTIVITIES = {'observation', 'comparison', 'transfer'}

# Two course shapes share one catalogue. A course that declares no format keeps the
# chapter contract above; `field-guide-v1` replaces it with named operations. Any other
# value is a broken contract and is reported, never guessed at.
FIELD_GUIDE = 'field-guide-v1'
COURSE_FORMATS = {FIELD_GUIDE}
FIELD_GUIDE_BLOCKS = {'paragraph', 'heading', 'list', 'case', 'case_pair', 'comparison',
                      'tradeoffs', 'field_recipe', 'video_sequence', 'exercise', 'reveal'}
RECIPE_KEYS = {'type', 'id', 'problem', 'setup', 'instruction', 'target', 'comparison',
               'check', 'cost', 'why', 'source_ids'}
# Try first, read later: the two already-rendered reading blocks travel with this format
# unchanged. Their ids are free here, so a course asks only what it actually needs; the
# closed analysis must name an exercise the same course asks.
EXERCISE_KEYS = {'type', 'id', 'title', 'prompt', 'label'}
REVEAL_KEYS = {'type', 'activity_id', 'title', 'paragraphs', 'source_ids'}
RECIPE_TARGET_KEYS = {'text', 'basis', 'source_id', 'locator', 'conditions', 'proposed'}
RECIPE_COMPARISON_KEYS = {'case_ids', 'relation', 'conditions', 'look_for', 'controlled'}
VIDEO_KEYS = {'type', 'id', 'source_id', 'start_seconds', 'end_seconds', 'inspection', 'steps'}
INSPECTION_KEYS = {'method', 'detail', 'checked_at'}
# A stopping point is one of three honest kinds: something visible, something the source
# actually measured, or something this course proposes to try. The labels are the check.
STOPPING_BASES = ('visible_marker', 'source_measured', 'practice_start')
COMPARISON_RELATIONS = ('same_session', 'illustrative')
# Section ids are free in this format, but they still become element ids and anchors.
SECTION_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')

# Optional per-case teaching evidence. Each layer is independent; only the quote layer
# may claim the author's own wording, and only with a verified original-text check.
EVIDENCE_TEXT = re.compile(r'\S')
EVIDENCE_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
EVIDENCE_LAYERS = {
    'observation': ({'text'}, {'checked_at'}),
    'quote': ({'text'}, {'language', 'source_id', 'locator', 'checked_at', 'verification'}),
    'explanation': ({'text'}, {'source_ids', 'checked_at'}),
    'advice': ({'text'}, {'checked_at'}),
}
QUOTE_ONLY_FIELDS = {'language', 'verification', 'source_id', 'locator'}
QUOTE_VERIFICATIONS = {'unverified', 'verbatim_checked'}


def public_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlparse(value)
        return (url.scheme == 'https' and bool(url.hostname) and not url.username and not url.password
                and url.hostname not in {'localhost', '127.0.0.1', '::1'} and '\\' not in value)
    except ValueError:
        return False


def _text(value) -> bool:
    return isinstance(value, str) and bool(EVIDENCE_TEXT.search(value))


def _real_date(value) -> bool:
    """A shaped date is not a date: 2026-13-40 must never count as a checking date."""
    if not isinstance(value, str) or not EVIDENCE_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_case_evidence(evidence, case_id, source_ids: set, sources: dict,
                           case_url: str | None = None) -> list[str]:
    """Check the optional A/B/C/D teaching layers; absence stays valid and unchanged."""
    if evidence is None:
        return []
    label = f'{case_id}'
    if not isinstance(evidence, dict) or not evidence:
        return [f'Invalid case evidence block: {label}']
    errors = []
    for layer, value in evidence.items():
        if layer not in EVIDENCE_LAYERS:
            errors.append(f'Unknown case evidence layer: {label}/{layer}')
            continue
        required, optional = EVIDENCE_LAYERS[layer]
        if not isinstance(value, dict):
            errors.append(f'Missing case evidence {layer}: {label}')
            continue
        if not _text(value.get('text')):
            errors.append(f'Missing case evidence {layer} text: {label}')
        extra = set(value) - required - optional
        if extra:
            errors.append(f'Unknown case evidence {layer} fields: {label}/{sorted(extra)}')
        # Only the quote layer may speak for the author; C and D stay labelled as our own words.
        if layer != 'quote' and QUOTE_ONLY_FIELDS & set(value):
            errors.append(f'Case evidence {layer} cannot claim the author wording: {label}')
        if 'checked_at' in value and not _real_date(value['checked_at']):
            errors.append(f'Invalid case evidence {layer} date: {label}/{value.get("checked_at")!r}')
        if layer == 'explanation':
            listed = value.get('source_ids', [])
            if not isinstance(listed, list) or not all(isinstance(i, str) for i in listed):
                errors.append(f'Malformed case evidence explanation sources: {label}')
            elif not set(listed) <= source_ids:
                errors.append(f'Unknown case evidence explanation source: {label}')
        if layer == 'quote':
            errors.extend(_validate_quote(value, label, source_ids, sources, case_url))
    return errors


def _validate_quote(quote: dict, label: str, source_ids: set, sources: dict,
                    case_url: str | None = None) -> list[str]:
    errors = []
    verification = quote.get('verification')
    # A list, dict or absent level is unverified too; hashing it against the allowed
    # names must not raise, it only has to stay conservative.
    if not isinstance(verification, str) or verification not in QUOTE_VERIFICATIONS:
        return [f'Unknown case evidence quote verification: {label}/{verification!r}']
    if verification == 'verbatim_checked':
        source_id = quote.get('source_id')
        source = sources.get(source_id) if isinstance(source_id, str) else None
        if not (isinstance(source_id, str) and source_id in source_ids and source
                and source.get('url')):
            errors.append(f'Verified quote needs a known source: {label}/{source_id!r}')
        else:
            # Two pages that fail the same unsafe way are not evidence of a matching page.
            if not public_url(source['url']):
                errors.append(f'Verified quote needs a public source page: {label}/{source_id!r}')
            if not public_url(case_url):
                errors.append(f'Verified quote needs a public case page: {label}')
            elif source['url'] != case_url:
                # Another case's source may not be promoted into this author's verified record.
                errors.append(f'Veified quote source is not this case page: {label}/{source_id!r}')
        if not _text(quote.get('text')):
            errors.append(f'Verified quote needs the quoted words themselves: {label}')
        if not _text(quote.get('locator')) or not _text(quote.get('language')):
            errors.append(f'Verified quote needs a text locator and language: {label}')
        if not _real_date(quote.get('checked_at')):
            errors.append(f'Verified quote needs the real checking date: {label}')
    return errors


def _number(value) -> bool:
    """A real finite number. Booleans and strings are not seconds."""
    return type(value) in (int, float) and value == value and value not in (float('inf'), float('-inf'))


def _text_list(value) -> bool:
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def _id_list(value) -> list[str] | None:
    """A flat list of string ids, or None when the shape itself is wrong.

    Every id list is checked with this before it reaches a set, a membership test or a
    loop: a nested list or an object is a broken contract to report, not a TypeError to
    raise out of the validator.
    """
    if not isinstance(value, list):
        return None
    return list(value) if all(isinstance(item, str) for item in value) else None


def validate_field_recipe(block: dict, label: str, source_ids: set, case_ids: set) -> list[str]:
    """One field operation: problem, setup, instruction, stopping point, comparison,
    check, cost, and why. Every limit that changes what the reader can actually do
    sits next to the operation, not in a trailing appendix."""
    errors = [f'Unknown field recipe fields: {label}/{sorted(set(block) - RECIPE_KEYS)}'
              if set(block) - RECIPE_KEYS else '']
    for name in ('problem', 'setup', 'instruction', 'cost', 'why'):
        if not _text(block.get(name)):
            errors.append(f'Missing field recipe {name}: {label}')
    target = block.get('target')
    if not isinstance(target, dict):
        errors.append(f'Missing field recipe target: {label}')
    else:
        errors.extend(_validate_recipe_target(target, label, source_ids))
    comparison = block.get('comparison')
    if not isinstance(comparison, dict):
        errors.append(f'Missing field recipe comparison: {label}')
    else:
        errors.extend(_validate_recipe_comparison(comparison, label, case_ids))
    check = block.get('check')
    if not isinstance(check, dict):
        errors.append(f'Missing field recipe check: {label}')
    elif not _text(check.get('success')) or not _text(check.get('if_failed')):
        errors.append(f'Field recipe needs both success and failure handling: {label}')
    listed = block.get('source_ids')
    if not _text_list(listed):
        errors.append(f'Malformed field recipe sources: {label}')
    elif not set(listed) <= source_ids:
        errors.append(f'Unknown field recipe source: {label}')
    return [error for error in errors if error]


def _validate_recipe_target(target: dict, label: str, source_ids: set) -> list[str]:
    errors = []
    if set(target) - RECIPE_TARGET_KEYS:
        errors.append(f'Unknown field recipe target fields: {label}/{sorted(set(target) - RECIPE_TARGET_KEYS)}')
    if not _text(target.get('text')):
        errors.append(f'Missing field recipe stopping point: {label}')
    basis = target.get('basis')
    if basis not in STOPPING_BASES:
        # An unnamed basis cannot be read as a measurement later on.
        return errors + [f'Unknown stopping point basis: {label}/{basis!r}']
    if basis == 'source_measured':
        if not _text(target.get('locator')) or not _text_list(target.get('conditions')):
            errors.append(f'Measured stopping point needs a locator and conditions: {label}')
        source_id = target.get('source_id')
        if not isinstance(source_id, str) or source_id not in source_ids:
            errors.append(f'Measured stopping point needs a course source: {label}/{source_id!r}')
        # Measured and proposed are opposite claims; a block may not make both.
        if target.get('proposed') is True:
            errors.append(f'Stopping point cannot be measured and proposed: {label}')
    elif basis == 'practice_start':
        # A proposed starting point says so, in the data, not only in the prose.
        if target.get('proposed') is not True:
            errors.append(f'Proposed starting point must declare proposed=true: {label}')
        if target.get('source_id') or target.get('locator'):
            errors.append(f'Proposed starting point may not borrow measured evidence: {label}')
    else:
        for borrowed in ('source_id', 'locator', 'conditions'):
            if target.get(borrowed):
                errors.append(f'Visible stopping point may not carry {borrowed}: {label}')
    return errors


def _validate_recipe_comparison(comparison: dict, label: str, case_ids: set) -> list[str]:
    errors = []
    if set(comparison) - RECIPE_COMPARISON_KEYS:
        errors.append(f'Unknown field recipe comparison fields: {label}/{sorted(set(comparison) - RECIPE_COMPARISON_KEYS)}')
    listed = comparison.get('case_ids')
    # The comparison shows real pictures from this same course, not remembered ones.
    if not _text_list(listed) or not set(listed) <= case_ids:
        errors.append(f'Field recipe comparison cases must belong to this course: {label}')
    relation = comparison.get('relation')
    if relation not in COMPARISON_RELATIONS:
        return errors + [f'Unknown field recipe comparison relation: {label}/{relation!r}']
    if not _text_list(comparison.get('conditions')) or not _text(comparison.get('look_for')):
        errors.append(f'Malformed field recipe comparison: {label}')
    if relation == 'illustrative' and comparison.get('controlled') is not False:
        # Illustrative pictures are not a controlled before/after; saying only that is
        # not enough, the data has to carry the claim itself.
        errors.append(f'Illustrative comparison must declare controlled=false: {label}')
    return errors


def validate_video_sequence(block: dict, label: str, source_ids: set) -> list[str]:
    """A time-indexed reading order over one original source. The JSON records what was
    written down; it never proves anyone watched the video, so no field here may imply it."""
    errors = []
    if set(block) - VIDEO_KEYS:
        errors.append(f'Unknown video sequence fields: {label}/{sorted(set(block) - VIDEO_KEYS)}')
    if not isinstance(block.get('source_id'), str) or block['source_id'] not in source_ids:
        errors.append(f'Video sequence needs a course source: {label}/{block.get("source_id")!r}')
    start, end = block.get('start_seconds'), block.get('end_seconds')
    if not (_number(start) and _number(end) and start >= 0 and end > start):
        errors.append(f'Video sequence needs a finite 0 <= start < end interval: {label}')
    inspection = block.get('inspection')
    if (not isinstance(inspection, dict) or inspection.get('method') != 'continuous_segment'
            or not _text(inspection.get('detail')) or not _real_date(inspection.get('checked_at'))
            or set(inspection) - INSPECTION_KEYS):
        errors.append(f'Malformed video sequence inspection record: {label}')
    steps = block.get('steps')
    if not _text_list(steps) and not (isinstance(steps, list) and steps):
        errors.append(f'Missing video sequence steps: {label}')
        return [error for error in errors if error]
    previous = None
    for step in steps:
        if not isinstance(step, dict) or not _text(step.get('stage')) or not _text(step.get('summary')):
            errors.append(f'Malformed video sequence step: {label}')
            continue
        step_start, step_end = step.get('start_seconds'), step.get('end_seconds')
        if not (_number(step_start) and _number(step_end) and step_start >= 0 and step_end > step_start):
            errors.append(f'Video step needs a finite 0 <= start < end interval: {label}/{step.get("stage")}')
            continue
        if _number(start) and _number(end) and (step_start < start or step_end > end):
            errors.append(f'Video step lies outside the sequence interval: {label}/{step.get("stage")}')
        if previous is not None and step_start < previous:
            errors.append(f'Video steps are out of order: {label}/{step.get("stage")}')
        previous = step_start
    return [error for error in errors if error]


def _valid_id(value, seen: set) -> bool:
    """Free, element-safe and unique within this course. The type is settled first: a
    list id must never reach a set or a membership test."""
    if not isinstance(value, str) or not SECTION_ID.match(value) or value in seen:
        return False
    seen.add(value)
    return True


def _valid_exercise(block: dict, label: str, exercises: set) -> list[str]:
    """A free, unique id: this format asks the questions it needs, not three named ones."""
    errors = []
    if set(block) - EXERCISE_KEYS:
        errors.append(f'Unknown field-guide exercise fields: {label}/{sorted(set(block) - EXERCISE_KEYS)}')
    if not _valid_id(block.get('id'), exercises):
        errors.append(f'Invalid field-guide exercise ID: {label}/{block.get("id")!r}')
    if not _text(block.get('title')) or not _text(block.get('prompt')):
        errors.append(f'Malformed field-guide exercise: {label}')
    return errors


def _valid_reveal(block: dict, label: str, exercises: set, reveals: set, source_ids: set) -> list[str]:
    """The closed answer to one of this course's own exercises, cited to its sources."""
    errors = []
    if set(block) - REVEAL_KEYS:
        errors.append(f'Unknown field-guide reveal fields: {label}/{sorted(set(block) - REVEAL_KEYS)}')
    activity = block.get('activity_id')
    if not isinstance(activity, str) or activity not in exercises:
        errors.append(f'Field-guide reveal needs one of this course\'s exercises: {label}/{activity!r}')
    elif activity in reveals:
        errors.append(f'Field-guide reveal repeats an exercise already answered: {label}/{activity}')
    else:
        reveals.add(activity)
    if not _text(block.get('title')) or not _text_list(block.get('paragraphs')):
        errors.append(f'Malformed field-guide reveal: {label}')
    listed = _id_list(block.get('source_ids'))
    if listed is None or not set(listed) <= source_ids:
        errors.append(f'Unknown field-guide reveal source: {label}')
    return errors


def validate_field_guide_sections(gateway: dict, ident: str, cases: dict, source_ids: set,
                                  sources: dict) -> list[str]:
    """Free unique section ids and named operations: no eight chapters, no three
    activities, and no self-assessment, because this course is read, not scored."""
    errors = []
    sections = gateway.get('sections')
    if not isinstance(sections, list) or not sections:
        return [f'Field-guide course needs sections: {ident}']
    seen_sections, seen_blocks, exercises = set(), set(), set()
    pending_reveals = []
    for section in sections:
        if not isinstance(section, dict):
            errors.append(f'Field-guide section must be an object: {ident}')
            continue
        sid = section.get('id')
        if not _valid_id(sid, seen_sections):
            errors.append(f'Invalid field-guide section ID: {ident}/{sid!r}')
        if not _text(section.get('title')):
            errors.append(f'Missing field-guide section title: {ident}/{sid}')
        listed = _id_list(section.get('source_ids', []))
        if listed is None or not set(listed) <= source_ids:
            errors.append(f'Malformed field-guide section source: {ident}/{sid}')
        blocks = section.get('blocks')
        if not isinstance(blocks, list) or not blocks:
            errors.append(f'Empty field-guide section: {ident}/{sid}')
            continue
        for block in blocks:
            kind = block.get('type') if isinstance(block, dict) else None
            label = f'{ident}/{sid}'
            if not isinstance(kind, str) or kind not in FIELD_GUIDE_BLOCKS:
                errors.append(f'Invalid field-guide block {kind}: {label}')
                continue
            if kind == 'paragraph' or kind == 'heading':
                if not _text(block.get('text')):
                    errors.append(f'Empty field-guide block {kind}: {label}')
            elif kind == 'list':
                if not _text_list(block.get('items')):
                    errors.append(f'Malformed field-guide list: {label}')
            elif kind in {'comparison', 'tradeoffs'}:
                keys = ('novice', 'expert', 'question') if kind == 'comparison' else ('action', 'effect', 'cost', 'test')
                rows = block.get('rows')
                if not isinstance(rows, list) or not rows or not all(
                        isinstance(row, dict) and all(_text(row.get(key)) for key in keys) for row in rows):
                    errors.append(f'Malformed field-guide {kind}: {label}')
            elif kind == 'case':
                if not isinstance(block.get('case_id'), str) or block['case_id'] not in cases:
                    errors.append(f'Field-guide case block references an unknown case: {label}')
            elif kind == 'case_pair':
                ids = _id_list(block.get('case_ids'))
                if not ids or not set(ids) <= cases.keys():
                    errors.append(f'Field-guide case pair references unknown cases: {label}')
            elif kind == 'exercise':
                errors.extend(_valid_exercise(block, label, exercises))
            elif kind == 'reveal':
                # Checked after every section: a reveal may answer an exercise the course
                # asks in either direction, and one exercise is answered once.
                pending_reveals.append((block, label))
            else:
                block_id = block.get('id')
                if not _valid_id(block_id, seen_blocks):
                    errors.append(f'Invalid field-guide {kind} ID: {label}/{block_id!r}')
                    continue
                errors.extend(validate_field_recipe(block, f'{label}/{block_id}', source_ids, cases.keys())
                              if kind == 'field_recipe'
                              else validate_video_sequence(block, f'{label}/{block_id}', source_ids))
    reveals = set()
    for block, label in pending_reveals:
        errors.extend(_valid_reveal(block, label, exercises, reveals, source_ids))
    return errors


def validate_gateways(catalog: dict, tree: dict, learning_content: dict | None = None,
                      extra_source_media: dict | None = None) -> list[str]:
    # A separate extension registry is copied in for this call only; the base map
    # keeps owning exactly its own reviewed cases and is never mutated here.
    source_media = dict(SOURCE_CASE_MEDIA)
    if extra_source_media:
        source_media.update(extra_source_media)
    errors = []
    if not isinstance(catalog, dict) or catalog.get('schema_version') != 1:
        return ['Invalid gateway schema']
    if not isinstance(catalog.get('gateways'), list) or not isinstance(catalog.get('sources'), list):
        return ['Gateway catalogue requires gateways and sources lists']
    skills = {s['id'] for s in tree['skills']}
    content = learning_content or {}
    media = {m['id']: m for m in content.get('media', [])}
    media_sources = {s['id']: s for s in content.get('sources', [])}
    sources, seen = {}, set()
    for source in catalog['sources']:
        if not isinstance(source, dict):
            errors.append('Invalid gateway source: a source record must be an object')
            continue
        ident = source.get('id')
        if not isinstance(ident, str) or not ident or ident in sources:
            errors.append(f'Duplicate/missing gateway source ID: {ident!r}')
        else:
            sources[ident] = source
        if not public_url(source.get('url')):
            errors.append(f'Unsafe source URL: {ident}')
        for name in ('title', 'author', 'reading_depth', 'checked_at', 'locator', 'support', 'limitation'):
            if not isinstance(source.get(name), str) or not source[name].strip():
                errors.append(f'Missing source {name}: {ident}')
    for gateway in catalog['gateways']:
        if not isinstance(gateway, dict):
            errors.append('Invalid gateway: a gateway entry must be an object')
            continue
        ident = gateway.get('id')
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append(f'Duplicate/missing gateway ID: {ident!r}')
        seen.add(ident)
        for name in ('title', 'question', 'outcome', 'method', 'author', 'reading_depth', 'prior_knowledge'):
            if not isinstance(gateway.get(name), str) or not gateway[name].strip():
                errors.append(f'Missing gateway {name}: {ident}')
        listed_skills = _id_list(gateway.get('skill_ids'))
        if not listed_skills or not set(listed_skills) <= skills:
            errors.append(f'Unknown or missing skill mapping: {ident}')
        # ID types are settled before anything becomes a set: a nested id is a broken
        # course to report, never a TypeError out of the validator.
        listed_sources = _id_list(gateway.get('source_ids', []))
        if listed_sources is None:
            errors.append(f'Malformed source mapping: {ident}')
        source_ids = set(listed_sources or [])
        if not source_ids or not source_ids <= sources.keys():
            errors.append(f'Unknown source mapping: {ident}')
        raw_cases = gateway.get('cases', [])
        if not isinstance(raw_cases, list):
            errors.append(f'Invalid case list: {ident}')
            raw_cases = []
        cases = {}
        for case in raw_cases:
            if not isinstance(case, dict):
                errors.append(f'Invalid case entry: {ident}')
                continue
            cid = case.get('id')
            if not isinstance(cid, str) or not cid or cid in cases:
                errors.append(f'Duplicate/missing case: {ident}/{cid!r}')
            else:
                cases[cid] = case
            if not public_url(case.get('url')):
                errors.append(f'Unsafe case URL: {cid}')
            rights, review = case.get('rights'), case.get('review')
            # A rights or review record that is not an object is missing, not a shape to
            # dereference; both are reported and the case keeps failing its own checks.
            rights = rights if isinstance(rights, dict) else {}
            review = review if isinstance(review, dict) else {}
            if not public_url(rights.get('url')) or not rights.get('statement') or type(rights.get('allowed')) is not bool:
                errors.append(f'Missing rights record: {cid}')
            if review.get('level') != 'pixel_reviewed' or not review.get('detail') or not review.get('checked_at'):
                errors.append(f'Missing actual image review: {cid}')
            if case.get('display') == 'licensed_remote':
                if not public_url(case.get('src')) or not rights.get('allowed') or not rights.get('license'):
                    errors.append(f'Unlicensed image or invalid rights/URL: {cid}')
                else:
                    image_url = urlparse(case['src'])
                    if (image_url.netloc != 'thumb.wikimedia.org'
                            or not image_url.path.startswith('/wikipedia/commons/thumb/')):
                        errors.append(f'Image outside the learning page policy: {cid}')
                if any(type(case.get(k)) is not int or case[k] <= 0 for k in ('width', 'height')):
                    errors.append(f'Missing intrinsic image dimensions: {cid}')
            elif case.get('display') == 'source_remote':
                images = case.get('images', [])
                registered = source_media.get(cid)
                if (not isinstance(images, list) or not images or not registered
                        or tuple(i.get('src') for i in images if isinstance(i, dict)) != registered
                        or case.get('src')):
                    errors.append(f'Source image outside the learning page policy: {cid}')
                for image in images if isinstance(images, list) else []:
                    if (not isinstance(image, dict) or not public_url(image.get('src'))
                            or not image.get('alt')
                            or any(type(image.get(k)) is not int or image[k] <= 0 for k in ('width', 'height'))):
                        errors.append(f'Missing source image metadata/dimensions: {cid}')
                summary = case.get('source_summary', {})
                if (not isinstance(summary, dict)
                        or any(not isinstance(summary.get(k), str) or not summary[k].strip()
                               for k in ('text', 'locator', 'source_id', 'checked_at'))
                        or summary.get('source_id') not in source_ids
                        or sources.get(summary.get('source_id'), {}).get('url') != case.get('url')):
                    errors.append(f'Missing or mismatched source summary: {cid}')
            elif case.get('display') == 'note_media':
                images = case.get('images', [])
                if (not isinstance(images, list) or not images or case.get('src')
                        or not any(sources.get(s, {}).get('url') == case.get('url') for s in source_ids)):
                    errors.append(f'Invalid local media source: {cid}')
                for image in images if isinstance(images, list) else []:
                    entry = media.get(image.get('media_id')) if isinstance(image, dict) else None
                    if not entry:
                        errors.append(f'Unregistered local media: {cid}')
                    elif media_sources.get(entry['source_id'], {}).get('url') != case.get('url'):
                        errors.append(f'Local media source mismatch: {cid}')
                    if isinstance(image, dict) and image.get('src'):
                        errors.append(f'Local media cannot override registered URL: {cid}')
            elif case.get('display') != 'external_only' or case.get('src') or case.get('images'):
                errors.append(f'Invalid case display/rights: {cid}')
            for name in ('author', 'title', 'caption', 'alt'):
                if not case.get(name):
                    errors.append(f'Missing case {name}: {cid}')
            errors.extend(validate_case_evidence(case.get('evidence'), cid,
                                                 source_ids, sources, case.get('url')))
        sections = gateway.get('sections', [])
        # An undeclared format is the chapter contract. A declared one must be known:
        # an unrecognised format is reported as invalid, never read as the old shape.
        course_format = gateway.get('course_format')
        if 'course_format' in gateway and (not isinstance(course_format, str)
                                           or course_format not in COURSE_FORMATS):
            errors.append(f'Unknown course format: {ident}/{course_format!r}')
            continue
        if course_format == FIELD_GUIDE:
            if gateway.get('kind') != 'course':
                errors.append(f'Field-guide format requires kind=course: {ident}')
            errors.extend(validate_field_guide_sections(gateway, ident, cases, source_ids, sources))
            continue
        if not isinstance(sections, list) or [s.get('id') for s in sections if isinstance(s, dict)] != list(CHAPTERS):
            errors.append(f'Invalid gateway chapters: {ident}')
        exercises, reveals, earlier_cases, transfer_cases = set(), set(), set(), set()
        for section in sections:
            if not isinstance(section, dict) or not section.get('title') \
                    or not isinstance(section.get('blocks'), list) or not section['blocks']:
                errors.append(f'Empty teaching section: {ident}')
                continue
            listed = _id_list(section.get('source_ids', []))
            if listed is None or not set(listed) <= source_ids:
                errors.append(f'Unknown section source: {ident}/{section.get("id")}')
            for block in section['blocks']:
                if not isinstance(block, dict):
                    errors.append(f'Invalid teaching block: {ident}/{section.get("id")}')
                    continue
                kind = block.get('type')
                if kind in {'paragraph', 'heading'}:
                    valid = isinstance(block.get('text'), str) and bool(block['text'].strip())
                elif kind == 'list':
                    valid = bool(block.get('items')) and all(isinstance(i, str) and i for i in block['items'])
                elif kind == 'comparison':
                    valid = bool(block.get('rows')) and all(all(r.get(k) for k in ('novice', 'expert', 'question')) for r in block['rows'])
                elif kind == 'tradeoffs':
                    valid = bool(block.get('rows')) and all(all(r.get(k) for k in ('action', 'effect', 'cost', 'test')) for r in block['rows'])
                elif kind == 'case':
                    ids = [block['case_id']] if isinstance(block.get('case_id'), str) else []
                    valid = bool(ids) and set(ids) <= cases.keys()
                    (transfer_cases if section['id'] == 'transfer' else earlier_cases).update(ids)
                elif kind == 'case_pair':
                    ids = _id_list(block.get('case_ids', [])) or []
                    valid = bool(ids) and set(ids) <= cases.keys()
                    (transfer_cases if section['id'] == 'transfer' else earlier_cases).update(ids)
                elif kind == 'exercise':
                    valid = isinstance(block.get('id'), str) and block['id'] in ACTIVITIES \
                        and block['id'] not in exercises and block.get('title') and block.get('prompt')
                    if isinstance(block.get('id'), str):
                        exercises.add(block['id'])
                elif kind == 'reveal':
                    valid = isinstance(block.get('activity_id'), str) and block['activity_id'] in ACTIVITIES \
                        and block.get('title') and block.get('paragraphs')
                    if isinstance(block.get('activity_id'), str):
                        reveals.add(block['activity_id'])
                    analysis = _id_list(block.get('source_ids', []))
                    if analysis is None or not set(analysis) <= source_ids:
                        errors.append(f'Unknown analysis source: {ident}')
                else:
                    valid = False
                if not valid:
                    errors.append(f'Invalid teaching block {kind}: {ident}/{section.get("id")}')
        if exercises != ACTIVITIES or not {'observation', 'comparison', 'transfer'} <= reveals:
            errors.append(f'Incomplete observation/contrast/transfer: {ident}')
        if not transfer_cases or transfer_cases & earlier_cases:
            errors.append(f'Transfer needs a previously unanalysed case: {ident}')
    return errors
