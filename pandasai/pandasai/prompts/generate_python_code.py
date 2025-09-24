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
        from pandasai.helpers.vector_store import VectorStore

        # Extract dataframe information
        dataframes_info = ""
        dataframe_names = []
        for i, df in enumerate(context.dfs):
            df_info = df.head_csv if hasattr(df, 'head_csv') else str(df)[:500]
            dataframes_info += f"dfs[{i}]: {df_info}\n"
            dataframe_names.append(f"dfs[{i}]")

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

        # Initialize vector store and generate contexts
        vector_store = self._get_or_create_vector_store(context)

        # Get current query for few-shot context
        current_query = context.get("current_user_query", "")
        few_shot_context = ""
        column_context = ""

        if current_query and getattr(context.config, 'enable_few_shot_prompting', True):
            few_shot_context = vector_store.generate_few_shot_context(current_query)

        if getattr(context.config, 'enable_column_context', True):
            # Extract and store column context for current dataframes
            vector_store.extract_column_context_from_dataframes(context.dfs, dataframe_names)
            column_context = vector_store.generate_column_context(dataframe_names)

        # Build messages using builder pattern
        messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info=dataframes_info,
            skills_info=skills_info,
            previous_code=previous_code,
            viz_library=viz_lib,
            reasoning_level=reasoning_level,
            few_shot_context=few_shot_context,
            column_context=column_context
        )

        return messages

    def _get_or_create_vector_store(self, context: "PipelineContext"):
        """Get or create vector store instance with persistent storage"""
        from pandasai.helpers.vector_store import VectorStore
        import tempfile
        import os

        # Check if vector store already exists in context
        if hasattr(context, '_vector_store'):
            return context._vector_store

        # Create storage path
        storage_dir = getattr(context.config, 'vector_store_path', None)
        if not storage_dir:
            storage_dir = os.path.join(tempfile.gettempdir(), 'pandasai_vector_store')

        storage_path = os.path.join(storage_dir, 'vector_store.json')

        # Create and cache vector store
        vector_store = VectorStore(storage_path)
        context._vector_store = vector_store

        return vector_store

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
