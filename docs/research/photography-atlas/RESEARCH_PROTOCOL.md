# Research contract

Read USER_BRIEF.txt in this directory. Work in the assigned isolated worktree and only your assigned research files. Do not change UI, shared files, Git branches or publish. The parent integrates your artifact. Use real web searches/opened primary professional sources; source snippets, course marketing or unread videos are discovery leads, not evidence of the detailed teaching. No login bypass, paywall circumvention or image downloads.

## Pass 1

Broad scanning only: save `research/<scope>_sources.json` in your worktree. Root object: `scope`, `queries` (actual queries), `sources` (records below), `gaps`, `excluded`. Aim for diverse primary sources in the assigned field; do not invent a final tree. Use English and useful Chinese/Japanese originals. Report completion to parent and wait for extraction instructions.

Source: `id` (scope prefix + short stable id), `title`, `author`, `identity`, `kind`, `tier` (A/B/C), `language`, `url`, `coverage` (array), `trust_reason`, `independence_key` (original teacher/author/institution, not hosting domain), `access` (full_text/partial/index_only/blocked), `read_depth`, `worth_deep_read` (bool), `notes`, `accessed_at` (YYYY-MM-DD). Course syllabus alone supports breadth, not unseen lesson claims. Keep paraphrase brief; no lengthy quotations or reproduced source material.

## Pass 2 (only after parent confirms broad scan complete)

Save `research/<scope>_candidates.json`: `scope`, `candidates`, `conflicts`, `gaps`. Save any newly read sources in the source file. Candidate fields:

- `id`, `skill_name`, `capability`, `why_it_matters`
- `module_hint`, `domain_hint` (clustering hints only)
- `prerequisites` (local candidate IDs where possible; empty when none established)
- `failure_modes` (array), `practice`, `acceptance` (array of observable checks)
- `evidence` (array of `{source_id, locator, support, scope}`; scope=direct/adapted; a concise paraphrase that actually supports the skill)
- `visual_examples` (array of `{source_id,url,description}`; actual page-linked professional demonstrations, no invented image analysis)
- `relevance` (core/important/advanced/optional), `status` (unassessed), `confidence` (high/medium/low)
- `basis` (professional_consensus/photographer_method/project_adaptation), `practice_basis` (project_designed or source_exercise), `search_terms` (array)

Formal skills require directly supported controllable variables. Cosplay-specific adaptations must state their limits; an unsupported weapon/wig claim belongs in gaps rather than the formal tree. `high` requires at least two genuinely independent professionally credible sources supporting the actual capability, not two domains quoting one author. One source => at most medium. Do not add low-confidence inference-only entries to the formal tree.

Each skill must isolate a trainable variable, visible failure, repeatable minimal experiment and observable acceptance. Project-designed exercises are not claims that the photographer prescribed these counts or thresholds. Keep entries concise and avoid repeated prose. Coverage and distinctness outrank counts. Retain disagreements/conditions instead of averaging them. Distinguish professional consensus, one teacher's method, project exercise design and personal user evidence.

Never claim image visual review unless you actually opened those pixels. Linking a tutorial example is permitted with text-only inspection labeled as such. All personal state begins unassessed; no owner photographs or assessments are invented.
