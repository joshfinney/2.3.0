from typing import TYPE_CHECKING

from .base import BasePrompt

if TYPE_CHECKING:
    from pandasai.helpers.harmony_messages import HarmonyMessages
    from pandasai.pipelines.pipeline_context import PipelineContext


class CorrectErrorPrompt(BasePrompt):
    """Prompt to generate Python code from a dataframe."""

    template_path = "correct_error_prompt.tmpl"

    def to_harmony_messages(self, context: "PipelineContext") -> "HarmonyMessages":
        """Convert to Harmony format for isolated error correction"""
        from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder

        # Get error details
        failed_code = self.props.get("code", "")
        error_details = str(self.props.get("error", ""))

        # Get reasoning level for error correction
        reasoning_level = self.get_reasoning_level(context)

        # Build isolated error correction messages
        return HarmonyMessagesBuilder.for_error_correction(
            error_details=error_details,
            failed_code=failed_code,
            reasoning_level=reasoning_level
        )

    def to_json(self):
        context = self.props["context"]
        code = self.props["code"]
        error = self.props["error"]
        memory = context.memory
        conversations = memory.to_json()

        system_prompt = memory.get_system_prompt()

        # prepare datasets
        datasets = [dataset.to_json() for dataset in context.dfs]

        return {
            "datasets": datasets,
            "conversation": conversations,
            "system_prompt": system_prompt,
            "error": {
                "code": code,
                "error_trace": str(error),
                "exception_type": "Exception",
            },
            "config": {"direct_sql": context.config.direct_sql},
        }
