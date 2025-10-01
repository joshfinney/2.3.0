"""
Query Transformation Pipeline Stage

Integrates query transformation into the GenerateChatPipeline as the first preprocessing step.
Designed for minimal surface area and maximum backward compatibility.
"""

from typing import Any, Optional, Dict
from pandasai.pipelines.base_logic_unit import BaseLogicUnit
from pandasai.pipelines.logic_unit_output import LogicUnitOutput
from pandasai.pipelines.pipeline_context import PipelineContext
from pandasai.helpers.logger import Logger
from pandasai.helpers.query_transformer import (
    QueryTransformer,
    QueryTransformerFactory,
    QueryTransformationResult
)


class QueryTransformationUnit(BaseLogicUnit):
    """
    Pipeline logic unit for query transformation

    Position: First stage after input validation
    Purpose: Preprocess user queries to optimize downstream pipeline understanding
    Impact: Internal only - user never sees transformed query directly
    """

    def __init__(
        self,
        transformer: Optional[QueryTransformer] = None,
        **kwargs
    ):
        """
        Initialize query transformation unit

        Args:
            transformer: Optional custom QueryTransformer instance
            **kwargs: Additional BaseLogicUnit arguments
        """
        super().__init__(**kwargs)
        self._transformer = transformer
        self._transformer_cache = {}

    def execute(self, input: Any, **kwargs) -> Any:
        """
        Execute query transformation

        Args:
            input: ChatPipelineInput containing the user query
            kwargs: Pipeline context including logger and config

        Returns:
            LogicUnitOutput with transformation results
        """
        context: PipelineContext = kwargs.get("context")
        logger: Logger = kwargs.get("logger")

        # Check if transformation is enabled in config
        if not self._should_transform(context):
            logger.log("Query transformation disabled, passing through original query")
            return LogicUnitOutput(
                input,
                True,
                "Query transformation skipped (disabled in config)"
            )

        # Get transformer based on configuration mode
        transformer = self._get_transformer(context)

        # Extract query from input
        original_query = getattr(input, 'query', str(input))

        # Build context metadata for transformation
        context_metadata = self._build_context_metadata(context)

        # Perform transformation
        try:
            transformation_result = transformer.transform(
                original_query,
                context_metadata
            )

            # Log transformation details
            self._log_transformation(logger, transformation_result)

            # Store transformation metadata in pipeline context (internal only)
            self._store_transformation_metadata(context, transformation_result)

            # Modify input query if transformation should be applied
            if transformation_result.should_apply_transformation():
                if hasattr(input, 'query'):
                    # Store original query for reference
                    context.add("original_user_query", input.query)
                    # Update query with transformed version
                    input.query = transformation_result.transformed_query
                    logger.log(f"Query transformed: '{original_query}' -> '{input.query}'")
                else:
                    logger.log("Input does not have 'query' attribute, transformation not applied")

            return LogicUnitOutput(
                input,
                True,
                "Query transformation completed",
                {
                    "content_type": "query_transformation",
                    "transformation_applied": transformation_result.should_apply_transformation(),
                    "query_type": transformation_result.query_type.value,
                    "confidence": transformation_result.confidence_score
                }
            )

        except Exception as e:
            # Graceful degradation: if transformation fails, continue with original query
            logger.log(f"Query transformation failed: {str(e)}, using original query")
            return LogicUnitOutput(
                input,
                True,
                f"Query transformation failed (graceful degradation): {str(e)}"
            )

    def _get_transformer(self, context: PipelineContext) -> QueryTransformer:
        """Get transformer instance based on configuration mode"""
        if self._transformer:
            return self._transformer

        # Get transformation mode from config
        mode = getattr(context.config, 'query_transformation_mode', 'default')

        # Use cached transformer if available
        if mode in self._transformer_cache:
            return self._transformer_cache[mode]

        # Create transformer based on mode
        if mode == 'conservative':
            transformer = QueryTransformerFactory.create_conservative()
        elif mode == 'aggressive':
            transformer = QueryTransformerFactory.create_aggressive()
        else:  # 'default'
            transformer = QueryTransformerFactory.create_default()

        # Cache for reuse
        self._transformer_cache[mode] = transformer
        return transformer

    def _should_transform(self, context: PipelineContext) -> bool:
        """Check if query transformation should be applied"""
        # Check config flag (defaults to True if not specified)
        return getattr(context.config, 'enable_query_transformation', True)

    def _build_context_metadata(self, context: PipelineContext) -> Dict[str, Any]:
        """Build context metadata for transformer"""
        metadata = {
            "dataframe_count": len(context.dfs) if context.dfs else 0,
            "available_columns": []
        }

        # Extract available columns from dataframes
        try:
            for df in context.dfs:
                if hasattr(df, 'columns'):
                    metadata["available_columns"].extend(
                        [str(col) for col in df.columns]
                    )
                elif hasattr(df, 'head'):
                    # For connectors, try to get column info
                    try:
                        sample = df.head()
                        if hasattr(sample, 'columns'):
                            metadata["available_columns"].extend(
                                [str(col) for col in sample.columns]
                            )
                    except Exception:
                        pass
        except Exception:
            # If we can't extract columns, continue with empty list
            pass

        return metadata

    def _log_transformation(
        self,
        logger: Logger,
        result: QueryTransformationResult
    ) -> None:
        """Log transformation details for debugging"""
        logger.log(f"Query Type: {result.query_type.value}")
        logger.log(f"Intent Level: {result.intent_level.value}")
        logger.log(f"Confidence: {result.confidence_score:.2f}")

        if result.metadata.get("transformations_applied"):
            logger.log(
                f"Transformations: {', '.join(result.metadata['transformations_applied'])}"
            )

        if result.metadata.get("optimization_hints"):
            logger.log(
                f"Optimization hints: {len(result.metadata['optimization_hints'])} detected"
            )

    def _store_transformation_metadata(
        self,
        context: PipelineContext,
        result: QueryTransformationResult
    ) -> None:
        """Store transformation metadata in pipeline context for downstream use"""
        # Store as internal metadata - not exposed to user
        context.add("query_transformation_metadata", {
            "query_type": result.query_type.value,
            "intent_level": result.intent_level.value,
            "confidence_score": result.confidence_score,
            "detected_entities": result.metadata.get("detected_entities", {}),
            "optimization_hints": result.metadata.get("optimization_hints", [])
        })
