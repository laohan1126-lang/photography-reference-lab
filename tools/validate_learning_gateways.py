"""Validate teaching provenance/relationships, never certify instructional quality."""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import urlparse
from ref_lab.learning_media import SOURCE_CASE_MEDIA

CHAPTERS = ('problem', 'observe', 'principle', 'contrast', 'boundary', 'transfer', 'reflect', 'sources')
ACTIVITIES = {'observation', 'comparison', 'transfer'}

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
        ident = source.get('id')
        if not ident or ident in sources:
            errors.append(f'Duplicate/missing gateway source ID: {ident}')
        sources[ident] = source
        if not public_url(source.get('url')):
            errors.append(f'Unsafe source URL: {ident}')
        for name in ('title', 'author', 'reading_depth', 'checked_at', 'locator', 'support', 'limitation'):
            if not isinstance(source.get(name), str) or not source[name].strip():
                errors.append(f'Missing source {name}: {ident}')
    for gateway in catalog['gateways']:
        ident = gateway.get('id')
        if not isinstance(ident, str) or not ident or ident in seen:
            errors.append(f'Duplicate/missing gateway ID: {ident}')
        seen.add(ident)
        for name in ('title', 'question', 'outcome', 'method', 'author', 'reading_depth', 'prior_knowledge'):
            if not isinstance(gateway.get(name), str) or not gateway[name].strip():
                errors.append(f'Missing gateway {name}: {ident}')
        if not gateway.get('skill_ids') or not set(gateway['skill_ids']) <= skills:
            errors.append(f'Unknown or missing skill mapping: {ident}')
        source_ids = set(gateway.get('source_ids', []))
        if not source_ids or not source_ids <= sources.keys():
            errors.append(f'Unknown source mapping: {ident}')
        cases = {}
        for case in gateway.get('cases', []):
            cid = case.get('id')
            if not cid or cid in cases:
                errors.append(f'Duplicate/missing case: {ident}/{cid}')
            cases[cid] = case
            if not public_url(case.get('url')):
                errors.append(f'Unsafe case URL: {cid}')
            rights, review = case.get('rights', {}), case.get('review', {})
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
                if (not images or case.get('src')
                        or not any(sources.get(s, {}).get('url') == case.get('url') for s in source_ids)):
                    errors.append(f'Invalid local media source: {cid}')
                for image in images:
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
        if [s.get('id') for s in sections] != list(CHAPTERS):
            errors.append(f'Invalid gateway chapters: {ident}')
        exercises, reveals, earlier_cases, transfer_cases = set(), set(), set(), set()
        for section in sections:
            if not section.get('title') or not isinstance(section.get('blocks'), list) or not section['blocks']:
                errors.append(f'Empty teaching section: {ident}/{section.get("id")}')
                continue
            if not set(section.get('source_ids', [])) <= source_ids:
                errors.append(f'Unknown section source: {ident}/{section.get("id")}')
            for block in section['blocks']:
                kind = block.get('type')
                if kind in {'paragraph', 'heading'}:
                    valid = isinstance(block.get('text'), str) and bool(block['text'].strip())
                elif kind == 'list':
                    valid = bool(block.get('items')) and all(isinstance(i, str) and i for i in block['items'])
                elif kind == 'comparison':
                    valid = bool(block.get('rows')) and all(all(r.get(k) for k in ('novice', 'expert', 'question')) for r in block['rows'])
                elif kind == 'tradeoffs':
                    valid = bool(block.get('rows')) and all(all(r.get(k) for k in ('action', 'effect', 'cost', 'test')) for r in block['rows'])
                elif kind in {'case', 'case_pair'}:
                    ids = [block.get('case_id')] if kind == 'case' else block.get('case_ids', [])
                    valid = bool(ids) and set(ids) <= cases.keys()
                    (transfer_cases if section['id'] == 'transfer' else earlier_cases).update(ids)
                elif kind == 'exercise':
                    valid = block.get('id') in ACTIVITIES and block['id'] not in exercises and block.get('title') and block.get('prompt')
                    exercises.add(block.get('id'))
                elif kind == 'reveal':
                    valid = block.get('activity_id') in ACTIVITIES and block.get('title') and block.get('paragraphs')
                    reveals.add(block.get('activity_id'))
                    if not set(block.get('source_ids', [])) <= source_ids:
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
