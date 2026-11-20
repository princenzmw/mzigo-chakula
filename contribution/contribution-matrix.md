# Group Project Contribution Matrix (DSA 3050A)

**Project:** Mzigo Chakula (Kenya Food Price Inflation and Household Affordability, 2007 to 2026)
**Repository:** `princenzmw/mzigo-chakula`
**Group Composition Note:** Two-member group (`Prince Nzamuwe` and `Yizere Denis Derick`). Yizere Denis Derick notified the course lecturer of a medical situation during execution; his framing and review contributions are recorded below.

## Individual Contribution Register

| Group Member | Assigned Role | Tasks Completed | Evidence in Repository (Files, Branches & PRs) |
| --- | --- | --- | --- |
| Prince Nzamuwe | Lead Analyst & BI Architect | Dataset sourcing and audit, 46-column profiling, 4 Power Query M scripts (10 transformations T1 to T10), star schema model and 15 DAX measures, Python QA/DAX validation suite (44 automated tests), 4-page 46-visual Power BI report with native page navigation, 12-page PDF report, 12-slide presentation, PR workflow management | `src/mzigo_chakula/*.py`, `tests/*.py`, `powerquery/*.pq`, `pbip/`, `README.md`, `docs/proposal.pdf`, `docs/dataset-dictionary.csv`, `docs/data-quality-profile.md`, `docs/transformation-log.md`, `docs/model-diagram.png`, `docs/dax-catalogue.md`, `docs/usability-and-insights.md`, `docs/report.md`, `docs/report.pdf`, `slides/presentation.pptx`, `screenshots/`, `output/`, `contribution/contribution-matrix.md`, PRs #1 to #12 |
| Yizere Denis Derick | Group Contributor | Problem framing alignment, stakeholder and operational decision specification, analytical question review, deliverable checklist verification | `README.md` (Problem statement, Business decisions supported, Analytical questions, Contributors) |

## Weekly Submission Traceability

| Checkpoint | Primary Deliverable | Repository Evidence |
| --- | --- | --- |
| Week 1 | Proposal, 46-column dictionary, data quality profile, initial Power BI import screenshot | PR #2, PR #4 (`docs/proposal.pdf`, `docs/dataset-dictionary.csv`, `docs/data-quality-profile.md`, `screenshots/week1-initial-import.png`) |
| Week 2 | 10 Power Query M transforms, dimension CSVs (`dim_markets.csv`, `dim_date.csv`, `dim_commodity.csv`), transformation QA log, Python cleaning card | PR #3, PR #4 (`powerquery/*.pq`, `data/processed/dim_*.csv`, `docs/transformation-log.md`, `screenshots/week2-powerquery-cleaning.png`) |
| Week 3 | 4-table star schema packaged in Tabular Model Definition Language (TMDL) and Power BI Project (PBIP), 15 DAX measures, Model View screenshot, DAX validation card and schema diagram | PR #5, PR #8, PR #9 (`pbip/`, `docs/model-diagram.png`, `screenshots/week3-powerbi-model-view.png`, `screenshots/week3-dax-validation.png`, `docs/dax-catalogue.md`) |
| Week 4 | 4-page Power BI Enhanced Report Format (PBIR) layout (46 visuals, native page navigation, custom theme, full-width tables), 300 DPI PNG screenshots, usability insights | PR #6, PR #8, PR #9, PR #10 (`pbip/mzigo-chakula.Report/`, `screenshots/page1-executive-pulse.png`, `screenshots/page2-county-commodity.png`, `screenshots/page3-trends-diagnostics.png`, `screenshots/page4-decisions-action.png`, `output/page1-executive-pulse.png`, `output/page2-county-commodity.png`, `output/page3-trends-diagnostics.png`, `output/page4-decisions-action.png`, `docs/usability-and-insights.md`) |
| Week 5 | 12-page final PDF report with workflow visuals and Power BI Desktop captures, 12-slide presentation, README, contribution matrix | PR #7, PR #8, PR #9, PR #10 (`docs/report.pdf`, `docs/report.md`, `slides/presentation.pptx`, `README.md`, `contribution/contribution-matrix.md`) |
