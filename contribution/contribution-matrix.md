# Group Project Contribution Matrix (DSA 3050A)

**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability Intelligence, 2007 to 2026)
**Repository:** `princenzmw/mzigo-chakula`
**Group Composition Note:** Two-member group (`Prince Nzamuwe` and `Yizere Denis Derick`). Denis informed the course lecturer of a medical situation during execution; his framing and review contributions are recorded transparently below.

## Individual Contribution Register

| Group Member | Assigned Role | Tasks Completed | Evidence in Repository (Files, Branches & PRs) |
| --- | --- | --- | --- |
| Prince Nzamuwe | Lead Analyst & BI Architect | Dataset sourcing & audit, 46-column profiling, 10 Power Query M scripts, star schema model & 15 DAX measures, Python QA/DAX validation suite (36+ tests), 4-page PBIR dashboard design, 12-page PDF report, 12-slide presentation, PR workflow management | `src/mzigo_chakula/*.py`, `tests/*.py`, `powerquery/*.pq`, `pbip/`, `docs/proposal.pdf`, `docs/transformation-log.md`, `docs/dax-catalogue.md`, `docs/report.pdf`, `slides/presentation.pptx`, PRs #1 to #8 |
| Yizere Denis Derick | Group Contributor | Theme 10 problem framing alignment, stakeholder & operational decision specification, analytical question review, academic deliverable checklist verification | `README.md` (Problem framing, Stakeholders, Decisions, Questions, Contributors) |

## Weekly Submission Traceability

| Checkpoint | Primary Deliverable | Repository Evidence |
| --- | --- | --- |
| Week 1 | Proposal, 46-column dictionary, profile, initial Power BI import screenshot | PR #2, PR #4 (`docs/proposal.pdf`, `docs/dataset-dictionary.csv`, `screenshots/week1-initial-import.png`) |
| Week 2 | 10 Power Query M transforms, dimension CSVs, transformation QA log, cleaning visual | PR #3, PR #4 (`powerquery/*.pq`, `data/processed/*.csv`, `docs/transformation-log.md`, `screenshots/week2-powerquery-cleaning.png`) |
| Week 3 | 4-table star schema TMDL/PBIP, 15 DAX measures, model view, DAX validation & diagram | PR #5, PR #8 (`pbip/`, `docs/model-diagram.png`, `screenshots/week3-powerbi-model-view.png`, `screenshots/week3-dax-validation.png`, `docs/dax-catalogue.md`) |
| Week 4 | 4-page PBIR report layout (44 visuals, custom theme), 300 DPI PNGs, usability insights | PR #6, PR #8 (`pbip/mzigo-chakula.Report/`, `screenshots/page1..4.png`, `output/page1..4.png`, `docs/usability-and-insights.md`) |
| Week 5 | 12-page final PDF report with step screenshots, 12-slide presentation, README, contribution log | PR #7, PR #8 (`docs/report.pdf`, `slides/presentation.pptx`, `README.md`, `contribution/contribution-matrix.md`) |
