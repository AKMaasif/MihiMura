## What changed

Describe the user workflow, API contract or operational behavior changed by this pull request.

## Safety / privacy impact

- [ ] No change to agricultural safety behavior
- [ ] Confirmation gates still apply to consequential actions
- [ ] Farm/project ownership is enforced server-side
- [ ] No secret or personal farm data was added to source control
- [ ] Sources/freshness/confidence remain visible where required

## Verification

- [ ] `python -m compileall -q app`
- [ ] Offline tests: `for t in tests/*_test.py; do python $t; done` (CI runs these)
- [ ] `python tests/smoke_test.py` (needs a configured Supabase project)
- [ ] `npm run lint && npm run build`
- [ ] Relevant page/workflow tested manually

## Screenshots / demo notes

Add before/after visuals or explain the demonstration path.
