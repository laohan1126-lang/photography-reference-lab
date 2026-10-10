# Verification delivery index

The independent report is copied byte-for-byte from the Verifier's own worktree.
Frozen originals under `../acceptance/` also remain byte-identical. The separate
supplemental browser script and its JSON are actual execution evidence; neither
changes the frozen standards. [artifact-hashes.json](artifact-hashes.json) binds
the report, script, raw development-log identity and local screenshot identities.

Screenshots and original public video stills are kept outside Git. Actual local
browser screenshots retained for this delivery:

- [Desktop viewport](<D:/AI PROJECTS/photography-reference-lab-multi-pilot-20261010/.local/multi-pilot/verifier-evidence/success-desktop-browser-viewport.png>)
- [Mobile viewport](<D:/AI PROJECTS/photography-reference-lab-multi-pilot-20261010/.local/multi-pilot/verifier-evidence/success-mobile-browser-viewport.png>)
- [Failure: simulated speech marked verified](<D:/AI PROJECTS/photography-reference-lab-multi-pilot-20261010/.local/multi-pilot/verifier-evidence/failure-simulated-speech-marked-verified.png>)
- [Failure: malformed quote closes the reader](<D:/AI PROJECTS/photography-reference-lab-multi-pilot-20261010/.local/multi-pilot/verifier-evidence/failure-malformed-quote-render.png>)

Four layer-by-layer desktop and four mobile images are in that same ignored
directory. A fresh clone needs the existing legal public-still cache to reproduce
image loading; missing images must remain visible as missing, not invented.

From the candidate root, with the existing Python/Playwright runtime:

```powershell
$env:VERIFIER_TARGET_ROOT = (Get-Location).Path
.venv/Scripts/python.exe -X utf8 -m pytest -q `
  docs/research/multi-agent-pilot-20261010/acceptance/test_video_evidence.py
.venv/Scripts/python.exe -X utf8 -m pytest -q --tb=short tests/test_video_evidence_display.py
Copy-Item -LiteralPath docs/research/multi-agent-pilot-20261010/verification/capture_candidate_evidence.py `
  -Destination .local/multi-pilot/capture_candidate_evidence.py
.venv/Scripts/python.exe -X utf8 .local/multi-pilot/capture_candidate_evidence.py
```

Expected recorded results for this checkpoint: frozen browser suite **5 PASS**;
development suite **77 PASS / 4 FAIL**; supplemental capture exits 0 because it
records both success and **FAIL** observations. That exit is not acceptance.
It uses a disposable database and never opens the owner's learning database.
Development failure stdout is in [development-tests.txt](development-tests.txt).

Do not run another paid CLI call just to replay screenshots. Do not mark the two
remaining defects accepted, discard their tests or present this checkpoint as FULL.
