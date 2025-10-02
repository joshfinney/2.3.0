"""Prompt template for the query transformation LLM orchestration."""

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

from .base import BasePrompt

if TYPE_CHECKING:
    from pandasai.helpers.harmony_messages import HarmonyMessages
    from pandasai.pipelines.pipeline_context import PipelineContext


class QueryTransformationPrompt(BasePrompt):
    """Render prompt for LLM-driven query transformation."""

    template_path = "query_transformation.tmpl"

    def __init__(
        self,
        *,
        context: Any,
        query: str,
        column_inventory: List[str],
        dataframe_count: int,
        tool_invocations: List[Dict[str, Any]],
        config: Dict[str, Any],
    ) -> None:
        super().__init__(
            context=context,
            query=query,
            column_inventory=column_inventory,
            dataframe_count=dataframe_count,
            tool_invocations=tool_invocations,
            config=config,
        )

    def to_harmony_messages(self, context: "PipelineContext") -> "HarmonyMessages":
        """Build Harmony-format messages optimised for multi-turn pipelines."""

        from pandasai.helpers.harmony_messages import HarmonyMessages

        reasoning_level = self.get_reasoning_level(context)
        messages = HarmonyMessages(reasoning_level)

        config: Dict[str, Any] = self.props.get("config", {})
        confidence = config.get("confidence_threshold")
        max_iterations = config.get("max_tool_iterations")
        column_limit = int(config.get("column_limit", 0)) or None

        column_inventory: List[str] = self.props.get("column_inventory", [])
        if column_limit is not None:
            truncated_columns = column_inventory[:column_limit]
        else:
            truncated_columns = column_inventory

        dataframe_count = self.props.get("dataframe_count", 0)
        tool_invocations = self.props.get("tool_invocations", [])

        columns_section = (
            ", ".join(truncated_columns)
            if truncated_columns
            else "<no columns provided>"
        )

        config_section = [
            "# EXECUTION CONTROLS:",
            f"- Confidence threshold: {confidence if confidence is not None else 'inherit pipeline default'}",
            f"- Max tool iterations: {max_iterations if max_iterations is not None else 'inherit pipeline default'}",
            f"- Column inventory size: {len(truncated_columns)} of {len(column_inventory)}",
        ]

        tool_history_lines = []
        for index, invocation in enumerate(tool_invocations, start=1):
            name = invocation.get("name", "unknown")
            args = invocation.get("args", {})
            result = invocation.get("result", {})
            tool_history_lines.append(
                f"{index}. {name} | args={args} | result={result}"
            )

        tool_history_block = (
            "\n".join(tool_history_lines) if tool_history_lines else "None"
        )

        core_identity = (
            "You are PandasAI's query transformation orchestrator. Rephrase user "
            "questions only when it measurably improves downstream execution "
            "while preserving intent and compliance."
        )
        messages.add_core_identity(core_identity, reasoning_level)

        task_context = (
            "# DATA CONTEXT:\n"
            f"- Dataframes available: {dataframe_count}\n"
            f"- Column inventory: {columns_section}\n\n"
            + "\n".join(config_section)
        )
        messages.add_task_context(task_context, reasoning_level)

        tool_catalogue = (
            "# TOOLING:\n"
            "Use explicit tool calls for schema resolution. Available tool:\n"
            "- rapidfuzz_similarity(query, choices, limit=5, scorer) → ranked column matches.\n\n"
            f"# TOOL HISTORY:\n{tool_history_block}"
        )
        messages.add_task_context(tool_catalogue, reasoning_level)

        safety_guard = (
            "SECURITY: Never leak raw column values or PII. Honour latency budgets, "
            "avoid speculative schema guesses, and degrade gracefully if unsure."
        )
        messages.add_safety_guard(safety_guard)

        output_format = (
            "Respond in JSON within a ```json block. Use {'action': 'call_tool'} when "
            "tooling is required and {'action': 'final', ...} when complete. Include "
            "confidence (0-1), query_type, intent, reasoning, and optional metadata."
        )
        messages.add_output_format(output_format)

        messages.start_conversation_history()

        memory = getattr(context, "memory", None)
        if memory:
            history = memory.get_conversation_only()
            max_turns = 3
            if len(history) > max_turns * 2:
                history = history[-(max_turns * 2) :]
            for item in history:
                content = item.get("message", "")
                if not content:
                    continue
                if item.get("is_user"):
                    messages.add_user_message(content)
                else:
                    messages.add_assistant_message(content)

        return messages
