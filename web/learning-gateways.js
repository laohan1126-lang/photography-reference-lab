'use strict';
// Teaching owns its drafts and reading position; the atlas owns routes and writes.
window.LearningGateways = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {unassessed:'尚未自评', unseen:'尚未接触', terms:'了解术语', principles:'理解基本原理', analysis:'能够分析案例', transfer:'能独立迁移到新场景', field:'已经过实际拍摄验证'};
  const notes = {unassessed:'阅读与展开解析不会替你升级。', unseen:'这是你的自评，可以直接跳到有挑战的部分。', terms:'能认出概念名称，还不等于能解释照片。', principles:'能解释变量关系；下一步用具体画面检验。', analysis:'能指出图中证据，也能说清尚不能确定的条件。', transfer:'由你确认能在未讲过的场景中独立判断。', field:'由你确认已经拍摄、比较并验证；可在关联技能中附实拍记录。'};
  const drafts = new Map();
  let catalog = [], sources = new Map(), noteMedia = new Map(), contentSources = new Map(), speechRecords = new Map(), host, dialog, scroll, current = null, origin = null, busy = false;
  const key = id => `photography-gateway-draft-v2:${id}`;
  const safeURL = value => { try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password ? u.href : ''; } catch { return ''; } };
  // Video evidence is optional metadata. Anything a field claims about itself is never enough on its own.
  const evidenceLayers = {
    A: {tag:'A 画面观察', note:'视频画面里直接看得见的内容，不是谁的说法'},
    B: {tag:'B 摄影师本人言语', note:'视频作者本人在片中说的话'},
    C: {tag:'C 专业解释（第三方依据）', note:'独立来源的解释，不是作者原话'},
    D: {tag:'D 项目建议 / 待验证推断', note:'课程给的项目动作，尚未在视频中核验'}
  };
  const evidenceVerdicts = {
    verified:{label:'已核验（仅限所列片段与核验方式）', hint:'核验方式与日期可对照，仍不等于看过整段视频。'},
    unverified:{label:'未核实', hint:'缺少可核对的核验依据，按未核实展示。'},
    insufficient:{label:'证据不足', hint:'来源、时间码或正文缺失，无法展示为证据。'},
    suggestion:{label:'建议 / 推断', hint:'项目建议或待验证推断，不作事实陈述。'}
  };
  // A verification method names what a person actually compared; a field claiming it was checked is not a method.
  const verificationMethods = {
    frames_reviewed:'逐帧查看已登记的画面截图',
    clip_watched:'通看已登记的播放片段',
    av_segment_check:'按时间码逐段听看音视频',
    subtitle_segment_check:'按时间码逐段核对字幕',
    text_cross_check:'逐段核对来源正文'
  };
  // A single frame cannot prove what somebody said; third-party prose is not proved by watching frames either.
  const layerMethods = {
    A: new Set(['frames_reviewed','clip_watched']),
    B: new Set(['av_segment_check','subtitle_segment_check']),
    C: new Set(['text_cross_check'])
  };
  const methodLabel = code => verificationMethods[code] || '';
  const quoteKinds = new Set(['verbatim','translation','paraphrase']);
  const quoteLabel = {verbatim:'逐字引文 · 视频原话，未翻译', translation:'中文翻译 · 对应上方原文，不是新拍视频', paraphrase:'转述 · 非摄影者逐字原话'};
  const clipSeconds = value => Number.isInteger(value) && value >= 0 && value <= 86400;
  const evidenceTime = seconds => `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
  const timeAt = (url, seconds) => { const target = new URL(url); target.searchParams.set('t', String(seconds)); return target.href; };
  const samePerson = (a, b) => typeof a === 'string' && typeof b === 'string' && a.trim().replace(/\s+/g,' ').toLowerCase() === b.trim().replace(/\s+/g,' ').toLowerCase();
  const frameSeconds = value => {
    if (Number.isInteger(value)) return value;
    if (typeof value === 'string' && /^\d{1,3}:\d{2}$/.test(value.trim())) {
      const parts = value.trim().split(':').map(Number);
      return parts[0] * 60 + parts[1];
    }
    return null;
  };
  // Only a real calendar day counts as a checking date; 2026-99-99 is not one.
  const calendarDay = value => {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
    const [year, month, day] = value.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  };
  // Identity of the video itself: ?t= and #fragment never make two clips look different, but the video ID always does.
  const timingParams = new Set(['t','time','start','end','timestamp','amp','list','index']);
  const youTubeID = value => /^[A-Za-z0-9_-]{11}$/.test(value || '') ? value : '';
  const videoKey = value => {
    const href = safeURL(value);
    if (!href) return '';
    const parsed = new URL(href);
    const host = parsed.hostname.toLowerCase().replace(/^www\./, '');
    const segments = parsed.pathname.split('/').filter(Boolean);
    if (host === 'youtu.be') { const id = youTubeID(segments[0]); return id ? `youtube:${id}` : ''; }
    if (/(^|\.)youtube(-nocookie)?\.com$/.test(host)) {
      const fromQuery = youTubeID(parsed.searchParams.get('v'));
      if (fromQuery) return `youtube:${fromQuery}`;
      if (new Set(['shorts','embed','live','v']).has(segments[0])) {
        const id = youTubeID(segments[1]);
        return id ? `youtube:${id}` : '';
      }
      return '';
    }
    if (host === 'bilibili.com' || host === 'b23.tv') {
      const tagged = segments.find(part => /^BV[0-9A-Za-z]{10}$/.test(part));
      if (!tagged) return '';
      const page = /^\d+$/.test(parsed.searchParams.get('p') || '') ? `:p${parsed.searchParams.get('p')}` : '';
      return `bilibili:${tagged}${page}`;
    }
    // Other sites keep every parameter that decides which item this is; only timing and tracking are dropped.
    const kept = [...parsed.searchParams.entries()].filter(([name]) => !timingParams.has(name.toLowerCase()));
    return `${host}${parsed.pathname}${kept.length ? `?${kept.map(([name, value]) => `${name}=${value}`).join('&')}` : ''}`;
  };
  const MISSING_TEXT = '没有可读的证据正文';
  const record = id => host.record(id) || {};
  function getDraft(id) {
    if (drafts.has(id)) return drafts.get(id);
    let saved;
    try { saved = JSON.parse(sessionStorage.getItem(key(id)) || 'null'); } catch {}
    const server = record(id);
    const value = saved && saved.answers && typeof saved.answers === 'object' && Number.isInteger(saved.revision)
      ? saved : {stage:server.stage || 'unassessed', answers:{...(server.answers || {})}, revealed:[...(server.revealed || [])], last_section:server.last_section || 'problem', revision:host.revision(), serverSnapshot:JSON.stringify(server), scroll:0, dirty:false};
    if (!Array.isArray(value.revealed)) value.revealed = [];
    if (!(value.stage in labels)) value.stage = 'unassessed';
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
  function evidenceTiming(item, entry) {
    const caseKey = videoKey(item && item.url);
    if (!caseKey) return {ok:false, reason:'该案例没有安全、可识别的视频出处，时间码无法归属到具体视频'};
    if (!clipSeconds(entry.start) || !clipSeconds(entry.end) || entry.end <= entry.start) return {ok:false, reason:'缺少可用时间码'};
    const clip = item.playback;
    if (!clipSeconds(clip?.start) || !clipSeconds(clip?.end) || clip.end <= clip.start) return {ok:false, reason:'该案例没有登记播放区间，无法确认这段时间码属于本片'};
    if (entry.start < clip.start || entry.end > clip.end) return {ok:false, reason:`时间码 ${evidenceTime(entry.start)}–${evidenceTime(entry.end)} 超出本案例播放区间 ${evidenceTime(clip.start)}–${evidenceTime(clip.end)}`};
    const declared = typeof entry.url === 'string' ? entry.url.trim() : '';
    if (declared) {
      const entryKey = videoKey(declared);
      if (!entryKey) return {ok:false, reason:'声明的视频出处不是安全、可识别的视频地址'};
      if (entryKey !== caseKey) return {ok:false, reason:'声明的视频出处与该案例登记的视频不是同一条'};
    }
    return {ok:true, start:entry.start, end:entry.end, text:`${evidenceTime(entry.start)}–${evidenceTime(entry.end)}`};
  }
  // Frame review only counts when it points at a screenshot this checkout already holds, from this case's own video.
  function frameBinding(item, entry, timing) {
    if (!timing.ok) return timing.reason;
    const mediaId = typeof entry.media_id === 'string' ? entry.media_id.trim() : '';
    if (!mediaId) return '没有指向任何一张已登记的画面截图';
    const media = noteMedia.get(mediaId);
    if (!media) return '所指截图不在本机已登记的画面清单里';
    const at = frameSeconds(media.position);
    if (at === null || !clipSeconds(at)) return '该截图没有登记可追溯的时间位置';
    if (at < timing.start || at > timing.end) return `该截图取自 ${evidenceTime(at)}，不在所列时间码 ${timing.text} 内`;
    const sourceId = typeof media.source_id === 'string' ? media.source_id.trim() : '';
    const source = sourceId ? contentSources.get(sourceId) : null;
    if (!source) return '该截图没有登记到可追溯的视频来源';
    const sourceKey = videoKey(source.url);
    if (!sourceKey) return '该截图登记的视频来源不是安全、可识别的视频地址';
    if (sourceKey !== videoKey(item.url)) return '该截图登记的视频来源与本案例不是同一条视频';
    return '';
  }
  // Saying the words were checked is not a check: layer B needs a registered transcript record for this very clip.
  function speechBinding(item, entry, timing) {
    if (!timing.ok) return timing.reason;
    const method = typeof entry.verified_by === 'string' ? entry.verified_by : '';
    const recordId = typeof entry.speech_record_id === 'string' ? entry.speech_record_id.trim() : '';
    if (!recordId) return '没有指向任何一条已登记的言语记录（speech_record_id），只有“已核对音视频/字幕”的自述';
    const record = speechRecords.get(recordId);
    if (!record || typeof record !== 'object') return '所指言语记录不在本机已登记的言语记录清单里';
    // The registry's own trust state is a precondition, not something matching fields may lift: a record that says it is
    // simulated, or that it was never verified, stays unverified however well its source, timing, speaker and quote line up.
    if (record.simulated === true) return '所指言语记录登记为模拟数据，不能用来核验作者本人在片中的说话';
    if (record.verified === false || record.status === 'unverified') return '所指言语记录已被记为未核实，字段对得上也不能提升它';
    const sourceId = typeof record.source_id === 'string' ? record.source_id.trim() : '';
    const source = sourceId ? contentSources.get(sourceId) : null;
    const declared = typeof record.url === 'string' ? record.url.trim() : '';
    const recordURL = declared || (source && typeof source.url === 'string' ? source.url.trim() : '');
    if (!recordURL) return '该言语记录没有登记到可追溯的视频出处';
    const recordKey = videoKey(recordURL);
    if (!recordKey) return '该言语记录登记的视频出处不是安全、可识别的视频地址';
    if (recordKey !== videoKey(item.url)) return '该言语记录登记的视频与本案例不是同一条';
    if (record.start !== timing.start || record.end !== timing.end) return '该言语记录登记的时间段与这条证据所列时间码不是同一段';
    if (!samePerson(record.speaker, item.author)) return '该言语记录登记的说话者与本案例作者对不上';
    const transcript = typeof record.transcript === 'string' ? record.transcript.trim() : '';
    if (!transcript) return '该言语记录没有写出实际转录原文';
    const quoted = entry.quote_kind === 'translation'
      ? (typeof entry.original === 'string' ? entry.original.trim() : '')
      : (typeof entry.text === 'string' ? entry.text.trim() : '');
    if (!quoted || transcript !== quoted) return '转录原文与这条证据所引的原话对不上';
    if (typeof record.verification_scope !== 'string' || !record.verification_scope.trim()) return '该言语记录没有写清核验范围';
    if (!calendarDay(record.checked_at)) return '该言语记录没有可核对的真实核验日期';
    if (method && record.verified_by !== method) return '该言语记录的核对方式与这条证据所注方式不是同一种';
    if (!layerMethods.B.has(record.verified_by)) return '该言语记录登记的核对方式不能证明作者本人在片中说了什么';
    return '';
  }
  // Anything read for display is normalized once, here: a value that is not plain text counts as missing, never as a crash.
  const plain = value => typeof value === 'string' ? value : '';
  const displayFields = {text:'证据正文', speaker:'说话者', original:'原文', verification_scope:'核验范围'};
  function readableEntry(entry) {
    const safe = {...entry};
    const unreadable = [];
    for (const [field, name] of Object.entries(displayFields)) {
      const value = entry[field];
      if (value === undefined || value === null) continue;
      if (typeof value !== 'string') { safe[field] = ''; unreadable.push(name); continue; }
      safe[field] = value;
    }
    return {entry: safe, unreadable};
  }
  function citedSources(entry, caseKey) {
    const ids = (Array.isArray(entry.source_ids) ? entry.source_ids : []).filter(id => typeof id === 'string' && id.trim());
    const problems = ids.length ? [] : ['没有列出可追溯的来源'];
    const registered = [];
    for (const id of ids) {
      const source = sources.get(id);
      if (!source) { problems.push('所列来源没有登记在本项目的来源清单里'); continue; }
      if (!safeURL(source.url)) { problems.push('所列来源的链接不是安全地址'); continue; }
      if (caseKey && videoKey(source.url) === caseKey) { problems.push('所列来源就是本案例这条视频，不能当作独立第三方依据'); continue; }
      registered.push(source);
    }
    if (!registered.length && !problems.length) problems.push('没有可追溯的独立来源');
    return {problems, registered};
  }
  function evidenceIssues(item, entry, layer, timing, simulated) {
    const issues = [];
    if (typeof entry.text !== 'string' || !entry.text.trim()) issues.push(MISSING_TEXT);
    if (simulated) issues.push('模拟夹具，非真实视频研究，不构成核验');
    if (entry.verified === false || entry.status === 'unverified') issues.push('这条证据已被记为未核实，不能靠其他字段提升');
    if (layer === 'B') {
      if (entry.attribution !== 'clip_speech') issues.push('没有明确声明这是作者本人在片中的说话');
      if (!samePerson(entry.speaker, item.author)) issues.push('说话者没有对上本案例登记的作者');
      if (!quoteKinds.has(entry.quote_kind)) issues.push('没有说明这是逐字原话、翻译还是转述');
      else if (entry.quote_kind === 'paraphrase') issues.push('转述不能当作作者本人的逐字言语');
      if (entry.quote_kind === 'translation' && (typeof entry.original !== 'string' || !entry.original.trim())) issues.push('标为翻译但缺少原文');
      if (entry.verified_by === 'av_segment_check' || entry.verified_by === 'subtitle_segment_check') {
        const problem = speechBinding(item, entry, timing);
        if (problem) issues.push(problem);
      }
    }
    if (layer === 'A') {
      const method = entry.verified_by;
      if (method === 'frames_reviewed') { const problem = frameBinding(item, entry, timing); if (problem) issues.push(problem); }
      else if (method === 'clip_watched') {
        if (!timing.ok) issues.push(timing.reason);
        if (!citedSources(entry, videoKey(item.url)).registered.length) issues.push('通看片段却没有登记可追溯的片段来源');
      } else if (!timing.ok) issues.push(timing.reason);
    } else if (layer === 'B' && !timing.ok) issues.push(timing.reason);
    if (layer === 'C') {
      issues.push(...citedSources(entry, videoKey(item.url)).problems);
      if (typeof entry.verification_scope !== 'string' || !entry.verification_scope.trim()) issues.push('没有写清这段解释在来源中的范围');
    }
    const allowed = layerMethods[layer];
    const method = typeof entry.verified_by === 'string' ? entry.verified_by : '';
    if (!allowed || !allowed.has(method)) issues.push('所注核验方式与这一层证据能证明的事情不相称，或没有登记核验方式');
    else if (!calendarDay(entry.checked_at)) issues.push('没有可核对的真实核验日期');
    return issues;
  }
  function evidenceVerdict(item, entry, layer, timing, simulated, issues) {
    if (layer === 'D') return issues.includes(MISSING_TEXT) ? 'insufficient' : 'suggestion';
    if (typeof entry.text !== 'string' || !entry.text.trim()) return 'insufficient';
    if (simulated) return 'unverified';
    return issues.length ? 'unverified' : 'verified';
  }
  // A quote_kind only counts when it is one of the three known plain strings. Anything else — an object, a number, a
  // missing field — is unknown and degrades to the conservative paraphrase label; the value is never coerced into a
  // string, because an entry's own toString is untrusted input that can throw and is not a statement of its meaning.
  const quoteKindOf = entry => { const kind = entry.quote_kind; return typeof kind === 'string' && quoteKinds.has(kind) ? kind : ''; };
  function evidenceQuoteHTML(entry) {
    const kind = quoteKindOf(entry);
    if (kind === 'translation') return `<blockquote class="evidence-quote"><span class="evidence-quote-kind">原文</span>${esc(entry.original)}</blockquote><p class="evidence-body"><span class="evidence-quote-kind">中文翻译</span>${esc(entry.text)}</p><span class="evidence-kind">${quoteLabel.translation}</span>`;
    const tag = kind === 'verbatim' ? 'blockquote' : 'p';
    return `<${tag} class="evidence-body">${esc(entry.text)}</${tag}><span class="evidence-kind">${quoteLabel[kind] || quoteLabel.paraphrase}</span>`;
  }
  function frameLabel(entry) {
    const media = typeof entry.media_id === 'string' ? noteMedia.get(entry.media_id.trim()) : null;
    const at = media ? frameSeconds(media.position) : null;
    if (!media || at === null || !clipSeconds(at)) return '';
    return `画面来源：已登记截图 · 取自 ${evidenceTime(at)}${typeof media.caption === 'string' && media.caption.trim() ? ` · ${media.caption.trim()}` : ''}`;
  }
  function evidenceEntryHTML(item, url, entry, simulated) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) return `<div class="evidence-item" data-verdict="insufficient"><p class="evidence-tag">未分类证据 · 证据不足</p><p class="evidence-note">该条不是可读的证据对象，已跳过。</p></div>`;
    const layer = typeof entry.layer === 'string' ? entry.layer.trim().toUpperCase() : '';
    const meta = evidenceLayers[layer];
    if (!meta) {
      const unknown = readableEntry(entry);
      return `<div class="evidence-item" data-verdict="insufficient"><p class="evidence-tag">未分类证据 · 证据不足</p><p class="evidence-body">${esc(unknown.entry.text)}</p><p class="evidence-note">层级标识无法识别，不能归入 A/B/C/D。</p></div>`;
    }
    const readable = readableEntry(entry);
    const view = readable.entry;
    const timing = (layer === 'A' || layer === 'B') ? evidenceTiming(item, view) : {ok:false};
    const issues = evidenceIssues(item, view, layer, timing, simulated);
    if (readable.unreadable.length) issues.push(`${readable.unreadable.join('、')}不是可读文本，无法展示或核对，按未核实处理`);
    const verdict = evidenceVerdict(item, view, layer, timing, simulated, issues);
    const shown = evidenceVerdicts[verdict];
    const speaker = layer === 'B' && view.speaker ? `<p class="evidence-meta">说话者：${samePerson(view.speaker, item.author) ? esc(view.speaker) : `${esc(view.speaker)}（与本案例登记的作者对不上）`}</p>` : '';
    const timingLine = (layer === 'A' || layer === 'B')
      ? `<p class="evidence-meta">时间码：${timing.ok ? esc(timing.text) : `缺失或越界（${esc(timing.reason)}）`}${timing.ok && url ? ` · <a class="evidence-clip" href="${esc(timeAt(url, timing.start))}" target="_blank" rel="noopener noreferrer">播放此片段 ↗</a>` : ''}</p>`
      : '';
    const frame = layer === 'A' && frameLabel(view) ? `<p class="evidence-meta">${esc(frameLabel(view))}</p>` : '';
    const citations = layer === 'C'
      ? `<p class="evidence-meta">独立来源：${(Array.isArray(view.source_ids) ? view.source_ids : []).map(id => sources.get(id)).filter(Boolean).map(source => `<a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(plain(source.short_title) || plain(source.title))} ↗</a> · ${esc(plain(source.author))}`).join('；') || '未登记'}</p>`
      : '';
    const scope = view.verification_scope ? `<p class="evidence-meta">核验范围：${esc(view.verification_scope)}</p>` : '';
    const stamp = verdict === 'verified'
      ? `<p class="evidence-meta">核验于 ${esc(view.checked_at)} · ${esc(methodLabel(view.verified_by))}</p>`
      : `<p class="evidence-meta">核验依据：未提供可追溯的核对记录</p>`;
    return `<div class="evidence-item" data-layer="${esc(layer)}" data-verdict="${esc(verdict)}"><p class="evidence-tag">${esc(meta.tag)} <span class="evidence-verdict">${esc(shown.label)}</span></p><p class="evidence-note">${esc(meta.note)} · ${esc(shown.hint)}</p>${speaker}${timingLine}${frame}${layer === 'B' ? evidenceQuoteHTML(view) : `<p class="evidence-body">${esc(view.text)}</p>`}${citations}${scope}${stamp}${issues.length ? `<p class="evidence-issues">未核实原因：${esc(issues.join('；'))}</p>` : ''}</div>`;
  }
  function videoEvidenceHTML(item, url) {
    const data = item.video_evidence;
    const entries = Array.isArray(data) ? data : Array.isArray(data?.layers) ? data.layers : [];
    const simulated = data?.simulated === true || entries.some(entry => entry && typeof entry === 'object' && entry.simulated === true);
    if (!entries.length && !simulated) return '';
    const body = entries.map(entry => evidenceEntryHTML(item, url, entry, simulated)).join('');
    const banner = simulated ? `<p class="evidence-fixture">模拟夹具，非真实视频研究。此处只用于验证分层显示，不构成任何真实媒体事实或正式核验。</p>` : '';
    return `<section class="case-evidence" aria-label="视频证据分层"><p class="evidence-title">视频证据分层 <span>A 画面观察 · B 摄影者本人言语 · C 专业解释 · D 建议 / 推断</span></p>${banner}${body || '<p class="evidence-note">没有可用的证据条目。</p>'}<p class="evidence-note">“已核验”只覆盖所列时间码、所引来源与所注核验方式；搜索摘要、AI 判断或自称已核验的字段都不算核对过。时间码链接只跳转播放，不写入任何私人学习记录。</p></section>`;
  }
  function caseHTML(gateway, id) {
    const item = gateway.cases.find(c => c.id === id);
    if (!item) return '';
    const url = safeURL(item.url);
    const images = item.display === 'note_media' ? (item.images || []).map(image=>{
      const registered=noteMedia.get(image.media_id);
      return registered ? {src:`/api/learning-note-media/${encodeURIComponent(registered.id)}`,alt:registered.alt,label:image.label || registered.position} : null;
    }).filter(Boolean) : item.display === 'source_remote' ? item.images || []
      : item.display === 'licensed_remote' && item.rights.allowed === true ? [item] : [];
    const mediaURL = value => /^\/api\/learning-note-media\/[a-z0-9-]+$/.test(value) ? value : safeURL(value);
    const media = images.filter(image=>mediaURL(image.src)).map(image=>{
      const dimensions = Number.isInteger(image.width) && Number.isInteger(image.height) ? ` width="${image.width}" height="${image.height}"` : '';
      return `<div class="case-media">${image.label?`<p class="case-media-label">${esc(image.label)}</p>`:''}<div class="case-image"><img src="${esc(mediaURL(image.src))}" alt="${esc(image.alt)}" loading="lazy"${dimensions} referrerpolicy="no-referrer"><span class="case-loading" role="status">正在加载原案例照片…</span><span class="case-load-error" hidden>这张图片暂时无法加载。中文要点仍可阅读，原案例链接在下方。</span></div></div>`;
    }).join('');
    const summary = item.source_summary;
    const clip = item.playback;
    let playback = '';
    if (url && Number.isInteger(clip?.start) && Number.isInteger(clip?.end) && clip.start >= 0 && clip.end > clip.start && clip.end <= 86400) {
      playback = `<a class="case-playback" href="${esc(timeAt(url, clip.start))}" target="_blank" rel="noopener noreferrer">播放出处 ${evidenceTime(clip.start)}–${evidenceTime(clip.end)} ↗</a>`;
    }
    return `<figure class="gateway-case" data-case="${esc(id)}">${media || `<a class="gateway-case-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">打开原站实拍对照 ↗<span>${esc(item.title)}</span></a>`}<figcaption><strong>${esc(item.title)}</strong><span>${esc(item.author)} · ${esc(item.caption)}</span>${summary?`<details class="case-source-summary"><summary>原文要点 · 中文转述</summary><p>${esc(summary.text)}</p><span class="case-source-locator">原文定位：${esc(summary.locator)} · 核对于 ${esc(summary.checked_at)}</span></details>`:''}${playback}${videoEvidenceHTML(item, url)}<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">原案例与图像出处 ↗</a><details><summary>图像使用与核验范围</summary><p>${esc(item.review.detail)}</p><p>${esc(item.rights.statement)} <a href="${esc(safeURL(item.rights.url))}" target="_blank" rel="noopener noreferrer">权利说明 ↗</a></p></details></figcaption></figure>`;
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
      case 'exercise': return `<div class="gateway-exercise"><h3>${esc(block.title)}</h3><p>${esc(block.prompt)}</p>${block.options?.length?`<div class="gateway-choices" role="group" aria-label="${esc(block.title)}">${block.options.map(option=>`<button type="button" data-gw-choice="${esc(block.id)}" data-value="${esc(option)}" aria-pressed="${draft.answers[block.id]===option}">${esc(option)}</button>`).join('')}</div>`:''}<label for="gw-answer-${esc(block.id)}">${esc(block.label || '先记下你的观察（可跳过）')}</label><textarea id="gw-answer-${esc(block.id)}" data-gw-answer="${esc(block.id)}" maxlength="8000" rows="3" placeholder="${esc(block.placeholder || '图中看见了什么？还有什么不能确定？')}">${esc(draft.answers[block.id] || '')}</textarea></div>`;
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
    const gateway = current, draft = getDraft(gateway.id);
    dialog.innerHTML = `<header class="gateway-reader-header"><div><p class="eyebrow">${gateway.kind==='course'?'PHOTO ATLAS · 课程样板':'CONCEPTUAL GATEWAY · 认知入口'}</p><h2 id="gateway-title" tabindex="-1">${esc(gateway.title)}</h2></div><button id="gateway-close" class="close-button" type="button" aria-label="关闭阅读，返回原位置">×</button></header><div class="gateway-scroll"><div class="gateway-reading-layout"><aside class="gateway-outline"><details open><summary>阅读目录</summary><nav aria-label="阅读章节">${gateway.sections.map((section,index)=>`<button type="button" data-gw-section="${esc(section.id)}"><span>${String(index+1).padStart(2,'0')}</span>${esc(section.title)}</button>`).join('')}</nav></details><label for="gateway-switch">切换课程 / 认知入口</label><select id="gateway-switch">${catalog.map(item=>`<option value="${esc(item.id)}"${gateway.id===item.id?' selected':''}>${esc(item.title)}</option>`).join('')}</select></aside><article class="gateway-reading"><div class="gateway-reading-intro"><p class="gateway-byline">${esc(gateway.author)} · ${esc(gateway.reading_depth)}</p><p>${esc(gateway.outcome)}</p><p class="gateway-small">${esc(gateway.prior_knowledge)}</p><p class="gateway-citation">专业依据：${citations(gateway.source_ids.slice(0,3))}</p></div>${gateway.sections.map(section=>`<section class="gateway-chapter" id="gw-${esc(section.id)}" tabindex="-1"><p class="eyebrow">${esc(section.kicker || section.id.toUpperCase())}</p><h2>${esc(section.title)}</h2>${section.blocks.map(block=>blockHTML(block,gateway,draft)).join('')}${section.source_ids?.length?`<p class="gateway-citation">本节依据：${citations(section.source_ids)}</p>`:''}${section.id==='reflect'?selfAssessment(draft):''}${section.id==='sources'?sourceHTML(gateway):''}</section>`).join('')}<footer class="gateway-reading-footer"><p>继续在技能地图里练习</p>${gateway.skill_ids.map(id=>`<button type="button" data-gw-skill="${esc(id)}">${esc(host.skillName(id))} →</button>`).join('')}</footer></article></div></div>`;
    scroll = dialog.querySelector('.gateway-scroll');
    scroll.scrollTop = draft.scroll || 0;
    dialog.querySelectorAll('img').forEach(img=>{
      const loading=img.parentElement.querySelector('.case-loading'), error=img.parentElement.querySelector('.case-load-error');
      img.addEventListener('load',()=>{loading.hidden=true;});
      img.addEventListener('error',()=>{img.hidden=true;loading.hidden=true;error.hidden=false;});
      if(img.complete) {
        loading.hidden=true;
        if(!img.naturalWidth) {img.hidden=true;error.hidden=false;}
      }
    });
    dialog.querySelectorAll('[data-gw-reveal]').forEach(details=>details.addEventListener('toggle',()=>{
      const active = getDraft(gateway.id), id = details.dataset.gwReveal;
      const before = active.revealed.includes(id);
      if (before === details.open) return;
      active.revealed = details.open ? [...active.revealed,id] : active.revealed.filter(value=>value!==id);
      active.dirty=true; remember();
    }));
    document.getElementById('gateway-form').addEventListener('submit', save);
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
    contentSources=new Map((data.learning_content?.sources || []).map(item=>[item.id,item]));
    speechRecords=new Map((data.learning_content?.speech_records || []).map(item=>[item.id,item]));
    dialog=document.getElementById('gateway-dialog');
    const index=document.getElementById('gateway-index');
    index.hidden=!catalog.length;
    const courses=catalog.filter(item=>item.kind==='course'), gateways=catalog.filter(item=>item.kind!=='course');
    const entries=items=>items.map((gateway,i)=>`<button type="button" class="gateway-entry" data-open-gateway="${esc(gateway.id)}"><span class="gateway-index-number">${String(i+1).padStart(2,'0')}</span><span><strong>${esc(gateway.title)}</strong><span>${esc(gateway.question)}</span></span><span aria-hidden="true">↗</span></button>`).join('');
    index.innerHTML=`${courses.length?`<section class="course-index"><div class="section-heading"><div><p class="eyebrow">PHOTO ATLAS · COURSE</p><h2>从现场问题，连续学一章</h2></div><p class="section-note">解释原因、比较代价，再用新照片判断。样板等你试读，暂不批量扩展。</p></div>${entries(courses)}</section>`:''}<div class="section-heading"><div><p class="eyebrow">LEARN TO SEE</p><h2>从一个问题，换一种看法</h2></div><p class="section-note">原有认知入口。能力地图用于检索与记录；短笔记用于回看。</p></div><div class="gateway-index-list">${entries(gateways)}</div>`;
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
  return {init,links,close,openFromURL,onRouteChange:()=>{if(dialog?.open)close(false);},isOpen:()=>!!dialog?.open};
})();
