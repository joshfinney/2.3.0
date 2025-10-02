# Query Transformation System – LLM Upgrade Summary

## Executive Overview

The query transformation stage now leverages an LLM-orchestrated workflow with
explicit RapidFuzz-powered tool calls. The upgrade removes legacy rule-based
normalisation while preserving intent, latency budgets, and the existing
pipeline contract. Transformations are now traceable through structured LLM
metadata stored in the `PipelineContext`.

## Implementation Highlights

- **Core Logic** – `pandasai/helpers/query_transformer.py`
  - Replaced deterministic pipeline with iterative LLM calls and tool handling.
  - Added audit-friendly metadata, configurable confidence threshold, and
    bounded tool iterations.
- **Prompting** – `pandasai/pandasai/prompts/query_transformation_prompt.py`
  with `templates/query_transformation.tmpl`
  - Defines tool catalogue, response schema, and context injection rules.
  - Provides Harmony-format multi-message prompts by default with automatic
    fallback to the legacy single prompt when configured.
- **Pipeline Integration** – `pandasai/pandasai/pipelines/chat/query_transformation.py`
  - Injects configured LLM, caches transformers per `(mode, llm)` pair, and
    logs reasoning + tool usage.
- **Examples & Docs** – Updated `query_transformation_example.py` and added
  `QUERY_TRANSFORMATION_LLM_DESIGN_NOTE.md` plus
  `QUERY_TRANSFORMATION_MIGRATION_NOTES.md`.
- **Testing** – New unit suite `pandasai/tests/unit_tests/helpers/test_query_transformer_llm.py`
  covers final-only flows, tool invocation loops, and graceful fallbacks.

## Behavioural Changes

- LLM responses control query classification, intent labels, and confidence; no
  regex heuristics remain.
- Tool invocations are mandatory for schema disambiguation; RapidFuzz is called
  via the orchestrator with difflib fallback when unavailable.
- `QueryTransformationResult` now stores `confidence_threshold` for accurate
  `should_apply_transformation()` decisions and enriches metadata with
  `llm_reasoning`, `tool_invocations`, `final_payload`, and raw responses.
- Pipeline context persists the above metadata, enabling downstream telemetry
  and debugging.

## Configuration Surface

- Factory helpers accept the LLM instance and expose the following knobs:
  - `confidence_threshold` (float, default 0.7)
  - `max_tool_iterations` (int, default per mode)
  - `max_candidates` (int, cap on schema inventory)
- Modes retain their previous semantics but now map to tool iteration limits:
  - `conservative`: threshold 0.9, 1 tool iteration
  - `default`: threshold 0.7, 2 iterations
  - `aggressive`: threshold 0.5, 3 iterations

## Observability & Safety

- Each run logs query type, intent, confidence, reasoning, and tool counts.
- Stored metadata redacts sensitive tool arguments (query text, column lists)
  while capturing outputs for audit trails.
- Missing or malformed LLM responses trigger graceful degradation to the
  original query with confidence `0.0`.

## Testing & Quality

- Unit tests validate LLM orchestration, RapidFuzz integration, and fallback
  behaviour. Tests leverage stub LLMs and patched RapidFuzz hooks for
  determinism.
- Examples switched to deterministic `FakeLLM` outputs for local execution.

## Next Steps

- Monitor tool invocation telemetry to tune column inventory limits.
- Extend the prompt catalogue with additional tools (e.g., aggregation hints)
  when new downstream requirements emerge.

