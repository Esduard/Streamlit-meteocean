# ADR-0001: Model update UX deferred to a future in-app feature

**Status:** Decided

## Context

When distributing `MeteoceanForecast` as a packaged executable, model files (`prophet_model.json`) live in a `models/` folder next to the executable and are designed to be replaced independently of the app (external runtime resources). A user could in principle manually copy new model files into that folder.

The question arose during PRD preparation: should the packaged app include a UI for updating models (e.g. drag-and-drop a new model file inside the app itself)?

## Decision

Model update UX is **out of scope for the initial packaging PRD**. The packaging task is strictly about producing a reliable, portable executable that runs the existing app. The `models/` folder ships pre-populated; replacing models by hand is acceptable for now.

A future in-app feature will let users drag-and-drop a new model file directly in the Streamlit UI. That feature will be specified in a separate PRD.

## Consequences

- The packaging PRD does not need to specify model update flows, validation of incoming model files, or version management.
- The `models/` folder structure and the `model_registry.py` glob pattern must remain stable so the future drag-and-drop feature can write into it without breaking the loader.
- Anyone reading the packaging PRD and wondering "how do users update models?" should be directed here.
