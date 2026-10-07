# Source quality final audit

Snapshot: 2026-10-08, captured from the canonical atlas files listed by SHA-256 in `source_quality_final.json`. This is a bounded audit, not blanket verification of all professional claims.

## Result

The snapshot contains 14 domains, 71 modules, 247 skill cards, 205 source records, and 247 evidence rows. All 205 source records contain the required metadata fields and have unique exact URLs. There are no Tier B records. The 49 partial, index-only, or blocked/unranked records remain ineligible; no formal evidence row references an ineligible or non-full-text record.

There are 109 high-confidence rows. Every one references at least two distinct `independence_key` values. Repeated Adobe pages remain one Adobe lineage; repeated PPA chapters remain one PPA lineage. This confirms source-family counting metadata, not the detailed semantic support of every high-confidence claim.

## Actual pages reopened in this pass

- [DuChemin, “Is It Any Good?”](https://davidduchemin.com/2018/07/is-it-any-good/) and [his about page](https://davidduchemin.com/about-david/): the text supports intent-first review and exploration when intent is still unclear; his first-party bio identifies his photography, writing, books, and workshop activity.
- [McNally, “More From Corregidor”](https://joemcnally.com/2008/02/19/more-from-corregidor/) and [his official bio](https://joemcnally.com/about/): the post describes one ballerina lighting example, including blue open shade, a bright/reverse-gradient backdrop, and flagging/feathering spill. The images were not independently reviewed.
- [Muncy’s Adorama cosplay portrait article](https://www.adorama.com/alc/c-s-muncy-on-how-to-shoot-cosplay-portraits/): lines 147–155 describe securing permission for one AwesomeCon setup and surveying a spot that would not impede crowd flow. The candidate correctly treats this as a limited case, not a China venue rule.
- [Nikon Cosgenic Lesson 5](https://nij.nikon.com/cms/sp/cosgenic/lesson5/): the exact lesson supports group placement/variation and credits 井上依子 (YOL) and 渡邉 (yakul). This is distinct from the about/index page.
- [Neil van Niekerk on manual flash controls](https://neilvn.com/tangents/practical-tutorial-manual-flash-exposure/), [David X. Tejada at Nikon](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/lighting-with-two-speedlights), and [Paul Van Allen at Nikon](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/photographing-still-life-subjects-using-flash): the pages support test-shot manual-power adjustment and the normal-sync flash/ambient distinction, with the Nikon system/HSS boundaries stated.
- [PPA Module 4B](https://wiki.ppa.com/books/photography-certification-guide/page/module-4b-utilizing-the-exposure-triangle-to-create-images) and [Canon’s portrait settings article by Laura Tillinghast](https://www.usa.canon.com/learning/training-articles/training-articles-list/camera-settings-for-stunning-portraits): examples support aperture/shutter trade-offs; Canon directly supports raising ISO for low-light/moving portraits and notes noise. PPA line 143 specifically names ISO as an exposure adjustment.
- [Nikon’s histogram guide](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/learning-how-to-use-your-cameras-histogram), [Tom Bol’s aurora example](https://www.nikonusa.com/learn-and-explore/c/tips-and-techniques/awesome-skies-tips-and-techniques-for-photographing-the-northern-lights), and [Canon’s snow/highlight guide](https://www.usa.canon.com/learning/training-articles/training-articles-list/photographing-snow): the new RGB-histogram skill is appropriately medium/project-adaptation and limits feature availability to supported camera models; the aurora case is not treated as cosplay-specific proof.
- [Mark Rigsby’s convention photography article](https://www.spekture.com/how-to-improve-your-cosplay-photography-in-4-easy-steps/): lines 37–45 support a nearby low-clutter location, asking the subject to move, and continuing conversation while walking. The source does not establish Chinese venue permissions or crowd-control rules; the candidate stays medium and adds authorization as a project constraint.

The complete page-by-page locations and findings are recorded in the JSON artifact. No image pixels or videos were inspected.

## Actionable follow-up

1. In `field-test-failure-hypothesis`, widen the McNally locator to lines 74–80; the current lines 78–84 omit the reported setup error and cause at lines 76–77. Keep the skill medium/project-adaptation.
2. In `lightgap-exposure-aperture-iso-tradeoff`, add PPA 4B lines 140–143 to its locator; the current PPA locator points only to lines 84–114 and misses the explicit ISO passage at line 143. The canonical skill now correctly keeps aperture and shutter fixed while testing ISO.
3. Record explicit discovery/exclusion dispositions for `cosplay-c12-subject-set-overlap` and `post-skin-dodge-burn-scope`. Both are absent from the formal evidence matrix, which is the cautious outcome, but neither has an explicit `excluded_skills` decision in the current snapshot.

## Prior PASS2 corrections checked against this snapshot

Cosplay C02/C08/C14 resolve through canonical merges; C07 uses exact Nikon Lesson 11 and a separate COSPLAY MODE lineage; C13 uses exact Lesson 5 and remains medium. Frequency separation is medium and cites PHLEARN only for Aaron Nace’s method. The video-only/project-adaptation corrections remain medium; duplicate ASC passage citations do not create independent sources. C01 has an explicit atomicity exclusion. Two old candidates noted above remain absent without explicit dispositions.

The audit deliberately does not claim that every source is professionally qualified or that every high-confidence capability was re-read. Full snapshot hashes, metadata checks, old-correction reconciliation, and the exact reopened locations are in [source_quality_final.json](source_quality_final.json).
