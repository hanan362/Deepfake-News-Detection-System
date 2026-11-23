# Problem statement

## The problem

A reader who meets a news item online has few ways to judge it. Automated detectors could help, but three weaknesses make the tools that exist today hard to use responsibly.

1. **Scores that do not transfer.** A classifier can score above 97% on articles from its own collection and still be close to chance on other data. This project measured exactly that: 0.973 accuracy in-collection and 0.552 on LIAR2 for the same model. A tool that shows only the first number overstates what it knows.
2. **Verdicts without limits.** Detectors for generated images and manipulated media lose reliability after compression, resizing and when generators change (Wang et al., 2020; Corvi et al., 2023; Li et al., 2025). A single "fake" or "real" label hides this.
3. **Fragmented checks.** Text, images, video, context and evidence are studied separately. A reader has no single place that applies the available checks, keeps a record, and states which checks were not possible.

## The question

Can a complete, maintainable platform be built that applies the checks that are currently defensible, explains them exactly where that is possible, refuses where a check is not defensible, and makes its own measured limits visible to the person using it?

## What counts as a solution

| Requirement | Meaning here |
|---|---|
| Real inference | Every shown result comes from a real model or measurement, never from a random or hard-coded value |
| Honest abstention | The system can answer *Unverified* or *Indicators Only* and says why |
| Visible limits | Each result page says in plain words what the result does not mean, and the administrators' Models page shows the measured external evaluation |
| Faithful explanation | An explanation must be exact for the model that produced it, and a test must check that |
| Complete workflow | Accounts, history, reports, feedback, administration and deployment files exist, not only a notebook |
| Traceable claims | Every number in the documents comes from a saved file or a test run |

## What this project does not claim to solve

It does not decide whether a story is true. It does not detect AI-generated or edited images. It does not analyse video, check an image against its headline or retrieve evidence in this build. These are described as future work.
