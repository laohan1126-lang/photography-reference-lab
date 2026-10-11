'use strict';
// Teaching owns its drafts and reading position; the atlas owns routes and writes.
window.LearningGateways = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {unassessed:'尚未自评', unseen:'尚未接触', terms:'了解术语', principles:'理解基本原理', analysis:'能够分析案例', transfer:'能独立迁移到新场景', field:'已经过实际拍摄验证'};
  const notes = {unassessed:'阅读与展开解析不会替你升级。', unseen:'这是你的自评，可以直接跳到有挑战的部分。', terms:'能认出概念名称，还不等于能解释照片。', principles:'能解释变量关系；下一步用具体画面检验。', analysis:'能指出图中证据，也能说清尚不能确定的条件。', transfer:'由你确认能在未讲过的场景中独立判断。', field:'由你确认已经拍摄、比较并验证；可在关联技能中附实拍记录。'};
  const drafts = new Map();
  // Rebuilding a reader must not turn settled photos back into zero-height lazy
  // placeholders. Keep the observed presentation for this page, by exact media URL;
  // a fresh page retries failures, and a newly loaded image updates its real dimensions.
  const mediaPresentation = new Map();
  // Optional bounded label per course entry, so a full chapter is not called a sample.
  const courseLabel = gateway => typeof gateway?.label === 'string' && gateway.label.trim() ? gateway.label.trim() : 'PHOTO ATLAS · 课程样板';
  let catalog = [], sources = new Map(), noteMedia = new Map(), host, dialog, scroll, current = null, origin = null, busy = false;
  const key = id => `photography-gateway-draft-v2:${id}`;
  const safeURL = value => { try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password ? u.href : ''; } catch { return ''; } };
  const record = id => host.record(id) || {};
  // Reading position and revealed folds belong to one revision of the course text. A
  // field-guide rewrite changes both, so a stale scroll offset or reveal no longer means
  // anything; the private server record and the typed answers are not affected.
  function contentVersion(gateway) {
    if (!isFieldGuide(gateway)) return '';
    const text = JSON.stringify([gateway.content_version, gateway.sections, gateway.cases]);
    let hash = 2166136261;
    for (let i = 0; i < text.length; i++) hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
    return `${FIELD_GUIDE}:${(hash >>> 0).toString(16)}`;
  }
  function getDraft(id) {
    if (drafts.has(id)) return drafts.get(id);
    let saved;
    try { saved = JSON.parse(sessionStorage.getItem(key(id)) || 'null'); } catch {}
    const server = record(id);
    const value = saved && saved.answers && typeof saved.answers === 'object' && Number.isInteger(saved.revision)
      ? saved : {stage:server.stage || 'unassessed', answers:{...(server.answers || {})}, revealed:[...(server.revealed || [])], last_section:server.last_section || 'problem', revision:host.revision(), serverSnapshot:JSON.stringify(server), scroll:0, dirty:false};
    if (!Array.isArray(value.revealed)) value.revealed = [];
    if (!(value.stage in labels)) value.stage = 'unassessed';
    const gateway = catalog.find(item => item.id === id);
    const version = contentVersion(gateway);
    if (version && value.version !== version) {
      value.scroll = 0;
      value.revealed = [];
      value.last_section = (gateway.sections || [])[0]?.id || 'problem';
      value.dirty = !!Object.keys(value.answers || {}).length;
    }
    if (version) value.version = version;
    drafts.set(id, value);
    return value;
  }
  function remember() {
    if (!current) return;
    const draft = getDraft(current.id);
    draft.scroll = scroll.scrollTop;
    try { sessionStorage.setItem(key(current.id), JSON.stringify(draft)); } catch { /* In-memory draft still survives closing the reader. */ }
  }
  function notice(text, error=false) {
    const node = document.getElementById('gateway-message');
    if (node) { node.textContent = text; node.dataset.error = String(error); }
  }
  const evidenceText = value => typeof value === 'string' && value.trim() ? value : '';
  const evidenceDate = value => {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return '';
    // A date shape is not a date: 2026-13-40 has to fail the same way 2026-13 does.
    const [year, month, day] = value.split('-').map(Number);
    const stamp = new Date(0);
    stamp.setUTCFullYear(year, month - 1, day);
    return stamp.getUTCFullYear() === year && stamp.getUTCMonth() === month - 1 && stamp.getUTCDate() === day ? value : '';
  };
  const evidenceRow = (layer, label, body, state) => `<div class="case-evidence-row" data-evidence-layer="${esc(layer)}" data-evidence-state="${esc(state)}"><dt class="case-evidence-label">${esc(label)}</dt><dd>${body}</dd></div>`;
  const evidenceMissing = text => `<p class="case-evidence-missing">${esc(text)}</p>`;
  const EVIDENCE_LAYER_LABEL = {observation:'画面观察', quote:'作者原话', explanation:'专业解释', advice:'项目建议'};
  // The one format boundary the reader trusts. The extension reader and the base bundle
  // reader both refuse an unrecognised course_format before anything is rendered.
  const FIELD_GUIDE = 'field-guide-v1';
  const isFieldGuide = gateway => !!gateway && gateway.course_format === FIELD_GUIDE;
  // A reading order over one original video. It links out to precise points on the source
  // page and never embeds, proxies or downloads the video: this page plays nothing, so
  // research inspection is retained separately from the learner's navigation.
  const clock = value => { const total = Math.floor(Number(value) || 0); return `${String(Math.floor(total / 60)).padStart(2,'0')}:${String(total % 60).padStart(2,'0')}`; };
  const timedURL = (url, seconds) => {
    const base = safeURL(url);
    if (!base || !Number.isFinite(Number(seconds))) return base;
    try { const parsed = new URL(base); parsed.searchParams.set('t', `${Math.floor(Number(seconds))}s`); return parsed.href; }
    catch { return base; }
  };
  const BASIS_LABEL = {visible_marker:'画面里能直接看见的停止点', source_measured:'来源实测的停止点', practice_start:'建议练习起点（不是作者实测）'};
  const RELATION_LABEL = {same_session:'同一次拍摄内', illustrative:'姿态与拍法参照'};
  function recipeTargetHTML(target) {
    const label = BASIS_LABEL[target.basis] || '';
    const basis = `<p class="field-basis" data-basis="${esc(target.basis)}">${esc(label)}</p>`;
    if (target.basis === 'source_measured') {
      const source = sources.get(target.source_id);
      const link = source && safeURL(source.url)
        ? `<a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.short_title || source.title || target.source_id)} ↗</a> · ` : '';
      return `${basis}<p>${esc(target.text)}</p><p class="gateway-small">原文定位：${esc(target.locator)}${link ? ' · 出处：' + link : ''}</p><ul class="field-conditions">${(target.conditions||[]).map(text=>`<li>${esc(text)}</li>`).join('')}</ul>`;
    }
    if (target.basis === 'practice_start') return `${basis}<p>${esc(target.text)}</p><p class="gateway-small">这是本课程提出的练习起点，不是作者实测的数值；拍出来以后以你自己的照片为准。</p>`;
    return `${basis}<p>${esc(target.text)}</p>`;
  }
  function recipeHTML(block, gateway) {
    const comparison = block.comparison;
    return `<article class="field-recipe" data-recipe="${esc(block.id)}"><h3>${esc(block.instruction)}</h3><dl class="field-recipe-meta"><dt>要解决的问题</dt><dd>${esc(block.problem)}</dd><dt>先准备什么</dt><dd>${esc(block.setup)}</dd></dl><div class="field-stop"><p class="field-label">做到这里就停</p>${recipeTargetHTML(block.target)}</div><div class="field-compare"><p class="field-label">实际对照照片 · ${esc(RELATION_LABEL[comparison.relation] || comparison.relation)}</p><p class="gateway-small">${esc((comparison.conditions||[]).join('；'))}</p><div class="gateway-case-pair">${(comparison.case_ids||[]).map(id=>caseHTML(gateway,id)).join('')}</div><p class="field-look"><span class="field-label">看什么</span>${esc(comparison.look_for)}</p></div><div class="field-check"><p class="field-label">怎么算做到</p><p>${esc(block.check.success)}</p><p class="field-failed"><span class="field-label">没做到怎么办</span>${esc(block.check.if_failed)}</p></div><p class="field-cost"><span class="field-label">代价</span>${esc(block.cost)}</p><p class="field-why">${esc(block.why)}</p>${block.source_ids?.length?`<p class="gateway-citation">本条依据：${citations(block.source_ids)}</p>`:''}</article>`;
  }
  function videoHTML(block) {
    const source = sources.get(block.source_id);
    const url = source ? safeURL(source.url) : '';
    const inspection = block.inspection || {};
    const steps = (block.steps || []).map(step => {
      const href = timedURL(url, step.start_seconds);
      const range = `${clock(step.start_seconds)}–${clock(step.end_seconds)}`;
      return `<li class="video-step" data-stage="${esc(step.stage)}">${href?`<a class="video-time" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(range)} ↗</a>`:`<span class="video-time">${esc(range)}</span>`}<strong>${esc(step.stage)}</strong><span>${esc(step.summary)}</span></li>`;
    }).join('');
    const heading = url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(source.short_title || source.title || block.source_id)} ↗</a>` : esc(block.source_id);
    return `<section class="field-video" data-video="${esc(block.id)}"><h3>${heading} · ${esc(clock(block.start_seconds))}–${esc(clock(block.end_seconds))}</h3><p class="gateway-small">按时间点回看老师的动作，再用停点检查自己的下一张。</p><ol class="video-steps">${steps}</ol><details class="video-inspection"><summary>片段核对范围</summary><p>${esc(inspection.detail || '')} · 核对于 ${esc(inspection.checked_at || '')}</p></details></section>`;
  }
  // Only this gateway's own source, on this case's own readable page, quoting words that
  // exist, with locator/language/date, may present the author's wording as checked.
  // Two unsafe URLs that both fail the same way are not a match; anything else stays unverified.
  function checkedQuoteSource(item, gateway, quote, sourceMap) {
    if (!quote || quote.verification !== 'verbatim_checked') return null;
    if (!evidenceText(quote.text)) return null;
    const sourceId = evidenceText(quote.source_id);
    const source = sourceMap.get(sourceId);
    if (!source || !(gateway.source_ids || []).includes(sourceId)) return null;
    const caseURL = safeURL(item && item.url), sourceURL = safeURL(source.url);
    if (!caseURL || !sourceURL || caseURL !== sourceURL) return null;
    if (!evidenceText(quote.locator) || !evidenceText(quote.language) || !evidenceDate(quote.checked_at)) return null;
    return source;
  }
  function caseEvidenceHTML(item, gateway, sourceMap) {
    const registry = sourceMap instanceof Map ? sourceMap : new Map(Object.entries(sourceMap || {}));
    const evidence = item && item.evidence;
    const scope = gateway && typeof gateway === 'object' && Array.isArray(gateway.source_ids) ? gateway.source_ids : [];
    const readable = evidence && typeof evidence === 'object' && !Array.isArray(evidence) ? evidence : null;
    const rows = [];
    // An absent or empty record is how older cases already look: they render nothing at all.
    const present = !!readable && Object.keys(readable).length > 0;
    if (present) {
      const layer = (name, label, state, body) => rows.push(evidenceRow(name, label, body, state));
      // A. What is visible in the picture, in our words.
      const observation = readable.observation && typeof readable.observation === 'object' ? readable.observation : {};
      const seen = evidenceText(observation.text);
      layer('observation', 'A · 画面观察 · 我们在图中看到的事实', seen ? 'present' : 'missing',
        seen ? `<p>${esc(seen)}</p>` : evidenceMissing('未提供画面观察：这张照片里到底看见了什么，需要你自己先描述。'));
      // B. The author's own wording, kept separate from everything we wrote.
      const quote = readable.quote && typeof readable.quote === 'object' && !Array.isArray(readable.quote) ? readable.quote : {};
      const quoted = evidenceText(quote.text);
      const source = checkedQuoteSource(item, {source_ids:scope}, quote, registry);
      const body = quoted ? `<blockquote class="case-evidence-quote">${esc(quoted)}</blockquote>` : evidenceMissing('未提供作者原话。');
      const status = source
        ? `<p class="case-evidence-status" data-verified="true">已逐字核对原文 · 语言：${esc(quote.language)} · 原文定位：${esc(quote.locator)} · 核验日期：${esc(quote.checked_at)} · 出处：<a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.short_title || source.title || quote.source_id)} ↗</a></p>`
        : '<p class="case-evidence-status" data-verified="false">未核验：缺少完整的原文比对记录（逐字核对、原文定位、语言、核验日期，以及与本案例页面一致的来源），不能当作作者已确认的原话。</p>';
      layer('quote', source ? 'B · 作者原话 · 已核对原文' : 'B · 作者原话 · 未核验', source ? 'verified' : 'unverified', body + status);
      // C. Our professional reading, explicitly not the author's words.
      const explanation = readable.explanation && typeof readable.explanation === 'object' && !Array.isArray(readable.explanation) ? readable.explanation : {};
      const reading = evidenceText(explanation.text);
      // A source we cannot actually link is not a citable basis, so it never becomes one.
      const listed = Array.isArray(explanation.source_ids) ? explanation.source_ids.filter(id => evidenceText(id) && scope.includes(id) && safeURL((registry.get(id) || {}).url)) : [];
      const cited = listed.map(id => { const source = registry.get(id); return `<a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.short_title || source.title || id)} ↗</a>`; }).join(' · ');
      const links = listed.length ? `<p class="case-evidence-sources">解释依据：${cited}</p>` : '<p class="case-evidence-missing">这段解释缺少可核对的来源记录。</p>';
      layer('explanation', 'C · 专业解释 · 我们的理解，不代表作者原话', reading ? 'present' : 'missing',
        (reading ? `<p>${esc(reading)}</p>` : evidenceMissing('未提供专业解释。')) + links);
      // D. What this changes in your own next shoot.
      const advice = readable.advice && typeof readable.advice === 'object' && !Array.isArray(readable.advice) ? readable.advice : {};
      const next = evidenceText(advice.text);
      layer('advice', 'D · 项目建议 · 下一次实拍怎么用', next ? 'present' : 'missing',
        next ? `<p>${esc(next)}</p>` : evidenceMissing('未提供练习建议。'));
    } else if (readable === null && evidence !== undefined && evidence !== null) {
      rows.push(evidenceRow('evidence', '教学证据 · 缺失', evidenceMissing('这条证据记录无法读取，四层内容均标记为未核验。'), 'unreadable'));
    }
    if (!rows.length) return '';
    return `<dl class="case-evidence" data-evidence-rows="${rows.length}">${rows.join('')}</dl>`;
  }
  function caseHTML(gateway, id) {
    const item = gateway.cases.find(c => c.id === id);
    if (!item) return '';
    const url = safeURL(item.url);
    const listedImages = Array.isArray(item.images) ? item.images : [];
    const images = item.display === 'note_media' ? listedImages.map(image=>{
      const registered=noteMedia.get(image.media_id);
      return registered ? {src:`/api/learning-note-media/${encodeURIComponent(registered.id)}`,alt:registered.alt,label:image.label || registered.position} : null;
    }).filter(Boolean) : item.display === 'source_remote' ? listedImages
      : item.display === 'licensed_remote' && item.rights.allowed === true ? [item] : [];
    const mediaURL = value => /^\/api\/learning-note-media\/[a-z0-9-]+$/.test(value) ? value : safeURL(value);
    const media = images.filter(image=>mediaURL(image.src)).map(image=>{
      const dimensions = Number.isInteger(image.width) && Number.isInteger(image.height) ? ` width="${image.width}" height="${image.height}"` : '';
      return `<div class="case-media">${image.label?`<p class="case-media-label">${esc(image.label)}</p>`:''}<div class="case-image"><img src="${esc(mediaURL(image.src))}" alt="${esc(image.alt)}" loading="lazy"${dimensions} referrerpolicy="no-referrer"><span class="case-loading" role="status">正在加载原案例照片…</span><span class="case-load-error" hidden>这张图片暂时无法加载。中文要点仍可阅读，原案例链接在下方。</span></div></div>`;
    }).join('');
    const summary = item.source_summary;
    const rights = item.rights || {}, review = item.review || {};
    // A field-guide case carries its evidence as one closed record. The legacy course and
    // the three conceptual gateways keep their four visible layers untouched.
    if (isFieldGuide(gateway)) {
      const record = [
        summary ? `<p>${esc(summary.text)}</p><span class="case-source-locator">原文定位：${esc(summary.locator)} · 核对于 ${esc(summary.checked_at)}</span>` : '',
        item.evidence && typeof item.evidence === 'object' && !Array.isArray(item.evidence)
          ? Object.entries(item.evidence).filter(([,value])=>value && typeof value==='object' && evidenceText(value.text))
            .map(([layer,value])=> {
              if (layer !== 'quote') return `<p class="case-record-line"><span>${esc(EVIDENCE_LAYER_LABEL[layer] || layer)}</span>${esc(evidenceText(value.text))}</p>`;
              const checked = checkedQuoteSource(item, gateway, value, sources);
              return `<p class="case-record-line" data-verified="${!!checked}"><span>${checked?'作者原话 · 已核对':'待核引文 · 未核验'}</span>${esc(evidenceText(value.text))}${checked?` · 原文定位：${esc(value.locator)} · <a href="${esc(safeURL(checked.url))}" target="_blank" rel="noopener noreferrer">出处 ↗</a>`:''}</p>`;
            }).join('')
          : '',
        review.detail ? `<p><span>图像核验范围</span>${esc(review.detail)}${review.checked_at?` · 核对于 ${esc(review.checked_at)}`:''}</p>` : '',
        rights.statement ? `<p><span>使用与限制</span>${esc(rights.statement)}${safeURL(rights.url)?` <a href="${esc(safeURL(rights.url))}" target="_blank" rel="noopener noreferrer">权利说明 ↗</a>`:''}</p>` : '',
      ].filter(Boolean).join('');
      return `<figure class="gateway-case" data-case="${esc(id)}">${media || `<a class="gateway-case-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">打开原站实拍对照 ↗<span>${esc(item.title)}</span></a>`}<figcaption><strong>${esc(item.title)}</strong><span>${esc(item.author)} · ${esc(item.caption)}</span><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">原案例与图像出处 ↗</a>${record?`<details class="case-record"><summary>来源与研究记录</summary>${record}</details>`:''}</figcaption></figure>`;
    }
    return `<figure class="gateway-case" data-case="${esc(id)}">${media || `<a class="gateway-case-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">打开原站实拍对照 ↗<span>${esc(item.title)}</span></a>`}<figcaption><strong>${esc(item.title)}</strong><span>${esc(item.author)} · ${esc(item.caption)}</span>${caseEvidenceHTML(item,gateway,sources)}${summary?`<details class="case-source-summary"><summary>原文要点 · 中文转述</summary><p>${esc(summary.text)}</p><span class="case-source-locator">原文定位：${esc(summary.locator)} · 核对于 ${esc(summary.checked_at)}</span></details>`:''}<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">原案例与图像出处 ↗</a><details><summary>图像使用与核验范围</summary><p>${esc(item.review.detail)}</p><p>${esc(item.rights.statement)} <a href="${esc(safeURL(item.rights.url))}" target="_blank" rel="noopener noreferrer">权利说明 ↗</a></p></details></figcaption></figure>`;
  }
  function citations(ids) {
    return (ids || []).map(id => sources.get(id)).filter(Boolean).map(source => `<a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.short_title || source.title)} ↗</a>`).join(' · ');
  }
  function blockHTML(block, gateway, draft) {
    switch (block.type) {
      case 'paragraph': return `<p>${esc(block.text)}</p>`;
      case 'heading': return `<h3>${esc(block.text)}</h3>`;
      case 'list': return `<ul>${block.items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`;
      case 'comparison': return `<div class="gateway-observations">${block.rows.map(row=>`<div><p class="gateway-small">第一眼可能会问</p><p>${esc(row.novice)}</p><p class="gateway-small">再往下观察</p><p><strong>${esc(row.expert)}</strong></p><p>${esc(row.question)}</p></div>`).join('')}</div>`;
      case 'case': return caseHTML(gateway, block.case_id);
      case 'tradeoffs': return `<div class="course-tradeoffs">${block.rows.map(row=>`<article><h3>${esc(row.action)}</h3><p><strong>预计变化：</strong>${esc(row.effect)}</p><p><strong>代价：</strong>${esc(row.cost)}</p><p><strong>怎样检查：</strong>${esc(row.test)}</p></article>`).join('')}</div>`;
      case 'case_pair': return `<div class="gateway-case-pair">${block.case_ids.map(id=>caseHTML(gateway,id)).join('')}</div>`;
      case 'field_recipe': return recipeHTML(block, gateway);
      case 'video_sequence': return videoHTML(block);
      case 'exercise': {
        const question = `<h3>${esc(block.title)}</h3><p>${esc(block.prompt)}</p>`;
        if (gateway.kind === 'course') return `<div class="gateway-exercise">${question}</div>`;
        return `<div class="gateway-exercise">${question}${block.options?.length?`<div class="gateway-choices" role="group" aria-label="${esc(block.title)}">${block.options.map(option=>`<button type="button" data-gw-choice="${esc(block.id)}" data-value="${esc(option)}" aria-pressed="${draft.answers[block.id]===option}">${esc(option)}</button>`).join('')}</div>`:''}<label for="gw-answer-${esc(block.id)}">${esc(block.label || '先记下你的观察（可跳过）')}</label><textarea id="gw-answer-${esc(block.id)}" data-gw-answer="${esc(block.id)}" maxlength="8000" rows="3" placeholder="${esc(block.placeholder || '图中看见了什么？还有什么不能确定？')}">${esc(draft.answers[block.id] || '')}</textarea></div>`;
      }
      case 'reveal': return `<details class="gateway-reveal" data-gw-reveal="${esc(block.activity_id)}"${draft.revealed.includes(block.activity_id)?' open':''}><summary>${esc(block.title)}</summary><div>${block.paragraphs.map(text=>`<p>${esc(text)}</p>`).join('')}${block.source_ids?.length?`<p class="gateway-citation">分析依据：${citations(block.source_ids)}</p>`:''}</div></details>`;
      default: return '';
    }
  }
  function sourceHTML(gateway) {
    return gateway.source_ids.map(id=>sources.get(id)).filter(Boolean).map(source=>`<article class="gateway-source"><h3><a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.title)} ↗</a></h3><p>${esc(source.author)} · ${esc(source.reading_depth)} · 核对于 ${esc(source.checked_at)}</p><dl><dt>定位</dt><dd>${esc(source.locator)}</dd><dt>支持什么</dt><dd>${esc(source.support)}</dd><dt>边界</dt><dd>${esc(source.limitation)}</dd></dl></article>`).join('');
  }
  function selfAssessment(draft) {
    return `<form id="gateway-form" class="gateway-reflection"><label for="gateway-stage">我目前能做到什么 · 自评</label><select id="gateway-stage">${Object.entries(labels).map(([value,label])=>`<option value="${value}"${draft.stage===value?' selected':''}>${label}</option>`).join('')}</select><p id="gateway-stage-note" class="gateway-small">${esc(notes[draft.stage])}</p><label for="gw-confusion">仍然困惑的部分 / 下次实拍如何验证</label><textarea id="gw-confusion" data-gw-answer="confusion" rows="3" maxlength="8000">${esc(draft.answers.confusion || '')}</textarea><div class="gateway-save-row"><button id="gateway-save" class="primary-button" type="submit"${host.canWrite()&&!busy?'':' disabled'}>保存观察与自评</button><p id="gateway-message" role="status">${host.canWrite() ? (draft.dirty?'有未保存的草稿；关闭抽屉仍会保留在本标签页。':'只有主动保存才会写入私人记录。') : '私人记录当前不可写；可阅读和在本标签页暂存草稿。'}</p></div><button type="button" id="gateway-reload" class="text-link" hidden>加载服务器记录（替换此入口的本页草稿）</button></form>`;
  }
  function render() {
    const gateway = current, draft = getDraft(gateway.id), field = isFieldGuide(gateway);
    dialog.innerHTML = `<header class="gateway-reader-header"><div><p class="eyebrow">${gateway.kind==='course'?esc(courseLabel(gateway)):'CONCEPTUAL GATEWAY · 认知入口'}</p><h2 id="gateway-title" tabindex="-1">${esc(gateway.title)}</h2></div><button id="gateway-close" class="close-button" type="button" aria-label="关闭阅读，返回原位置">×</button></header><div class="gateway-scroll"><div class="gateway-reading-layout"><aside class="gateway-outline"><details open><summary>阅读目录</summary><nav aria-label="阅读章节">${gateway.sections.map((section,index)=>`<button type="button" data-gw-section="${esc(section.id)}"><span>${String(index+1).padStart(2,'0')}</span>${esc(section.title)}</button>`).join('')}</nav></details><label for="gateway-switch">切换课程 / 认知入口</label><select id="gateway-switch">${catalog.map(item=>`<option value="${esc(item.id)}"${gateway.id===item.id?' selected':''}>${esc(item.title)}</option>`).join('')}</select></aside><article class="gateway-reading"><div class="gateway-reading-intro"><p class="gateway-byline">${esc(gateway.author)} · ${esc(gateway.reading_depth)}</p><p>${esc(gateway.outcome)}</p><p class="gateway-small">${esc(gateway.prior_knowledge)}</p><p class="gateway-citation">专业依据：${citations(gateway.source_ids.slice(0,3))}</p></div>${gateway.sections.map((section,index)=>`<section class="gateway-chapter" id="gw-${esc(section.id)}" tabindex="-1"><p class="eyebrow">${esc(section.kicker || (field ? `STEP ${String(index+1).padStart(2,'0')}` : section.id.toUpperCase()))}</p><h2>${esc(section.title)}</h2>${section.blocks.map(block=>blockHTML(block,gateway,draft)).join('')}${section.source_ids?.length?`<p class="gateway-citation">本节依据：${citations(section.source_ids)}</p>`:''}${section.id==='reflect' && gateway.kind!=='course'?selfAssessment(draft):''}${section.id==='sources'&&!field?sourceHTML(gateway):''}</section>`).join('')}${field?`<details class="gateway-source-fold"><summary>来源与研究记录</summary>${sourceHTML(gateway)}</details>`:''}<footer class="gateway-reading-footer"><p>继续在技能地图里练习</p>${gateway.skill_ids.map(id=>`<button type="button" data-gw-skill="${esc(id)}">${esc(host.skillName(id))} →</button>`).join('')}</footer></article></div></div>`;
    scroll = dialog.querySelector('.gateway-scroll');
    dialog.querySelectorAll('img').forEach(img=>{
      const loading=img.parentElement.querySelector('.case-loading'), error=img.parentElement.querySelector('.case-load-error');
      const url = img.src, known = mediaPresentation.get(url);
      const loaded = () => {
        if (!img.naturalWidth) return;
        mediaPresentation.set(url, {status:'loaded', width:img.naturalWidth, height:img.naturalHeight});
        img.hidden=false; loading.hidden=true; error.hidden=true;
      };
      const failed = () => {
        mediaPresentation.set(url, {status:'failed'});
        img.hidden=true; loading.hidden=true; error.hidden=false;
      };
      if (known?.status === 'failed') {
        failed();
      } else if (known?.status === 'loaded') {
        // width:auto ignores HTML dimensions while a lazy image has no intrinsic
        // size. Reserve its observed ratio within the same responsive height cap.
        img.style.width=`min(100%, ${known.width}px, calc(var(--case-image-limit) * ${known.width / known.height}))`;
        img.style.aspectRatio=`${known.width} / ${known.height}`;
      }
      img.addEventListener('load',loaded);
      img.addEventListener('error',failed);
      if(img.complete) {
        if(img.naturalWidth) loaded();
        else failed();
      }
    });
    // Restore only after settled media has its prior geometry. Native scroll anchoring
    // should handle genuinely new content, not compensate for state we just discarded.
    scroll.scrollTop = draft.scroll || 0;
    dialog.querySelectorAll('[data-gw-reveal]').forEach(details=>details.addEventListener('toggle',()=>{
      const active = getDraft(gateway.id), id = details.dataset.gwReveal;
      const before = active.revealed.includes(id);
      if (before === details.open) return;
      active.revealed = details.open ? [...active.revealed,id] : active.revealed.filter(value=>value!==id);
      active.dirty=true; remember();
    }));
    document.getElementById('gateway-form')?.addEventListener('submit', save);
  }
  function close(restore=true) {
    if (!dialog?.open) return;
    remember();
    const previous = origin;
    current = null; origin = null;
    dialog.close(); document.body.classList.remove('gateway-is-open');
    if (restore && previous?.route === location.hash) {
      window.scrollTo({top:previous.scroll,behavior:'instant'});
      if (previous.focus?.isConnected) previous.focus.focus({preventScroll:true});
    }
  }
  function open(id, button) {
    const gateway = catalog.find(item=>item.id===id);
    if (!gateway) return;
    if (dialog.open) remember();
    else origin = {route:location.hash, scroll:window.scrollY, focus:button || document.activeElement};
    current=gateway; render();
    if (!dialog.open) { dialog.showModal(); document.body.classList.add('gateway-is-open'); }
    document.getElementById('gateway-title').focus({preventScroll:true});
    scroll.scrollTop=getDraft(id).scroll || 0;
  }
  async function save(event) {
    event.preventDefault();
    if (!current || busy || !host.canWrite()) return;
    remember();
    const id=current.id, draft=getDraft(id);
    // Unrelated writes may advance the shared revision without changing this record.
    if (draft.serverSnapshot === JSON.stringify(record(id))) draft.revision=host.revision();
    const payload={stage:draft.stage,answers:{...draft.answers},revealed:[...draft.revealed],last_section:draft.last_section,expected_revision:draft.revision};
    busy=true;
    document.getElementById('gateway-save').disabled=true;
    notice('正在保存…');
    try {
      const revision=await host.save(id,payload);
      draft.revision=revision; draft.serverSnapshot=JSON.stringify(record(id));
      const changedWhileSaving=JSON.stringify([draft.stage,draft.answers,draft.revealed,draft.last_section])!==JSON.stringify([payload.stage,payload.answers,payload.revealed,payload.last_section]);
      draft.dirty=changedWhileSaving;
      try { sessionStorage.setItem(key(id),JSON.stringify(draft)); } catch {}
      if(current?.id===id) notice(changedWhileSaving?'先前内容已保存，保存过程中新增的编辑仍是草稿。':'观察与自评已保存。阅读行为没有改变你的能力等级。');
    } catch(error) {
      if(current?.id===id) {
        notice(error.status===409?'服务器记录已更新；你的草稿仍保留。检查后可加载服务器版本，再重新编辑。':`未保存：${error.message}。本页草稿仍保留。`,true);
        if(error.status===409) document.getElementById('gateway-reload').hidden=false;
      }
    } finally {
      busy=false;
      const button=document.getElementById('gateway-save');
      if(button) button.disabled=!host.canWrite();
    }
  }
  function links(skillId) {
    const matches=catalog.filter(item=>item.skill_ids.includes(skillId)).sort((a,b)=>Number(b.kind==='course')-Number(a.kind==='course'));
    return matches.length?`<section class="skill-gateway-entry"><p class="eyebrow">把相关技能连起来理解</p>${matches.map(gateway=>`<button type="button" class="gateway-entry" data-open-gateway="${esc(gateway.id)}"><span><strong>${esc(gateway.title)}</strong><span>${esc(gateway.question)}</span></span><span class="gateway-entry-action">学习原理 ↗</span></button>`).join('')}</section>`:'';
  }
  function init(data, options) {
    catalog=data.gateways || []; sources=new Map((data.gateway_sources || []).map(item=>[item.id,item])); host=options;
    noteMedia=new Map((data.learning_content?.media || []).map(item=>[item.id,item]));
    dialog=document.getElementById('gateway-dialog');
    const index=document.getElementById('gateway-index');
    index.hidden=!catalog.length;
    const courses=catalog.filter(item=>item.kind==='course'), gateways=catalog.filter(item=>item.kind!=='course');
    const entries=items=>items.map((gateway,i)=>`<button type="button" class="gateway-entry" data-open-gateway="${esc(gateway.id)}"><span class="gateway-index-number">${String(i+1).padStart(2,'0')}</span><span><strong>${esc(gateway.title)}</strong><span>${esc(gateway.question)}</span></span><span aria-hidden="true">↗</span></button>`).join('');
    // One course may name itself; the "sample" wording only survives while no entry does.
    const labelled=courses.filter(item=>typeof item.label==='string'&&item.label.trim()).map(item=>item.label.trim());
    const courseNote=labelled.length?`${labelled.join(' · ')}。解释原因、比较代价，再用新照片判断。`:'解释原因、比较代价，再用新照片判断。样板等你试读，暂不批量扩展。';
    index.innerHTML=`${courses.length?`<section class="course-index"><div class="section-heading"><div><p class="eyebrow">PHOTO ATLAS · COURSE</p><h2>从现场问题，连续学一章</h2></div><p class="section-note">${esc(courseNote)}</p></div>${entries(courses)}</section>`:''}<div class="section-heading"><div><p class="eyebrow">LEARN TO SEE</p><h2>从一个问题，换一种看法</h2></div><p class="section-note">原有认知入口。能力地图用于检索与记录；短笔记用于回看。</p></div><div class="gateway-index-list">${entries(gateways)}</div>`;
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    dialog.addEventListener('click',event=>{
      const target=event.target;
      if(target.id==='gateway-close') close();
      const chapter=target.closest('[data-gw-section]');
      if(chapter&&current) {
        const draft=getDraft(current.id); draft.last_section=chapter.dataset.gwSection;
        const section=document.getElementById(`gw-${draft.last_section}`);
        section.scrollIntoView({block:'start',behavior:'instant'}); section.focus({preventScroll:true}); remember();
      }
      const choice=target.closest('[data-gw-choice]');
      if(choice&&current) {
        const draft=getDraft(current.id), id=choice.dataset.gwChoice;
        draft.answers[id]=choice.dataset.value; draft.dirty=true;
        document.getElementById(`gw-answer-${id}`).value=choice.dataset.value;
        dialog.querySelectorAll(`[data-gw-choice="${id}"]`).forEach(button=>button.setAttribute('aria-pressed',String(button===choice))); remember();
      }
      const skill=target.closest('[data-gw-skill]');
      if(skill) {const id=skill.dataset.gwSkill;close(false);host.navigate(id);}
      if(target.id==='gateway-reload'&&current) {
        const id=current.id; drafts.delete(id); try{sessionStorage.removeItem(key(id));}catch{}
        render();document.getElementById('gw-reflect').scrollIntoView({block:'start'});notice('已加载服务器记录；请核对后编辑。');
      }
    });
    dialog.addEventListener('input',event=>{
      if(!current)return;
      const draft=getDraft(current.id), target=event.target;
      if(target.dataset.gwAnswer) {draft.answers[target.dataset.gwAnswer]=target.value;draft.dirty=true;remember();notice('有未保存的草稿；关闭或切换入口会保留在本标签页。');}
    });
    dialog.addEventListener('change',event=>{
      if(event.target.id==='gateway-switch') open(event.target.value);
      if(event.target.id==='gateway-stage'&&current) {const draft=getDraft(current.id);draft.stage=event.target.value;draft.dirty=true;document.getElementById('gateway-stage-note').textContent=notes[draft.stage];remember();notice('自评尚未保存。');}
    });
    document.addEventListener('click',event=>{const button=event.target.closest('[data-open-gateway]');if(button)open(button.dataset.openGateway,button);});
    window.addEventListener('pagehide',remember);
  }
  function openFromURL() {
    const id=new URLSearchParams(location.search).get('course');
    if(catalog.some(item=>item.id===id && item.kind==='course')) open(id);
  }
  return {init,links,close,openFromURL,caseEvidenceHTML,onRouteChange:()=>{if(dialog?.open)close(false);},isOpen:()=>!!dialog?.open};
})();
