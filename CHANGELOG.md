# Changelog

## 0.4.0 — 2026-11-17
- Added priority-based reverse and production-capacity modes to `/capacity/reverse`.
- Made total demand mandatory; removed the silent 1,100-set planner default.
- Added day/week/month horizons (3/18/75 shifts by default), configurable working days, and longer horizon support.
- Added II → III → I engagement escalation, I/II/III timing, 90% II/III and 85% I ceilings, and I-shift Curing/Coding priority.
- Extended the shared forward simulator with per-shift machine schedules and continuous WIP validation.
- Report actual shifts and working days required, remaining demand, and capacity shortfall.

## 0.1.0 — 2026-11-16
- Initial public preview.
- Added portable Agent Skill entry point and intent router.
- Added TOC, Logical Thinking Process, flow, manufacturing, project, and
  decision reference guides.
- Added independent standard-library flow simulator, templates, examples,
  tests, attribution, and licence notes.
