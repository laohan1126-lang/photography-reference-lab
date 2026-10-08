"""Validate teaching provenance/relationships, never certify instructional quality."""
from __future__ import annotations

from urllib.parse import urlparse
from ref_lab.learning_media import SOURCE_CASE_MEDIA

CHAPTERS = ('problem', 'observe', 'principle', 'contrast', 'boundary', 'transfer', 'reflect', 'sources')
ACTIVITIES = {'observation', 'comparison', 'transfer'}


def public_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlparse(value)
        return (url.scheme == 'https' and bool(url.hostname) and not url.username and not url.password
                and url.hostname not in {'localhost', '127.0.0.1', '::1'} and '\\' not in value)
    except ValueError:
        return False


def validate_gateways(catalog: dict, tree: dict) -> list[str]:
    errors = []
    if not isinstance(catalog, dict) or catalog.get('schema_version') != 1:
        return ['Invalid gateway schema']
    if not isinstance(catalog.get('gateways'), list) or not isinstance(catalog.get('sources'), list):
        return ['Gateway catalogue requires gateways and sources lists']
    skills = {s['id'] for s in tree['skills']}
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
                registered = SOURCE_CASE_MEDIA.get(cid)
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
            elif case.get('display') != 'external_only' or case.get('src') or case.get('images'):
                errors.append(f'Invalid case display/rights: {cid}')
            for name in ('author', 'title', 'caption', 'alt'):
                if not case.get(name):
                    errors.append(f'Missing case {name}: {cid}')
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
