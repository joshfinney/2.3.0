# Query Transformation LLM Migration Notes

## Scope

This document summarises operational changes required when upgrading from the
deterministic query transformation stack to the new LLM + tool orchestration
flow.

## Key Changes

- **LLM dependency:** `QueryTransformer` now requires an `LLM` instance at
  construction time. `QueryTransformationUnit` injects `Config.llm`, so ensure
  deployment configs still provide a valid LLM.
- **Factory signature:** `QueryTransformerFactory.create_*` helpers now accept
  the LLM instance as the first argument.
- **Metadata schema:** Transformation metadata stored in the pipeline context is
  now LLM-centric (`llm_reasoning`, `tool_invocations`, `final_payload`,
  `raw_responses`). Downstream consumers relying on legacy fields such as
  `transformations_applied` must switch to the new keys.
- **Observability:** Logging includes reasoning snippets and tool counts instead
  of rule identifiers. Update dashboards or alerts that parsed log strings.
- **Harmony defaults:** When `Config.use_harmony_format` is enabled the stage now
  emits multi-message Harmony prompts by default while still honouring the
  legacy template path when the flag is `False`. Add the optional
  `harmony_reasoning_levels['query_transformation']` knob to configuration
  management to tune reasoning depth without affecting other stages.

## Backward Compatibility

- `QueryTransformationResult` retains the same public API; the only addition is
  an internal `confidence_threshold` field used by
  `should_apply_transformation()`.
- If the LLM fails to provide a final response, the system falls back to the
  original query with confidence `0.0`, matching previous graceful degradation
  semantics.

## Recommended Actions

1. **Config audit:** Verify every environment sets `Config.llm`. Absence now
   raises a configuration error when the pipeline initialises.
2. **Monitoring update:** Adapt dashboards to the new metadata schema and
   include tool invocation counts to monitor RapidFuzz usage.
3. **Testing:** Add fixture coverage for multi-iteration tool flows to mirror
   the new behaviour, especially when custom `max_tool_iterations` values are
   used.
4. **Prompt format validation:** Smoke-test both Harmony (default) and legacy
   prompt modes during rollout to ensure downstream pipelines receive the
   expected format per environment configuration.

