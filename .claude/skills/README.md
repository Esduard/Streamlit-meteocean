# .claude/skills — Index

Skills are markdown files that give the agent domain knowledge or procedural instructions for specific tasks in this project.

---

## Procedural Skills
*(These tell the agent **how** to do something.)*

| File | Trigger | Purpose |
|---|---|---|
| [explore-dataset.md](explore-dataset.md) | Any `.xlsx`, `.csv`, `.xls` file encountered for the first time | Profile columns, infer semantics, create a dataset reference skill |
| [architecture-audit.md](architecture-audit.md) | "audit architecture", "check layer violations", or before any cross-layer refactor | Verify import-direction rules across domain/features/config/inference/app; produce findings table |
| [solid-check.md](solid-check.md) | "check SOLID", "review for clean code", or when reviewing a diff that adds a class/service | Audit file or diff for SRP/OCP/LSP/ISP/DIP violations mapped to specific codebase patterns |
| [add-model-adapter.md](add-model-adapter.md) | "add a new model", "integrate LSTM/XGBoost/ARIMA", or any new model family work | Step-by-step OCP-safe extension: new adapter file + two extension points only, no existing code modified |

---

## Dataset Reference Skills
*(These tell the agent **what** a specific dataset looks like — column names, types, units, quality notes.)*

*No dataset references yet. They will be created automatically when the `explore-dataset` skill runs on a new file.*

| File | Domain | Source file(s) | Time range |
|---|---|---|---|
| *(none yet)* | — | — | — |

---

## Templates
*(Copy these when creating a new skill manually.)*

| File | Use for |
|---|---|
| [_dataset-reference-template.md](_dataset-reference-template.md) | New dataset reference skills |

---

## How to add a new dataset reference

1. Drop the `.xlsx` or `.csv` file into the project.
2. Tell the agent: *"Explore `path/to/file.xlsx` and create a dataset reference."*
3. The agent will run the `explore-dataset` skill and write a new `dataset-<slug>.md` here.
4. Update the **Dataset Reference Skills** table above.
