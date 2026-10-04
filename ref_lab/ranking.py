"""Evidence-labelled candidate explanations. Metadata never becomes image evidence.

Keep arrival order until comparable visual features and confirmed personal preferences
exist. Numeric preference/usefulness/exploration scores would imply knowledge we lack.
"""
from __future__ import annotations
from typing import Any
from .policy import review_is_current, preflight_is_current


def evaluate_photographic_points(quality_data: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    """Describe only file dimensions; aspect ratio cannot establish subject or pose."""
    asset = metadata.get('asset') or {}
    if asset.get('id') != metadata.get('asset_sha'):
        return []
    w, h = asset.get('width', 0), asset.get('height', 0)
    if not w or not h:
        return []
    shape = '竖画幅' if h > w * 1.2 else '横画幅' if w > h * 1.2 else '近方画幅'
    return [f'文件测量：{w}×{h} · {shape}']


def score_and_rank_candidates(candidates: list[dict[str, Any]], profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    results = []
    for cand in candidates:
        sha = cand.get('asset_sha')
        review = cand.get('review') or {}
        current_review = review_is_current(cand)
        actor = cand.get('review_actor', 'unknown')
        pf = cand.get('preflight') or {}
        current_pf = preflight_is_current(cand)
        source = cand.get('source') or {}
        evidence = {
            'asset_sha': sha,
            'file_measurements': evaluate_photographic_points({}, cand),
            'discovery_context': {'title': cand.get('title', ''), 'search_query': source.get('search_query', ''),
                                  'source_title': source.get('title', ''), 'origin': 'discovery_metadata',
                                  'learning_eligible': False},
            'visual_observations': {'origin': 'unreviewed' if not current_review else 'human_visual_review' if actor == 'human' else 'ai_visual_inference' if actor == 'ai' else 'unknown_producer',
                                    'producer': cand.get('review_producer', ''),
                                    'items': review.get('observations', []) if current_review else [],
                                    'current_asset': current_review},
            'preflight': {'origin': 'unreviewed' if not current_pf else 'deterministic_file_check' if pf.get('producer') == 'deterministic_preflight' else 'agent_prediction',
                          'producer': pf.get('producer', ''),
                          'items': pf.get('visual_evidence', []) if current_pf else [],
                          'current_asset': current_pf},
            'shooting_plan': {'origin': 'shooting_plan_inference', 'producer': cand.get('card_producer', ''),
                              'interpretation': ((cand.get('card') or {}).get('lighting') or {}).get('interpretation', '') if current_review else '',
                              'current_context': bool(current_review and cand.get('card_current_context')), 'photographic_fact': False},
            'human_feedback': {'origin': cand.get('decision_origin', 'legacy_unverified'), 'decision': cand.get('decision'),
                               'preference_origin': cand.get('preference_origin', 'legacy_unverified'),
                               'borrow_origin': cand.get('borrow_origin', 'legacy_unverified'),
                               'rejection_origin': cand.get('rejection_feedback_origin', 'legacy_unverified'),
                               'project_id': cand.get('project_id'), 'preference': cand.get('preference', ''),
                               'borrow': cand.get('borrow', []),
                               'is_aesthetic_negative': cand.get('is_aesthetic_negative', False),
                               'rejection_reason': cand.get('rejection_reason', ''),
                               'photographic_fact': False,
                               'learning_eligibility': {'project_use': cand.get('decision_origin') == 'human_curation' and cand.get('decision') == 'keep',
                                                       'taste_interest': cand.get('decision_origin') == 'human_inspiration_archive',
                                                       'aesthetic_negative': cand.get('aesthetic_negative_origin') == 'human_curation' and bool(cand.get('is_aesthetic_negative'))}},
        }
        explanation = {'identity_status': '身份未核验', 'recommendation_reason': '按入库顺序浏览；尚无可靠个性化排序',
                       'photographic_points': evidence['file_measurements'], 'preference_points': [],
                       'is_exploration': False, 'exploration_reason': '', 'is_near_duplicate': False,
                       'total_score': None, 'relevance_score': None, 'usefulness_score': None,
                       'preference_score': None, 'exploration_score': None,
                       'scores': dict.fromkeys(('relevance','usefulness','preference','exploration','composite')),
                       'evidence': evidence, 'unknowns': ['光线、机位、动作不会由标题或搜索词推导', '长期偏好匹配尚未核验']}
        if current_review and actor in {'human', 'ai'}:
            label = '人工图像判断' if actor == 'human' else 'AI 图像推断，待人工核对'
            explanation['identity_status'] = f"{label}：{review.get('character_match', 'unknown')}"
        results.append({**cand, 'recommendation': explanation, 'ranking_explanation': explanation, 'ranking_score': None})
    return results
