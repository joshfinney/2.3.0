from typing import Any

from pandasai.pipelines.logic_unit_output import LogicUnitOutput

from ...helpers.logger import Logger
from ..base_logic_unit import BaseLogicUnit
from ..pipeline_context import PipelineContext


class CodeGenerator(BaseLogicUnit):
    """
    LLM Code Generation Stage
    """

    def __init__(self, on_failure=None, on_retry=None, **kwargs):
        super().__init__(**kwargs)
        self.on_failure = on_failure
        self.on_retry = on_retry

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
        pipeline_context: PipelineContext = kwargs.get("context")
        logger: Logger = kwargs.get("logger")

        try:
            code = pipeline_context.config.llm.generate_code(input, pipeline_context)
            pipeline_context.add("last_code_generated", code)
        except Exception as e:
            if self.on_failure:
                self.on_failure(None, e)
            if self.on_retry:
                return self.on_retry(None, e)
            raise
        logger.log(
            f"""Prompt used:
            {pipeline_context.config.llm.last_prompt}
            """
        )
        logger.log(
            f"""Code generated:
            ```
            {code}
            ```
            """
        )

        return LogicUnitOutput(
            code,
            True,
            "Code Generated Successfully",
            {"content_type": "code", "value": code},
        )
