from typing import Any

from pandasai.pipelines.logic_unit_output import LogicUnitOutput

from ...responses.context import Context
from ...responses.response_parser import ResponseParser
from ..base_logic_unit import BaseLogicUnit
from ..pipeline_context import PipelineContext


class ResultParsing(BaseLogicUnit):

    """
    Result Parsing Stage
    """

    pass

    def response_parser(self, context: PipelineContext, logger) -> ResponseParser:
        context = Context(context.config, logger=logger)
        return (
            context.config.response_parser(context)
            if context.config.response_parser
            else ResponseParser(context)
        )

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

        result = input

        self._add_result_to_memory(result=result, context=pipeline_context)
        self._store_successful_execution(result=result, context=pipeline_context)

        parser = self.response_parser(pipeline_context, logger=kwargs.get("logger"))
        result = parser.parse(result)
        return LogicUnitOutput(result, True, "Results parsed successfully")

    def _add_result_to_memory(self, result: dict, context: PipelineContext):
        """
        Add the result to the memory.

        Args:
            result (dict): The result to add to the memory
            context (PipelineContext) : Pipeline Context
        """
        if result is None:
            return

        if result["type"] in ["string", "number"]:
            context.memory.add(str(result["value"]), False)
        elif result["type"] == "dataframe":
            context.memory.add("Check it out: <dataframe>", False)
        elif result["type"] == "plot":
            context.memory.add("Check it out: <plot>", False)

    def _store_successful_execution(self, result: dict, context: PipelineContext):
        """
        Store successful query-code execution in vector store for few-shot learning

        Args:
            result (dict): The successful execution result
            context (PipelineContext): Pipeline Context
        """
        # Only store if vector store is available and result is successful
        if not hasattr(context, '_vector_store') or result is None:
            return

        try:
            # Get query and generated code
            query = context.get("current_user_query", "")
            code = context.get("last_code_generated", "")

            if not query or not code:
                return

            # Get result type
            result_type = result.get("type", "unknown")

            # Store in vector store
            vector_store = context._vector_store
            vector_store.add_query_code_pair(
                query=query,
                code=code,
                success=True,
                result_type=result_type
            )

        except Exception:
            # Silently fail if vector store update fails
            pass
