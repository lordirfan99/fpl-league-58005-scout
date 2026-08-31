# Frontend QA

Audit date: 2026-08-31

## Scope and result

The Next.js 16 dashboard was tested as a production build on desktop and mobile Chromium. TypeScript checking and the production build pass. The Playwright suite reports 17 passing scenarios and one intentional desktop skip for a mobile-only assertion.

| Area | Evidence | Result |
|---|---|---|
| Critical routes | Dashboard, My Team, Assistant, Planner, League, Journal, V5 Lab and supporting routes render from the production server | PASS |
| Gameweek navigation | Archived weeks route to journal detail; live week routes to My Team; planning week routes to Assistant; later weeks route to Planner with `?gw=` | PASS |
| Requested/returned GW state | A provisional league week can fall back only on 404/409 and displays both requested and finalized archive GW | PASS |
| Error honesty | Unknown API errors propagate to the route boundary instead of silently walking backward | PASS |
| Journal | Season index and GW1 archive render and remain downloadable | PASS |
| Player artwork | Direct image attempt plus shirt, badge and initial fallbacks; no Next image-proxy 403 in the clean run | PASS |
| Responsive shell | Mobile navigation opens and critical controls remain reachable | PASS |
| Browser console | No unexpected console errors in the automated critical flows | PASS |

## UX findings retained as non-blocking work

- `/league` and `/compare` embed approximately 10.3 MB of HTML at the observed production revision. This is functional but creates a material mobile performance risk (AUD-008).
- Accessibility has interaction coverage but not a complete WCAG audit with screen readers and contrast tooling.
- The journal makes archive/live/planning state explicit, but the calendar will become denser as all 38 weeks accumulate; periodic usability testing is recommended.

## Verdict

The external production run additionally found Netlify's injected badge intercepting the mobile `More` control. A CSS guard now makes that badge pointer-transparent. No known P0/P1 frontend defect remains; the frontend release gate is **PASS after the final deployed rerun**, with performance and full accessibility depth retained as P2 follow-up work.
