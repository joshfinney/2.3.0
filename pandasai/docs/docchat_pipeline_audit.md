# DocChat Pipeline Audit

## High-Level Architecture
- The DocChat experience is built on top of the generic `Pipeline` engine, which chains logic units and shares a `PipelineContext` across stages. Each stage returns a `LogicUnitOutput`, allowing metadata logging and short-circuiting on errors. 【F:pandasai/pandasai/pipelines/pipeline.py†L1-L134】
- The orchestration entry point is `GenerateChatPipeline`, which wires together both the code-generation and code-execution pipelines, an optional judge, and the error-correction sub-pipeline. 【F:pandasai/pandasai/pipelines/chat/generate_chat_pipeline.py†L1-L196】

## Nominal Flow
1. **Input preparation** – `run`/`run_generate_code`/`run_execute_code` attach conversation metadata, reset intermediates, and seed the memory before executing pipeline steps. 【F:pandasai/pandasai/pipelines/chat/generate_chat_pipeline.py†L97-L191】
2. **Validation and cache** – `ValidatePipelineInput`, `CacheLookup`, and `CachePopulation` guard and reuse previous results (not shown here, but part of the configured steps). 【F:pandasai/pandasai/pipelines/chat/generate_chat_pipeline.py†L44-L74】
3. **Prompt generation** – `PromptGeneration` selects the right prompt template (SQL vs. pure Python) and logs it. 【F:pandasai/pandasai/pipelines/chat/prompt_generation.py†L1-L56】
4. **Code generation** – `CodeGenerator` calls the configured LLM, preserves the generated code on the context, and emits telemetry. 【F:pandasai/pandasai/pipelines/chat/code_generator.py†L1-L46】
5. **Code cleaning** – `CodeCleaning` validates safety, adds chart persistence hooks, and injects extra dependencies; on failure it delegates to error correction if configured. 【F:pandasai/pandasai/pipelines/chat/code_cleaning.py†L1-L112】
6. **Code execution** – `CodeExecution` runs the Python payload, attaches `execute_sql_query` helpers when needed, and enforces schema via `OutputValidator`. 【F:pandasai/pandasai/pipelines/chat/code_execution.py†L1-L128】
7. **Result validation & parsing** – `ResultValidation` and `ResultParsing` enforce output contracts, log warnings, and serialize responses before returning them to the caller. 【F:pandasai/pandasai/pipelines/chat/result_validation.py†L1-L58】【F:pandasai/pandasai/pipelines/chat/result_parsing.py†L1-L56】

## Error-Correction Path
- When `CodeCleaning` or `CodeExecution` raise, their `on_retry` callbacks build an `ErrorCorrectionPipelineInput` and invoke `ErrorCorrectionPipeline.run`. 【F:pandasai/pandasai/pipelines/chat/generate_chat_pipeline.py†L75-L117】【F:pandasai/pandasai/pipelines/chat/code_execution.py†L73-L132】
- The correction pipeline regenerates a prompt tailored to the exception type (generic, output-type mismatch, or SQL-usage enforcement), re-issues code generation, and re-applies code cleaning before handing the patched code back to the execution loop. 【F:pandasai/pandasai/pipelines/chat/error_correction_pipeline/error_correction_pipeline.py†L1-L48】【F:pandasai/pandasai/pipelines/chat/error_correction_pipeline/error_prompt_generation.py†L1-L75】
- The main execution loop retries until `max_retries` is reached; if retries are exhausted or the framework is disabled, the exception propagates and the pipeline short-circuits before result parsing. 【F:pandasai/pandasai/pipelines/chat/code_execution.py†L97-L166】

## Clarification and Memory Hooks
- Clarification questions live on the `Agent` surface. They reuse the pipeline context and call a dedicated prompt when needed, keeping conversation IDs and memories aligned with the chat pipeline. 【F:pandasai/pandasai/agent/base.py†L311-L389】
- Result parsing also feeds successful outputs back into memory to improve follow-up prompts. 【F:pandasai/pandasai/pipelines/chat/result_parsing.py†L34-L56】

## Failure Modes Affecting Result Parsing
- **Retry exhaustion** – If `max_retries` is reached, `CodeExecution` raises before `ResultValidation` runs. Ensure your local changes keep `self.on_retry` wired to the `ErrorCorrectionPipeline`; removing it will bypass result parsing entirely. 【F:pandasai/pandasai/pipelines/chat/code_execution.py†L118-L166】
- **Error pipeline returning raw strings** – `ErrorCorrectionPipeline.run` must return a cleaned code string (or `LogicUnitOutput` wrapping one). Returning anything else (e.g., an error message) will be fed into the execution loop and can bubble up as user-facing output. 【F:pandasai/pandasai/pipelines/chat/error_correction_pipeline/error_correction_pipeline.py†L28-L48】
- **Missing `final_track_output` flag** – Result parsing is the stage that sets `final_track_output` for telemetry. If earlier stages start marking themselves as final (for example, a custom error handler returning `LogicUnitOutput(..., final_track_output=True)`), the pipeline stops tracking before parsing executes, which often correlates with raw error-correction responses surfacing. 【F:pandasai/pandasai/pipelines/pipeline.py†L67-L122】【F:pandasai/pandasai/pipelines/chat/code_execution.py†L137-L166】

## Guardrails When Modifying DocChat
1. Keep `on_code_retry` wired to `ErrorCorrectionPipeline`; do not return user-facing strings from retry handlers.
2. Ensure any injected logic units still return `LogicUnitOutput` so downstream steps run.
3. Preserve memory writes in `ResultParsing` to keep clarification and follow-up prompts contextual.
4. Align any custom result validators with `OutputValidator` to avoid false negatives that trigger the correction loop.
