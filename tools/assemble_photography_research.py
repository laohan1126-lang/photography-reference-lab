"""Apply reviewed placement/lineage decisions to preserved research extractions."""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'docs/research/photography-atlas'


def write(name, value):
    (DIR / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def assemble():
    decisions = json.loads((DIR / 'CLUSTER_DECISIONS.json').read_text(encoding='utf-8'))
    sources, skills, conflicts, gaps = {}, {}, [], []
    for path in sorted((DIR / 'raw').glob('*_sources.json')):
        for source in json.loads(path.read_text(encoding='utf-8'))['sources']:
            sources[source['id']] = copy.deepcopy(source)
    for path in sorted((DIR / 'raw').glob('*_candidates.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        skills.update({s['id']: copy.deepcopy(s) for s in data['candidates']})
        conflicts.extend({'research_scope': data['scope'], 'record': c} for c in data.get('conflicts', []))
        gaps.extend({'research_scope': data['scope'], 'record': g} for g in data.get('gaps', []))
    for sid, patch in decisions.get('source_corrections', {}).items():
        sources[sid].update(patch)
    aliases, by_url, canonical_sources = {}, {}, {}
    for sid, source in sources.items():
        url = source['url']
        if url in by_url:
            aliases[sid] = by_url[url]
        else:
            by_url[url] = sid
            canonical_sources[sid] = source
            source['eligible_for_skills'] = (source.get('access') == 'full_text'
                                            and source.get('tier') in {'A', 'B'}
                                            and source.get('eligible_for_skills', True))
    merges = decisions.get('merges', {})
    for sid, patch in decisions.get('skill_corrections', {}).items():
        skills[sid].update(copy.deepcopy(patch))
    for drop, keep in merges.items():
        old, target = skills[drop], skills[keep]
        for item in old['evidence']:
            if item not in target['evidence']:
                target['evidence'].append(item)
        target.setdefault('merged_candidate_ids', []).append(drop)
        target['search_terms'] = list(dict.fromkeys(target.get('search_terms', []) + old.get('search_terms', []) + [old['skill_name']]))
    rejected, placed, domains, modules = [], {}, [], []
    for domain_def in decisions['domains']:
        domain = {k: v for k, v in domain_def.items() if k != 'modules'}
        domain['module_ids'] = []
        domains.append(domain)
        for module_def in domain_def['modules']:
            module = {'id': module_def['id'], 'name': module_def['name'], 'domain_id': domain['id'], 'skill_ids': []}
            for sid in module_def['skill_ids']:
                if sid in merges:
                    continue
                skill = skills[sid]
                skill.update(decisions.get('skill_corrections', {}).get(sid, {}))
                evidence, discovery = [], []
                for item in skill['evidence']:
                    item = {**item, 'source_id': aliases.get(item['source_id'], item['source_id'])}
                    if canonical_sources[item['source_id']]['eligible_for_skills']:
                        if item not in evidence:
                            evidence.append(item)
                    else:
                        discovery.append(item)
                skill['evidence'], skill['discovery_references'] = evidence, discovery
                authors = {canonical_sources[e['source_id']]['independence_key'] for e in evidence if e['scope'] == 'direct'}
                if not authors or sid in decisions.get('excluded_skills', {}):
                    rejected.append({'id': sid, 'skill_name': skill['skill_name'], 'reason': decisions.get('excluded_skills', {}).get(sid, 'No directly read professional evidence after source-quality gate.')})
                    continue
                if len(authors) < 2:
                    skill['confidence'] = 'medium'
                    if skill['basis'] == 'professional_consensus':
                        skill['basis'] = 'photographer_method'
                if domain['id'] == 'moving-image':
                    skill['relevance'] = 'advanced'
                skill['module_id'] = module['id']
                if isinstance(skill['acceptance'], str):
                    skill['acceptance'] = [skill['acceptance']]
                skill['status'] = 'unassessed'
                examples = skill['visual_examples']
                if isinstance(examples, dict):
                    examples = [examples]
                skill['visual_examples'] = [{**e, 'source_id': aliases.get(e['source_id'], e['source_id']),
                                             'review_state': 'linked_text_only_no_pixel_review'} for e in examples]
                module['skill_ids'].append(sid)
                if sid in placed:
                    raise ValueError('Double placement: ' + sid)
                placed[sid] = skill
            if module['skill_ids']:
                domains[-1]['module_ids'].append(module['id'])
                modules.append(module)
    unplaced = set(skills) - set(placed) - set(merges) - {s['id'] for s in rejected}
    if unplaced:
        raise ValueError('Unplaced candidates: ' + ', '.join(sorted(unplaced)))
    for skill in placed.values():
        deps = [merges.get(d, d) for d in skill['prerequisites']]
        skill['extracted_prerequisites'] = list(skill['prerequisites'])
        skill['workflow_prerequisites'] = [d for d in deps if d not in placed]
        skill['prerequisites'] = list(dict.fromkeys(d for d in deps if d in placed and d != skill['id']))
    conflict_links = decisions.get('conflict_skill_ids', {})
    if set(conflict_links) != {item['record']['topic'] for item in conflicts}:
        raise ValueError('Every conflict needs a reviewed topic-to-skill mapping')
    for item in conflicts:
        item['skill_ids'] = conflict_links[item['record']['topic']]
        if not item['skill_ids'] or any(sid not in placed for sid in item['skill_ids']):
            raise ValueError('Invalid conflict skill mapping: ' + item['record']['topic'])
    write('SOURCE_MAP', {'schema_version': 1, 'sources': list(canonical_sources.values()), 'aliases': aliases,
                         'scope': 'Public text actually opened; paid/unwatched material is discovery only; no source image pixel review.'})
    write('SKILL_TREE', {'schema_version': 1, 'meta': decisions['meta'], 'domains': domains, 'modules': modules, 'skills': list(placed.values())})
    write('EVIDENCE_MATRIX', {'scope': 'Included-source agreement only, not universal professional consensus. Exercises and acceptance are project-designed unless explicitly attributed.',
                              'rows': [{'skill_id': s['id'], 'name': s['skill_name'], 'confidence': s['confidence'], 'basis': s['basis'], 'evidence': s['evidence']} for s in placed.values()]})
    write('CONFLICTS', {'conflicts': conflicts, 'scope': 'Named and conditional differences; not averaged into universal rules.'})
    write('EXTRACTION_DISPOSITIONS', {'merges': merges, 'excluded': rejected})
    print(json.dumps({'domains': len(domains), 'modules': len(modules), 'skills': len(placed), 'sources': len(canonical_sources), 'excluded': len(rejected)}, ensure_ascii=False))


if __name__ == '__main__':
    assemble()
