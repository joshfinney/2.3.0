from typing import TYPE_CHECKING

from .base import BasePrompt

if TYPE_CHECKING:
    from pandasai.helpers.harmony_messages import HarmonyMessages
    from pandasai.pipelines.pipeline_context import PipelineContext


class GeneratePythonCodePrompt(BasePrompt):
    """Prompt to generate Python code from a dataframe."""

    template_path = "generate_python_code.tmpl"

    def to_harmony_messages(self, context: "PipelineContext") -> "HarmonyMessages":
        """Convert to Harmony format with strategic system message separation"""
        from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder

        # Extract dataframe information
        dataframes_info = ""
        for i, df in enumerate(context.dfs):
            df_info = df.head_csv if hasattr(df, 'head_csv') else str(df)[:500]
            dataframes_info += f"dfs[{i}]: {df_info}\n"

        # Extract skills information
        skills_info = ""
        if context.skills_manager and context.skills_manager.has_skills():
            skills_info = context.skills_manager.prompt_display()

        # Get previous code if available
        previous_code = self.props.get("last_code_generated", "")

        # Get visualization library
        viz_lib = self.props.get("viz_lib", "")

        # Get reasoning level for code generation
        reasoning_level = self.get_reasoning_level(context)

        # Build messages using builder pattern
        messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info=dataframes_info,
            skills_info=skills_info,
            previous_code=previous_code,
            viz_library=viz_lib,
            reasoning_level=reasoning_level
        )

        return messages

    def to_json(self):
        context = self.props["context"]
        viz_lib = self.props["viz_lib"]
        output_type = self.props["output_type"]
        memory = context.memory
        conversations = memory.to_json()

        system_prompt = memory.get_system_prompt()

        # prepare datasets
        datasets = [dataset.to_json() for dataset in context.dfs]

        return {
            "datasets": datasets,
            "conversation": conversations,
            "system_prompt": system_prompt,
            "prompt": self.to_string(),
            "config": {
                "direct_sql": context.config.direct_sql,
                "viz_lib": viz_lib,
                "output_type": output_type,
            },
        }
