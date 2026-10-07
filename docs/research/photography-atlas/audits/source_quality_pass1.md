# Photography atlas — source quality audit, pass 1

Date: 2026-10-07. This is a source eligibility, attribution, independence, and access audit. It does not author candidate skills or modify the raw source maps.

## Result

I reviewed metadata for all 125 records in the nine `raw/*_sources.json` maps. The maps currently label 111 Tier A and 14 Tier B; there are no Tier C visual-discovery entries. The 125 records resolve to 122 unique exact URLs, with three repeated-page pairs. Sixteen independence-key values repeat exactly; normalizing names and institutional lineages reveals additional overlaps.

Tier B is the clearest taxonomy defect: only two of its 14 records are actual video landing pages, and neither video was watched. The remaining 12 are written articles, blogs, a museum page, a syllabus, an event listing, or secondary articles pointing to unwatched videos. The brief defines Tier B as professional videos. Move written items to Tier A only if the named author’s professional qualification is established; otherwise retain them in an unranked written-lead/editorial category. Do not label a video watched from its title, chapter list, synopsis, or an article summary.

The source-map `full_text` counts reflect first-pass authors’ reported reading, not this auditor’s independent re-reading. I re-opened 18 risk-selected primary pages/listings. No linked photograph pixels were inspected and no videos were watched. For all other pages, the JSON marks eligibility as metadata-only or limited to the originally recorded read depth.

## Actionable corrections

- Deduplicate these exact URL pairs while retaining topic cross-links: `composition-ukawa-fujiya-jp` / `perspective-ukawa-portrait-composition`; `cosplay-nikon-cosgenic` / `posing-nikon-cosgenic-index`; `perspective-adler-course` / `posing-lindsay-adler-series`. They are one page each, not independent works.
- Normalize repeated teacher/source lineages before confidence scoring: Lindsay Adler (5 records), Peter Hurley (3), Sue Bryce (2), Mayuko Ukawa (3), Gary Small (2), Todd Vorenkamp (2), Mathew Malwitz (2), the PPA Certification Guide (8 chapters), unbylined B&H and Canon editorial pages, Adobe Learn team pages, and overlapping COSPLAY MODE contributors. Full source IDs and lineage rules are in `source_quality_pass1.json`.
- Keep actual authors distinct from their publisher. Named PPA contributors may be separate author lineages; PPA’s eight certification-guide chapters remain one institutional guide. Nikon Cosgenic is one commissioned series family; use the credited lesson author for each claim, not the aggregate series/index page. The number of agents or scope files is never a measure of source independence.
- Five curriculum records use generic `identity` boilerplate. Replace it with the actual institution and only named instructor details documented by the primary page. The Society of Photographers lighting article has an Alison Carlino / Colin Jones byline display conflict; resolve it before treating the article as an individual photographer’s method.
- Treat unbylined B&H, Canon, Tamron, Fuji, and ASC editorial as institutional content. It may help discovery or technical explanation, but it is not an independently credentialed photographer’s method. `posing-bh-eyes-portrait` is a named editor’s compilation: trace attributed practice back to the named photographers before using it as primary evidence.
- Event rules (`field-manga-comiccon-rules`, `field-wcs-rules`) are operational constraints, not photography skill evidence. `cosplay-meihaku-sword` is sword-domain context, not photography pedagogy.
- Film/cinematography and classroom sources (`motion-arri-*`, `motion-asc-*`, `motion-acmi-cinematography`, `motion-hawaii-sequence-coverage`, `motion-sundance-shot-camera`, `motion-hollywood-camerawork-syllabus`, `perspective-okstate-cinematography`, `perspective-norton-framing`) can supply adjacent concepts, but need explicit transfer plus still-portrait evidence before entering core cosplay-photo claims.
- Software-manufacturer tutorials can establish software operation, not aesthetic thresholds or ethics. The Adobe cleanup tutorial covers Photoshop controls; it does not decide whether removing people or scene elements is acceptable.

## Tier B records to reclassify or hold as unranked leads

The 12 non-video IDs are `composition-john-harris-edges`, `composition-todd-vorenkamp-framing`, `composition-malwitz-portrait`, `composition-bh-basics`, `cosplay-note-sutten-motion`, `cosplay-note-kujira-posing`, `cosplay-meihaku-sword`, `motion-dcw-portrait-blur`, `motion-hollywood-camerawork-syllabus`, `posing-animek-coaching`, `post-fstoppers-grimes`, and `post-fstoppers-needham-skin-color`.

The two actual video pages are `posing-chris-orwig-bh-video` and `posing-jerry-ghionis-bh-video`. Chris Orwig’s page confirms the instructor, chapter list, and 1:02:59 runtime; the video itself was not watched. The Jerry Ghionis page open failed, so keep it at search-lead status.

## Metadata updates supported by this audit

- `field-ppa-photo-essay` is not index-only: the public [PPA article](https://www.ppa.com/ppmag/articles/master-the-photo-essay) returns the full text and names Mark Edward Harris. It supports travel/documentary sequence and editing concepts; it is not cosplay-specific.
- `post-adobe-cleanup` is not search-snippet-only: the [Adobe Learn tutorial](https://www.adobe.com/learn/photoshop/web/ai-remove-reflections-distractions) exposes a full transcript and credits Colin Smith. Restrict it to Photoshop operation.
- `curriculum-nyip`: the [public outline](https://www.nyip.edu/courses/professional-photography/lessons) is fully readable; mark the outline itself full-text, while keeping paid lessons unread and evidence scope at curriculum breadth.
- `field-ppa-location-video`: the [PPA landing page](https://www.ppa.com/photovision/watch/location-scouting-and-planning-your-shoot) provides the Ian Spanier synopsis; change index-only to partial page access. The video was not watched.
- `motion-arri-academy-course`: the [ARRI catalog](https://www.arri.com/en/learn/arri-academy/master-classes) identifies Julio Macat ASC and the camera-movement course outline; change index-only to partial page access. The course video remains unwatched and its film context is adjacent-transfer evidence.

The audit also re-opened [Nikon Cosgenic Lesson 3](https://nij.nikon.com/cms/sp/cosgenic/lesson3/), [COSPLAY MODE’s weapon-pose article](https://cosplaymode.net/howto/34432/), [Jeff Jenkins’ first-party profile](https://www.jeffjenkinsphotography.com/), [Lindsay Adler’s course page](https://learn.lindsayadlerphotography.com/product/the-posing-series/), [her hands-guide product page](https://learn.lindsayadlerphotography.com/product/posing-hands-guide/), [Chris Orwig’s video listing](https://www.bhphotovideo.com/explora/videos/photography/portrait-posing-simplified), [Cambridge in Colour’s portrait-lighting text](https://www.cambridgeincolour.com/tutorials/portrait-lighting.htm), [Nikon’s Tamara Lackey article](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/when-center-composition-can-elevate-a-portrait), and Joe Lenton’s [Society of Photographers article](https://thesocieties.net/blog/2023/06/17/how-to-pose-people-for-better-photos/). Public profile/product pages establish only their visible self-description or advertised scope. The WCS rules and B&H balance article did not return usable body/byline text in this audit.

## Boundary and limitations

Only `research/source_quality_pass1.json` and this report were written in the `atlas-audit-quality` worktree. The raw maps and shared application files were not modified. The JSON has a row for every source ID, the recorded metadata, a source-quality disposition, corrected lineage where identified, and reopen notes. Only the listed sample was re-opened; all other first-pass reading remains attributed to the source-map author. No image examples were visually reviewed. No tests, commits, or pushes were run.
