# Documentation index

This folder holds the documentation of the Deepfake News Detection System. The table maps the 26 items of the project specification (section 19) to files. The documents are plain Markdown with Mermaid diagrams, so they convert to Word or PDF with a tool such as Pandoc, in the order of the table below.

| # | Item | File |
|---|---|---|
| 1 | Project abstract | [technical_documentation/project_abstract.md](technical_documentation/project_abstract.md) |
| 2 | Introduction | [technical_documentation/introduction.md](technical_documentation/introduction.md) |
| 3 | Problem statement | [technical_documentation/problem_statement.md](technical_documentation/problem_statement.md) |
| 4 | Objectives | [technical_documentation/objectives.md](technical_documentation/objectives.md) |
| 5 | Scope | [technical_documentation/scope.md](technical_documentation/scope.md) |
| 6 | Literature review | [research/literature_review.md](research/literature_review.md) (with the four member paper analyses and the comparative analysis) |
| 7 | Research gap | [research/research_gap.md](research/research_gap.md) |
| 8 | Proposed methodology | [research/research_methodology.md](research/research_methodology.md), [research/proposed_contribution.md](research/proposed_contribution.md), [research/feasibility_analysis.md](research/feasibility_analysis.md) |
| 9 | Requirements specification | [technical_documentation/requirements_specification.md](technical_documentation/requirements_specification.md) |
| 10 | System architecture | [architecture/architecture.md](architecture/architecture.md) |
| 11 | ER diagram | [diagrams/er_diagram.md](diagrams/er_diagram.md) |
| 12 | Use case diagram | [diagrams/use_case_diagram.md](diagrams/use_case_diagram.md) |
| 13 | Data flow diagram | [diagrams/data_flow_diagram.md](diagrams/data_flow_diagram.md) |
| 14 | Activity diagrams | [diagrams/activity_diagrams.md](diagrams/activity_diagrams.md) |
| 15 | Sequence diagrams | [diagrams/sequence_diagrams.md](diagrams/sequence_diagrams.md) |
| 16 | Database documentation | [technical_documentation/database_documentation.md](technical_documentation/database_documentation.md) |
| 17 | API documentation | [api/api_reference.md](api/api_reference.md), [api/openapi.json](api/openapi.json) |
| 18 | AI model documentation | [technical_documentation/ai_model_documentation.md](technical_documentation/ai_model_documentation.md) |
| 19 | Testing report | [technical_documentation/testing_report.md](technical_documentation/testing_report.md) |
| 20 | Results and discussion | [technical_documentation/results_and_discussion.md](technical_documentation/results_and_discussion.md) |
| 21 | Limitations | [technical_documentation/limitations.md](technical_documentation/limitations.md) |
| 22 | Future work | [technical_documentation/future_work.md](technical_documentation/future_work.md) |
| 23 | Conclusion | [technical_documentation/conclusion.md](technical_documentation/conclusion.md) |
| 24 | References | [research/references.md](research/references.md) |
| 25 | User manual | [user_manual/user_manual.md](user_manual/user_manual.md) |
| 26 | Installation manual | [user_manual/installation_manual.md](user_manual/installation_manual.md) |

## Project management

| Document | Content |
|---|---|
| [TEAM.md](TEAM.md) | The four member roles, shared duties and working agreements |
| [ROADMAP.md](ROADMAP.md) | 12 months with weekly deliverables, dependencies, risks and completion criteria |
| [ACCEPTANCE_CHECKLIST.md](ACCEPTANCE_CHECKLIST.md) | The acceptance criteria of the specification, with evidence |

## Research folder

[research/README.md](research/README.md) explains how the 40 papers were chosen and verified, and lists the files: the four member paper analyses (`member1_*` to `member4_*`), `references.md`, `literature_review.md`, `comparative_analysis.md`, `research_gap.md`, `proposed_contribution.md`, `research_methodology.md` and `feasibility_analysis.md`.

## Screenshots

`screenshots/` holds pictures of the real interface, produced by `SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts` from the `frontend` folder. The user manual uses them. They show test data, not a real user.

## Suggested order for a report

1. Abstract, introduction, problem statement, objectives, scope
2. Literature review, research gap, methodology, feasibility
3. Requirements, architecture, diagrams, database, API, AI models
4. Testing report, results and discussion, limitations, future work, conclusion
5. References
6. Appendices: user manual, installation manual, team plan, roadmap, acceptance checklist

## Keeping the documents true

One document is checked by a test: `api/openapi.json` is compared with the live application by `test_committed_openapi_matches_the_application`, and `scripts/maintenance/export_openapi.py` refreshes it. The application itself reads the model numbers it shows from the saved evaluation file, but the copies of those numbers in these Markdown files were typed in from the file at the time of writing. After retraining, check them against `ai_models/evaluation/results/text_baseline_en_metrics.json` (`python scripts/evaluation/print_text_metrics.py`). The database tables in `technical_documentation/database_documentation.md` were produced from the models once and are not refreshed automatically. Everything else is written by hand and must be updated with the code.
