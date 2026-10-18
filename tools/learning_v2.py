"""Isolated, one-shot evidence/task-ranking experiment. No production writes."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
from pathlib import Path
import secrets
import subprocess
import threading
import time
from urllib.parse import urlsplit

from tools.learning_v1 import (ROOT, FEATURES, PHOTO_KINDS, NONPHOTO_KINDS,
                              canonical_group_hash, digest, load_json, rank_pool, stamp)
from tools.learning_v1_human import atomic_write, json_bytes, CHOICES, AESTHETIC_SCORE

EXPERIMENT = ROOT / '.local/learning-v2'
METHODS = ('original', 'existing_rule', 'task_rank')
STATES = {'CONFIRMED': 0, 'NEEDS_EVIDENCE': 1, 'MISMATCH': 2}


def save(path: Path, value: object, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        with path.open('xb') as stream:
            stream.write(json_bytes(value))
    else:
        atomic_write(path, json_bytes(value))


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context_sha(task: dict) -> str:
    return digest(task['context'])


def evidence_state(record: dict, review: dict, task: dict, human: dict | None = None) -> dict:
    """One boundary: byte/context/source binding, component evidence and conflict."""
    sha = record['asset_sha']
    result = {'ai_state': 'NEEDS_EVIDENCE', 'state': 'NEEDS_EVIDENCE',
              'identity_source': 'none', 'human_identity': None, 'reasons': []}
    valid = (review.get('asset_sha') == sha == review.get('opened_sha')
             and review.get('context_sha') == context_sha(task)
             and review.get('actor') == 'ai' and bool(review.get('producer'))
             and Path(record['original_path']).is_file()
             and file_sha(Path(record['original_path'])) == sha)
    if not valid:
        result['reasons'] = ['missing_or_stale_byte_context_or_model_binding']
        return result
    ev = review.get('evidence') or {}
    known = {k: bool(isinstance(ev.get(k), list) and ev[k]
                     and all(isinstance(x, str) and x.strip() for x in ev[k]))
             for k in ('kind', 'identity', 'costume')}
    kind, identity, costume = (review.get(k, 'unknown') for k in ('kind', 'identity', 'costume'))
    if ((kind in NONPHOTO_KINDS and known['kind']) or
            (identity == 'mismatch' and known['identity']) or
            (costume == 'mismatch' and known['costume'])):
        result.update(ai_state='MISMATCH', state='MISMATCH', reasons=['observed_mismatch'])
    elif (kind in PHOTO_KINDS and known['kind'] and identity == 'match' and known['identity']
          and ((not task['context']['costume'] and costume == 'not_required')
               or (costume == 'match' and known['costume']))):
        result.update(ai_state='CONFIRMED', state='CONFIRMED', identity_source='ai', reasons=[])
    else:
        result['reasons'] = [k for k in ('kind', 'identity', 'costume')
                             if not known[k] or review.get(k) in ('unknown', 'uncertain', None)]
    # Human evidence can resolve identity only; it cannot erase a nonphoto observation.
    if (human and human.get('asset_sha') == sha and human.get('context_sha') == context_sha(task)
            and human.get('source_snapshot_sha') and human.get('actor') == 'human'):
        label = human.get('identity')
        result['human_identity'] = label
        if ((identity == 'mismatch' and label == 'match') or
                (identity == 'match' and label == 'mismatch')):
            result.update(state='NEEDS_EVIDENCE', reasons=['model_human_identity_conflict'])
        elif label == 'mismatch':
            result.update(state='MISMATCH', identity_source='human', reasons=['human_identity_mismatch'])
        elif (label == 'match' and identity in ('unknown', 'uncertain')
              and kind in PHOTO_KINDS and known['kind']
              and ((not task['context']['costume'] and costume == 'not_required')
                   or (costume == 'match' and known['costume']))):
            result.update(state='CONFIRMED', identity_source='human', reasons=[])
    return result


def task_rank(pool: list[dict], reviews: dict, task: dict, humans: dict | None = None) -> list[dict]:
    if len({r['asset_sha'] for r in pool}) != len(pool):
        raise ValueError('Pool must be SHA unique')
    ranked = []
    for i, r in enumerate(pool):
        v = reviews.get(r['asset_sha'], {})
        state = evidence_state(r, v, task, (humans or {}).get(r['asset_sha']))
        features = v.get('features') or {}
        known = sum(features.get(k) not in (None, '', 'unknown') for k in FEATURES)
        matched = [k for k, values in task['criteria'].items() if features.get(k) in values]
        enough = state['state'] == 'CONFIRMED' and known >= task['min_known_features']
        ranked.append({**r, 'decision': state, 'original_rank': i+1,
                       'matched_task_features': matched if enough else [],
                       'task_points': len(matched) if enough else None,
                       'feature_count': known if enough else 0,
                       'ranking_status': 'TASK_RELEVANCE' if enough else 'INSUFFICIENT_EVIDENCE'})
    # Unknowns stay visible after confirmed items; no item is removed from the pool.
    return sorted(ranked, key=lambda r: (STATES[r['decision']['state']],
                                        -(r['task_points'] if r['task_points'] is not None else -1),
                                        r['original_rank']))


def freeze(folder: Path) -> dict:
    task = load_json(folder / 'task.json')
    if len(task['query_plan']['queries']) > 8:
        raise ValueError('Query budget')
    files = ['tools/learning_v2.py', 'tools/learning_v2_review.html', 'tests/test_learning_v2.py',
             'tools/learning_v1.py', 'tools/learning_v1_human.py', 'tools/collect_adapter.py']
    hashes = {str(ROOT / f): file_sha(ROOT / f) for f in files}
    hashes[str(folder / 'task.json')] = file_sha(folder / 'task.json')
    for f in task.get('reference_files', []):
        hashes[str(ROOT / f)] = file_sha(ROOT / f)
    for f in task.get('history_files', []):
        hashes[str(ROOT / f)] = file_sha(ROOT / f)
    manifest = {'at': stamp(), 'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                cwd=ROOT, text=True).strip(), 'files': hashes, 'task': task,
                'version_sha': digest(hashes), 'metrics': ['coverage', 'false_accept', 'false_reject',
                'abstention', 'wrong_character_or_costume_top5', 'useful_top5', 'like_top5',
                'ndcg5_global_idcg', 'source_traceability', 'tool_calls', 'elapsed_seconds'],
                'gain_rule': 'at least +1 useful in top5; aesthetic declines reported separately',
                'evaluation_limit': 1, 'candidate2_enabled': False}
    save(folder / 'freeze.json', manifest, exclusive=True)
    return manifest


def check_freeze(folder: Path) -> dict:
    manifest = load_json(folder / 'freeze.json')
    for name, expected in manifest['files'].items():
        if not Path(name).is_file() or file_sha(Path(name)) != expected:
            raise ValueError(f'Frozen input changed: {name}')
    return manifest


def search(folder: Path, bsk: str, browser: str) -> dict:
    from tools.collect_adapter import build_policy, fetch_bsk_candidates
    frozen = check_freeze(folder)
    task = frozen['task']
    save(folder / 'search-started.json', {'at': stamp(), 'version_sha': frozen['version_sha']}, exclusive=True)
    started = time.monotonic()
    calls = Counter()
    original_run = subprocess.run
    def counted_run(argv, *args, **kwargs):
        if argv and str(argv[0]) == bsk:
            calls[str(argv[1])] += 1
        return original_run(argv, *args, **kwargs)
    subprocess.run = counted_run
    try:
        candidates, images, log, blocked = fetch_bsk_candidates(bsk, browser, task, 12, build_policy(task))
    finally:
        subprocess.run = original_run
    for name, data in images.items():
        path = folder / 'received' / 'images' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    for r in candidates:
        r['original_path'] = str((folder / 'received' / r['file']).resolve())
        r['asset_sha'] = file_sha(Path(r['original_path']))
        r['dhash'] = canonical_group_hash(Path(r['original_path']))
    manifest = {'at': stamp(), 'candidates': candidates, 'query_log': log,
                'query_count': len(log), 'elapsed_seconds': time.monotonic()-started,
                'blocked': blocked, 'version_sha': frozen['version_sha'],
                'bsk_calls_by_command': dict(calls), 'bsk_call_count': sum(calls.values())}
    save(folder / 'received.json', manifest, exclusive=True)
    return {k:v for k,v in manifest.items() if k != 'candidates'}


def evaluate(folder: Path) -> dict:
    frozen = check_freeze(folder)
    received = load_json(folder / 'received.json')
    pool = received['candidates']
    raw_reviews = load_json(folder / 'model-reviews.json')
    if len(raw_reviews) > 20 or len(pool) > 20:
        raise ValueError('Image budget')
    reviews = {r['asset_sha']: r for r in raw_reviews}
    if len(reviews) != len(raw_reviews) or set(reviews) != {r['asset_sha'] for r in pool}:
        raise ValueError('Each received SHA needs exactly one review (unknown is allowed)')
    history = []
    for name in frozen['task'].get('history_files', []):
        rows = load_json(ROOT/name)
        history.extend(rows if isinstance(rows, list) else rows.get('candidates', []))
    overlap = []
    for r in pool:
        if any(r['asset_sha'] == h.get('asset_sha') or
               (len(r.get('dhash', '')) == len(h.get('dhash', '')) == 16
                and (int(r['dhash'],16)^int(h['dhash'],16)).bit_count() <= 5) for h in history):
            overlap.append(r['asset_sha'])
    old = []
    for r in pool:
        v = reviews[r['asset_sha']]
        old.append({**r, 'visual': {**v, 'observed': v.get('opened_sha') == r['asset_sha'],
                                    'evidence': [x for a in v.get('evidence', {}).values() for x in a]}})
    ranked = task_rank(pool, reviews, frozen['task'])
    original = [r['asset_sha'] for r in pool]
    rankings = {'original': original,
                'existing_rule': [r['asset_sha'] for r in rank_pool(old, 'baseline1')],
                'task_rank': [r['asset_sha'] for r in ranked]}
    # All methods are compared over the SAME <=12 SHA set. No cherry-picking by ranking.
    if len(pool) > 12:
        raise ValueError('More than 12 candidates: stop, do not select a favorable evaluation subset')
    if overlap:
        status = 'STOP_HISTORY_OVERLAP_NOT_PROVEN'
    elif not any(r['decision']['ai_state'] == 'CONFIRMED' for r in ranked):
        status = 'STOP_NO_VISUAL_DISCRIMINATION'
    else:
        status = 'WAITING_FOR_HUMAN'
    manifest = {'at': stamp(), 'status': status, 'rankings': rankings, 'rows': ranked,
                'review_order': sorted(original), 'pool_sha': digest(pool), 'reviews_sha': digest(raw_reviews),
                'version_sha': frozen['version_sha'], 'task': frozen['task'],
                'search': {k:v for k,v in received.items() if k != 'candidates'},
                'ai_counts': dict(Counter(r['decision']['ai_state'] for r in ranked)),
                'execution': load_json(folder/'execution.json') if (folder/'execution.json').exists() else {},
                'independence': {'historical_sha_or_near_overlap': overlap,
                                 'different_photographers_or_shoots': 'UNVERIFIED'},
                'source_traceability': {'page_url_count': sum(bool(r.get('source', {}).get('page_url')) for r in pool),
                                        'verified_original_author_count': 0, 'denominator': len(pool)}}
    save(folder / 'evaluation.json', manifest, exclusive=True)
    return manifest


def ndcg(ranking: list[str], scores: dict) -> float | None:
    # IDCG uses the complete fixed pool, not each method's own top-five relevance.
    if len(ranking) < 5 or any(scores.get(s) is None for s in ranking):
        return None
    def dcg(values):
        return sum((2**v-1) / math.log2(i+2) for i,v in enumerate(values))
    ideal = dcg(sorted(scores[s] for s in ranking)[-5:][::-1])
    return dcg([scores[s] for s in ranking[:5]]) / ideal if ideal else 0.0


def metrics(evaluation: dict, labels: dict) -> dict:
    shas = evaluation['review_order']
    def value(s, dim):
        return labels.get(s, {}).get(dim)
    scores = {s: AESTHETIC_SCORE.get(value(s, 'aesthetic')) for s in shas}
    output = {}
    for method, ranking in evaluation['rankings'].items():
        top = ranking[:5]
        def count(dim, positives):
            values = [value(s, dim) for s in top]
            known = [v for v in values if v is not None and v != 'uncertain']
            return {'count': sum(v in positives for v in known) if len(known) == 5 else None,
                    'rated': len(known), 'denominator': 5}
        output[method] = {'useful_top5': count('photography', {'useful'}),
                          'like_top5': count('aesthetic', {'like'}),
                          'wrong_character_or_costume_top5': count('identity', {'not_target'}),
                          'ndcg5': ndcg(ranking, scores)}
    rows = evaluation['rows']
    counts = Counter(r['decision']['ai_state'] for r in rows)
    pairs = [(r['decision']['ai_state'], value(r['asset_sha'], 'identity')) for r in rows
             if value(r['asset_sha'], 'identity') in ('target_cosplay', 'not_target')]
    false_accept = sum(p == 'CONFIRMED' and y == 'not_target' for p,y in pairs)
    false_reject = sum(p == 'MISMATCH' and y == 'target_cosplay' for p,y in pairs)
    coverage = {'counts': dict(counts), 'decided': counts['CONFIRMED']+counts['MISMATCH'],
                'denominator': len(rows), 'needs_evidence': counts['NEEDS_EVIDENCE'],
                'coverage_rate': (counts['CONFIRMED']+counts['MISMATCH'])/len(rows) if rows else None,
                'needs_evidence_rate': counts['NEEDS_EVIDENCE']/len(rows) if rows else None,
                'false_accept': false_accept if pairs else None, 'false_reject': false_reject if pairs else None,
                'human_known_denominator': len(pairs),
                'false_accept_rate': false_accept/sum(y=='not_target' for _,y in pairs) if any(y=='not_target' for _,y in pairs) else None,
                'false_reject_rate': false_reject/sum(y=='target_cosplay' for _,y in pairs) if any(y=='target_cosplay' for _,y in pairs) else None,
                'note': 'Combined target-role/version/real-photo truth; no separate modality accuracy claim.'}
    complete = len(shas) >= 5 and all(value(s, d) in CHOICES[d] and value(s,d) != 'uncertain'
                                    for s in shas for d in CHOICES)
    complete = complete and evaluation.get('status') == 'WAITING_FOR_HUMAN'
    outcome = 'NOT_PROVEN'
    if complete:
        if all(evaluation['rankings'][m] == evaluation['rankings']['task_rank'] for m in METHODS):
            outcome = 'NO_MEANINGFUL_GAIN'
        else:
            candidate = output['task_rank']
            gain = all(candidate['useful_top5']['count'] > output[m]['useful_top5']['count']
                       for m in ('original', 'existing_rule'))
            aesthetic_drop = any(candidate['ndcg5'] < output[m]['ndcg5']
                                 or candidate['like_top5']['count'] < output[m]['like_top5']['count']
                                 for m in ('original', 'existing_rule'))
            outcome = ('PHOTOGRAPHY_GAIN_AESTHETIC_DECLINE' if aesthetic_drop else 'FIXED_POOL_PHOTOGRAPHY_GAIN') if gain else 'NO_MEANINGFUL_GAIN'
    return {'at': stamp(), 'outcome': outcome, 'methods': output, 'verification': coverage,
            'source_traceability': evaluation['source_traceability'], 'search': evaluation['search'],
            'execution': evaluation.get('execution', {}),
            'labels_complete': complete, 'scope': 'One fixed pool; not retrieval gain or aesthetic generalization',
            'human_screening_cost_saved': None, 'cost_note': 'No timed human baseline; review burden reduction NOT_PROVEN'}


class ReviewStore:
    def __init__(self, folder: Path):
        check_freeze(folder)
        self.folder = folder
        self.evaluation = load_json(folder / 'evaluation.json')
        self.binding = file_sha(folder / 'evaluation.json')
        self.lock = threading.RLock()

    def state(self):
        check_freeze(self.folder)
        if file_sha(self.folder / 'evaluation.json') != self.binding:
            raise ValueError('Evaluation drift')
        for name, key in [('model-reviews.json', 'reviews_sha')]:
            if digest(load_json(self.folder/name)) != self.evaluation[key]:
                raise ValueError('Model evidence drift')
        if digest(load_json(self.folder/'received.json')['candidates']) != self.evaluation['pool_sha']:
            raise ValueError('Candidate drift')
        p = self.folder / 'labels-final.json'
        if not p.exists():
            p = self.folder / 'labels.json'
        data = load_json(p) if p.exists() else {'binding': self.binding, 'labels': {}, 'submitted': False}
        if data.get('binding') != self.binding:
            raise ValueError('Human label binding drift')
        return data

    def draft(self, payload):
        if not isinstance(payload, dict) or payload.get('asset_sha') not in self.evaluation['review_order']:
            raise ValueError('Unknown SHA')
        labels = payload.get('labels')
        if not isinstance(labels, dict) or any(k not in CHOICES or v not in CHOICES[k] for k,v in labels.items()):
            raise ValueError('Invalid label')
        with self.lock:
            data = self.state()
            if data['submitted']:
                raise ValueError('Already submitted')
            if labels:
                data['labels'].setdefault(payload['asset_sha'], {}).update(labels)
                save(self.folder/'labels.json', data)
            return data

    def submit(self):
        with self.lock:
            data = self.state()
            if data['submitted'] or (self.folder/'labels-final.json').exists():
                raise ValueError('Already submitted')
            if any(set(data['labels'].get(s, {})) != set(CHOICES) for s in self.evaluation['review_order']):
                raise ValueError('请逐张评价三个维度；无法判断可以选“无法确定”')
            data.update(submitted=True, submitted_at=stamp(), actor='human')
            atomic_write(self.folder/'labels-final.json', json_bytes(data), read_only=True)
            return self.report()

    def report(self):
        with self.lock:
            data = self.state()
            result = metrics(self.evaluation, data['labels'])
            result['label_status'] = 'SUBMITTED' if data['submitted'] else 'PENDING_HUMAN'
            save(self.folder/'metrics.json', result)
            return result


def create_server(folder: Path, port: int = 0):
    store = ReviewStore(folder)
    images = {}
    for r in store.evaluation['rows']:
        data = Path(r['original_path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != r['asset_sha']:
            raise ValueError('Image bytes drift')
        images[r['asset_sha']] = (data, mimetypes.guess_type(r['original_path'])[0] or 'application/octet-stream')
    token = secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send(self, status, data, content_type='application/json; charset=utf-8'):
            if not isinstance(data, bytes):
                data = json_bytes(data)
            self.send_response(status)
            for k,v in {'Content-Type': content_type, 'Content-Length': str(len(data)),
                        'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
                        'X-Content-Type-Options': 'nosniff'}.items():
                self.send_header(k,v)
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/':
                page = (ROOT/'tools/learning_v2_review.html').read_text('utf8').replace('__TOKEN__', token)
                self.send(200, page.encode(), 'text/html; charset=utf-8')
            elif path == '/api/health':
                self.send(200, {'ok':True, 'experiment':'learning-v2'})
            elif path.startswith('/image/') and path[7:] in images:
                data, mime = images[path[7:]]
                self.send(200, data, mime)
            elif path in ('/api/state', '/api/report') and hmac.compare_digest(self.headers.get('X-Review-Token',''), token):
                try:
                    if path == '/api/report':
                        self.send(200, store.report())
                    else:
                        public = [{'asset_sha':s, 'source':next(r.get('source',{}) for r in store.evaluation['rows'] if r['asset_sha']==s)} for s in store.evaluation['review_order']]
                        self.send(200, {**store.state(), 'assets':public, 'choices':CHOICES,
                                        'title':store.evaluation['task']['label']})
                except ValueError as exc:
                    self.send(409, {'error':str(exc)})
            else:
                self.send(404, {'error':'Not found'})
        def do_POST(self):
            path = urlsplit(self.path).path
            if not hmac.compare_digest(self.headers.get('X-Review-Token',''), token):
                self.send(403, {'error':'Invalid token'}); return
            if path not in ('/api/draft', '/api/submit'):
                self.send(404, {'error':'Not found'}); return
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length < 10000 or self.headers.get('Content-Type') != 'application/json':
                    raise ValueError('Invalid request size/type')
                data = json.loads(self.rfile.read(length))
                self.send(200, store.draft(data) if path == '/api/draft' else store.submit())
            except (ValueError, TypeError) as exc:
                self.send(409, {'error':str(exc)})
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.store = store
    return server


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['freeze','check-freeze','search','evaluate','serve','report'])
    ap.add_argument('--experiment', type=Path, default=EXPERIMENT)
    ap.add_argument('--bsk', default=str(Path.home()/'.local/bin/bsk.exe'))
    ap.add_argument('--browser', default='')
    ap.add_argument('--port', type=int, default=0)
    args = ap.parse_args()
    folder = args.experiment.resolve()
    if not folder.is_relative_to(ROOT/'.local'):
        raise ValueError('Experiment must stay inside repository .local')
    if args.action == 'serve':
        server = create_server(folder, args.port)
        url = f'http://127.0.0.1:{server.server_port}/'
        save(folder/'service.json', {'url':url, 'at':stamp()})
        print('REVIEW_URL', url, flush=True)
        server.serve_forever()
        return
    if args.action == 'freeze': result = freeze(folder)
    elif args.action == 'check-freeze': result = check_freeze(folder)
    elif args.action == 'search': result = search(folder, args.bsk, args.browser)
    elif args.action == 'evaluate': result = evaluate(folder)
    else: result = ReviewStore(folder).report()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
