---

## IV. Using Ruflo in This Setup

[Ruflo](https://github.com/ruvnet/ruflo) is a multi-agent harness for Claude Code and Codex. In this repo it is useful for coordinating coding, testing, documentation, and review work around the Streamlit meteocean forecasting app.

### Current repo configuration

This repository already includes a project-local MCP configuration in `.mcp.json`:

```json
{
  "mcpServers": {
    "claude-flow": {
      "command": "npx",
      "args": ["-y", "ruflo@latest", "mcp", "start"],
      "autoStart": false
    }
  }
}
```

The server key is still named `claude-flow` for compatibility with the older Claude Flow naming, but it runs `ruflo@latest`. You can leave the name as-is unless you are also updating every local tool reference that expects `claude-flow`.

Because `autoStart` is `false`, the MCP server starts only when the host tool requests it or when you run it manually.

### Prerequisites

- Node.js 18+ with `npx` available.
- Python 3.10+ for the Streamlit app.
- The Python environment from the installation section above.
- Claude Code, Codex, or another MCP-capable coding client.

Check Node from PowerShell:

```powershell
node --version
npx --version
```

### First-time Ruflo setup

From the repository root:

```powershell
npx ruflo@latest init wizard
```

Use the wizard when you want Ruflo to create or refresh its local `.claude/` commands, agents, skills, hooks, and helper files. This repo already has a `.claude/` directory, so review generated changes before committing them.

For a faster non-interactive init:

```powershell
npx ruflo@latest init
```

### Starting the MCP server manually

Most MCP clients can start the server from `.mcp.json`. If you want to verify Ruflo directly:

```powershell
npx.cmd -y ruflo@latest mcp start
```

OBS: Evite rodar comando "npx" pois o powershell está bloqueando o script "npx.ps1". Rode a versão CMD acima.

Keep that terminal open while testing MCP connectivity from your coding client. Stop it with `Ctrl+C`.

### Typical Ruflo workflow for this project

Use Ruflo agents for work that benefits from coordination or memory, then keep the actual app workflow grounded in the existing Python commands.

Good task prompts:

```text
Use Ruflo to inspect the Streamlit meteocean app and propose the smallest safe change for adding a new Prophet model.
```

```text
Use Ruflo to coordinate implementation and tests for feature engineering changes. Preserve the raw XLSX schema contract.
```

```text
Use Ruflo to review the current diff for regressions in forecasting_service, model_loader, and page_template.
```

After agent work, verify locally:

```powershell
cd streamlitapp
pytest -q
streamlit run app/Home.py
```

### Repo-specific guardrails for agents

When asking Ruflo/Claude/Codex agents to work here, include these constraints:

- Do not delete or overwrite existing `prophet_model.json`, `prophet_metadata.json`, or `.pkl` model files.
- Keep model runtime files under `streamlitapp/models/<target_variable>/<trial_name>/`.
- Keep source/reference model artifacts under root `models/` unless intentionally copying them into the deployable app package.
- Preserve the Prophet inference contract: input must include `ds`; output must include `ds`, `yhat`, `yhat_lower`, `yhat_upper`, `target_variable`, `model_name`, and `model_type`.
- Preserve the exogenous feature path: raw XLSX -> `read_raw_xlsx()` -> `engineer_features()` -> `select_and_scale_features()` -> Prophet regressors.
- Run `pytest -q` from `streamlitapp/` after code changes.
- Add or update tests when changing `features/`, `inference/`, or `config/model_registry.py`.

### Suggested agent roles

These roles map well to this repository:

| Role | Best used for |
|---|---|
| Domain agent | Checking meteocean, Prophet, and feature engineering assumptions against `CONTEXT.md` and `references/feature_engineering.ipynb`. |
| Implementation agent | Editing `streamlitapp/src/meteocean_forecast/` and Streamlit pages. |
| Test agent | Updating focused tests under `streamlitapp/tests/`. |
| Review agent | Inspecting diffs for inference regressions, path bugs, and missing tests. |
| Docs agent | Updating `README.md`, `SETUP.md`, `CONTEXT.md`, and ADRs under `docs/adr/`. |

### Useful local context files

Point Ruflo agents at these files before asking for changes:

- `CLAUDE.md` - project goal, model contracts, and agent notes.
- `CONTEXT.md` - domain context for the meteocean app.
- `streamlitapp/pyproject.toml` - package and test configuration.
- `streamlitapp/src/meteocean_forecast/config/model_registry.py` - model discovery and feature-name maps.
- `streamlitapp/src/meteocean_forecast/inference/forecasting_service.py` - forecast orchestration.
- `streamlitapp/src/meteocean_forecast/features/feature_engineering.py` - exogenous feature pipeline.
- `streamlitapp/tests/` - current regression suite.

### Troubleshooting Ruflo

| Symptom | Fix |
|---|---|
| `npx` is not recognized | Install Node.js, reopen the terminal, and rerun `node --version`. |
| MCP tools do not appear | Confirm your client loaded this repo's `.mcp.json`; then run `npx -y ruflo@latest mcp start` manually to check startup errors. |
| Ruflo creates many `.claude/` changes | Review the diff and commit only the commands, agents, or settings you want to keep for this project. |
| Windows shell complains about `bash` | Use `npx ruflo@latest init wizard`; the `curl ... | bash` install path is for POSIX shells. |
| Python imports fail after agent edits | From `streamlitapp/`, rerun `pip install -e .` and then `pytest -q`. |
