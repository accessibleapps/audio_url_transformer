# Goal

Add bounded public-wrapper compatibility coverage in accessibleapps/audio_url_transformer while preserving Python >=3.7, URL/result contracts, dependencies and consumers.

# State

- Existing draft PR #3: https://github.com/accessibleapps/audio_url_transformer/pull/3, originally published feature tip 7f1c218782c03d1387420c6ff8f02a94b5de3ac1. Fresh default remains daa2c03a07977a5712cda0700ed7ebb58853b852. Actions enabled=true verified read-only; no settings changed.
- CI amendment is isolated in worktrees/audio-url-transformer-ci, branch repair/task6-audio-url-transformer-ci. Original local/published feature tips are preserved separately in archive/task6-audio-url-ci-local and archive/task6-audio-url-ci-published; original feature worktree and clean canonical remain untouched.
- Smallest CI slice: one 44-line Linux workflow running the existing full offline pytest suite and Hatchling package build on Python 3.7 and 3.13, plus six-line monthly action-pin maintenance and this existing note refresh. Python >=3.7/dependencies/source/tests remain unchanged; no tracked lock exists or is added. Runner resolves declared dependencies/test extra rather than claiming locked installs.
- Existing tests/conftest.py blocks socket connects/DNS; canned media fixtures and FakeYoutubeDL supply extraction results. The direct-URL child-process test makes no network request. Live smoke.py is outside pytest and never invoked. No secret/service integration or model call.
- Ubuntu 22.04 plus pinned setup-python supplies the actual declared 3.7 floor (official runtime catalog provides 3.7.17); uv 0.8.8 has no managed 3.7 entry. Python 3.13 covers the existing feature-test runtime. Actions pins verified from official tag refs; workflow uses contents:read, no persisted checkout credentials, bounded timeout/cancellation. No local full CI run.
- Authored workflow passed actionlint v1.7.12 and offline zizmor v1.31.1 (no findings); diff whitespace check passes. Product source, all existing tests and both manifests compare identical to original feature tip. Hosted results and actual Claude review remain pending final publication.

## Historical initial feature evidence

- Authenticated GitHub identity: ctoth; exact repository accessibleapps/audio_url_transformer, admin/push access, default master. Complete paginated open-PR response: zero.
- Canonical checkout C:/Users/Q/code/audio_url_transformer was clean (tracked, staged and all untracked), master at daa2c03a07977a5712cda0700ed7ebb58853b852, upstream origin/master with 0/0 divergence. Its only registered worktree was canonical. No existing work was moved or overwritten.
- Fresh ls-remote and fetch agree on master daa2c03a07977a5712cda0700ed7ebb58853b852. New branch modernize/task6-audio_url_transformer was created directly in the approved workspace worktrees/audio_url_transformer after checking absence.
- Read global AGENTS.md and the Accessible Apps repository-ownership skill. No applicable ancestor or repository/nested AGENTS.md, CLAUDE.md, agent notes or .agents/skills were found. No active Git hooks or core.hooksPath configuration were found.
- Implemented exactly two characterization tests, 33 added lines in tests/test_resolve_info.py. The direct-link test fails if the wrapper initializes an extractor and checks the existing uppercase-extension/query/expiry result. The fixture-based extraction test checks initialization from None, explicit audio/webm capability selection of rendition 251, and extraction with download=False/process=False.
- Focused result: `python -m pytest tests/test_resolve_info.py` passed all 34 tests in 1.63 s on Python 3.13.6 / pytest 9.0.1.
- Authorized local full result: `python -m pytest` passed all 38 tests in 2.20 s, collecting both configured test files. Existing conftest.py blocks socket connections. No live smoke requests were run.
- `git diff --check` passed. Reviewed complete source/test diff and note: only task test coverage and this note are included; no secrets, private data, signing keys or unrelated changes were authored. Canonical checkout was rechecked clean at original HEAD; the only new registered worktree is the assigned isolated one.

# Initial decisions and why (historical)

- Smallest change: approximately 30-40 test lines in existing tests/test_resolve_info.py, plus this required living note. Characterize the public AudioURLTransformer.resolve_info direct-link fast path and lazy extractor initialization with client capability forwarding, using existing fake_ydl and youtube_vod_no_format_18 fixtures. No source defect fix or cleanup is justified by the inspected fixtures, so this is coverage only; no fabricated failing regression.
- Source evidence: audio_url_transformer/audio_url_transformer.py resolve_info chooses whether to call ensure_youtube_dl, then passes URL/capabilities/ydl to resolve.resolve_info. Existing test_transformer_method_uses_its_youtube_dl presets an extractor and tests only legacy AAC capabilities. Existing direct-audio test calls the module function rather than the public class wrapper.
- Owner: exact authenticated accessibleapps remote; audio_url_transformer is absent from accessible_apps_topology.json, so no topology membership is asserted or changed. Chicken Nugget requirements.txt:35 declares this dependency and chicken_nugget/interface.py:692 invokes its legacy transform method; consumers remain untouched.
- Test authority: pyproject.toml declares test=[pytest], testpaths=[tests], pythonpath=[.]. Exact focused invocation: python -m pytest tests/test_resolve_info.py; full configured repository suite: python -m pytest. These are derived from the actual pytest configuration, not claimed as README-documented commands. Parent explicitly authorized one local full run because no hosted test CI exists; the only GitHub workflow is dynamic/dependabot/update-graph. The separate smoke.py explicitly uses live services and is excluded from pytest; it will not be run.
- No dependency update, resolver, lock refresh, network media requests, extra workflow or security setting changes. Initial sandbox Git ownership checks required the normal approved runtime as Q; no safe.directory change was made.

# Historical initial surprises

- Local Python 3.13.6 has pytest and requests but not yt_dlp. Existing fake extractor patterns allow deterministic wrapper testing without installing or contacting yt_dlp.

# Next step

Return the complete feature-derived CI amendment and exact local head for coordinator review before publication. Final published head requires actual Claude review and green hosted jobs before merge. Keep the existing PR draft and preserve original worktrees/refs. No model call, local full CI, merge, settings/description edit or release is authorized here.
