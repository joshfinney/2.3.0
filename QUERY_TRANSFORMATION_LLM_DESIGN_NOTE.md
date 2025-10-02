# Query Transformation LLM Integration – Design Note

## Overview

The query transformation stage now uses an LLM-driven planner to optimise user
questions before they reach downstream pipeline logic. The LLM is prompted with
explicit tool definitions and can invoke RapidFuzz-backed fuzzy matching to map
ambiguous user tokens to dataframe schema elements. The previous deterministic
classification / normalization stack has been removed; intent preservation and
confidence are delegated to the LLM with strict schema validation in Python.

## Objectives

- Preserve existing pipeline contracts (`QueryTransformationResult`,
  `QueryTransformationUnit`) while upgrading their implementation.
- Provide observable, auditable traces of all LLM interactions and tool calls.
- Keep latency predictable through bounded tool iterations and capped column
  inventories.

## Architecture

1. **Prompt Template** (`pandasai/pandasai/prompts/templates/query_transformation.tmpl`)
   - Defines role, objectives, response schema, and available tools.
   - Enumerates query types and intent labels expected by downstream systems.
   - Injects context metadata (column inventory, dataframe count, tool history).
   - Mirrors the Harmony prompt surface for environments that opt into the
     legacy single-message format.

2. **QueryTransformer** (`pandasai/pandasai/helpers/query_transformer.py`)
   - Orchestrates iterative LLM calls with bounded tool invocations.
   - Executes RapidFuzz similarity search (with difflib fallback) and redacts
     sensitive inputs in stored metadata.
   - Builds `QueryTransformationResult` with sanitized audit payloads and
     configurable confidence thresholds.

3. **Pipeline Integration** (`pandasai/pandasai/pipelines/chat/query_transformation.py`)
   - Caches transformers per `(mode, llm)` pair for reuse.
   - Logs reasoning snippets, tool counts, and persists LLM traces in the
      `PipelineContext` for downstream telemetry.
   - Seeds `current_user_query` so Harmony-enabled LLMs receive the current turn
     while preserving the legacy prompt when `use_harmony_format=False`.

## Tool Contract

- **rapidfuzz_similarity** – expects `query` and `choices`, optional `limit`
  and `scorer`. Returns `{engine, matches[]}`. Automatically redacts raw inputs
  in persisted metadata while giving the LLM access to full context.
- Additional tools can be added by extending `_execute_tool` and the prompt
  catalogue without altering the pipeline surface area.

## Resiliency & Safety

- Invalid or missing final responses degrade gracefully to the original query
  with zero confidence.
- Tool executions are capped by `max_tool_iterations`; prompts embed the limit
  to set LLM expectations.
- Metadata captures raw LLM responses, final payload, and redacted tool inputs
  for audit purposes.

## Configuration Surface

- Modes (`default`, `conservative`, `aggressive`) map to confidence thresholds
  and tool-iteration budgets.
- `QueryTransformerFactory.create_from_config` exposes
  `confidence_threshold`, `max_tool_iterations`, and `max_candidates` knobs for
  fine tuning.

## Testing Strategy

- Unit tests cover direct LLM final responses, explicit tool-call flows, and
  graceful fallback scenarios.
- RapidFuzz integration is validated via patched mocks to guarantee the
  similarity engine is invoked when requested by the LLM.

