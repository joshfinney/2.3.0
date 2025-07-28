from typing import Any, Union

from pandasai.pipelines.logic_unit_output import LogicUnitOutput

from ...helpers.logger import Logger
from ...prompts.base import BasePrompt
from ...prompts.generate_python_code import GeneratePythonCodePrompt
from ...prompts.generate_python_code_with_sql import GeneratePythonCodeWithSQLPrompt
from ..base_logic_unit import BaseLogicUnit
from ..pipeline_context import PipelineContext
from .code_execution import get_global_tool_registry


class PromptGeneration(BaseLogicUnit):
    """
    Code Prompt Generation Stage
    """

    pass

    def execute(self, input: Any, **kwargs) -> Any:
        """
        This method will return output according to
        Implementation.

        :param input: Your input data.
        :param kwargs: A dictionary of keyword arguments.
            - 'logger' (any): The logger for logging.
            - 'config' (Config): Global configurations for the test
            - 'context' (any): The execution context.

        :return: The result of the execution.
        """
        self.context: PipelineContext = kwargs.get("context")
        self.logger: Logger = kwargs.get("logger")

        prompt = self.get_chat_prompt(self.context)
        self.logger.log(f"Using prompt: {prompt}")

        return LogicUnitOutput(
            prompt,
            True,
            "Prompt Generated Successfully",
            {"content_type": "prompt", "value": prompt.to_string()},
        )

    def get_chat_prompt(self, context: PipelineContext) -> Union[str, BasePrompt]:
        # set matplotlib as the default library
        viz_lib = "matplotlib"
        if context.config.data_viz_library:
            viz_lib = context.config.data_viz_library

        output_type = context.get("output_type")
        
        # Get tools prompt from global registry
        tool_registry = get_global_tool_registry()
        tools_prompt = ""
        if tool_registry:
            query = context.memory.get_last_message() if context.memory.count() > 0 else None
            tools_prompt = tool_registry.get_contextual_tools_prompt(query)

        return (
            GeneratePythonCodeWithSQLPrompt(
                context=context,
                last_code_generated=context.get("last_code_generated"),
                viz_lib=viz_lib,
                output_type=output_type,
                tools_prompt=tools_prompt,
            )
            if context.config.direct_sql
            else GeneratePythonCodePrompt(
                context=context,
                last_code_generated=context.get("last_code_generated"),
                viz_lib=viz_lib,
                output_type=output_type,
                tools_prompt=tools_prompt,
            )
        )
