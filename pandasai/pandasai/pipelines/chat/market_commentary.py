"""
Market Commentary Pipeline Step
Transforms code generation output into conversational market-style commentary
"""
from typing import Any
import json

from pandasai.pipelines.logic_unit_output import LogicUnitOutput

from ...helpers.logger import Logger
from ...helpers.harmony_messages import HarmonyMessages, HarmonyMessagesBuilder
from ..base_logic_unit import BaseLogicUnit
from ..pipeline_context import PipelineContext


class MarketCommentary(BaseLogicUnit):
    """
    Market Commentary Transformation Stage
    Converts code generation results into market-style commentary
    """

    def execute(self, input: Any, **kwargs) -> Any:
        """
        Transform code generation output into conversational market commentary

        :param input: Code generation result
        :param kwargs: Pipeline context and configuration
        :return: Enhanced result with market commentary
        """
        pipeline_context: PipelineContext = kwargs.get("context")
        logger: Logger = kwargs.get("logger")

        # Skip transformation if not in Harmony format or if disabled
        if not pipeline_context.config.use_harmony_format:
            logger.log("Skipping market commentary - not using Harmony format")
            return LogicUnitOutput(input, True, "Skipped market commentary transformation")

        # Skip if market commentary is disabled
        if not getattr(pipeline_context.config, 'enable_market_commentary', True):
            logger.log("Market commentary disabled in configuration")
            return LogicUnitOutput(input, True, "Market commentary disabled")

        try:
            # Get the executed result (with materialized values) and generated code
            executed_result = input.get("value") if isinstance(input, dict) else str(input)
            generated_code = pipeline_context.get("last_code_generated", "")
            current_query = pipeline_context.get("current_user_query", "")

            # Generate market commentary from executed result + code context
            commentary = self._generate_market_commentary(
                executed_result, generated_code, current_query, pipeline_context, logger
            )

            # Generate next steps if enabled
            next_steps = ""
            if getattr(pipeline_context.config, 'enable_next_steps_prompt', True):
                next_steps = self._generate_next_steps(
                    executed_result, generated_code, current_query, commentary, pipeline_context, logger
                )

            # Create enhanced result with clear UX separation
            if isinstance(input, dict):
                enhanced_result = {
                    # Primary artifacts (plots, data, etc.)
                    "primary_result": {
                        "type": input.get("type", "unknown"),
                        "value": input.get("value"),
                        "original_result": input
                    },

                    # Market commentary (conversationalized from materialized f-string results)
                    "market_commentary": {
                        "content": commentary,
                        "generated_from": "executed_result_analysis"
                    },

                    # Next steps suggestions (contextual follow-up prompts)
                    "next_steps": {
                        "suggestions": next_steps,
                        "enabled": bool(next_steps),
                        "prompt_style": "Do you want me to..."
                    },

                    # Metadata
                    "enhanced_chat_response": True,
                    "original_query": current_query
                }
            else:
                enhanced_result = {
                    "primary_result": {
                        "type": "raw_value",
                        "value": input
                    },
                    "market_commentary": {
                        "content": commentary,
                        "generated_from": "executed_result_analysis"
                    },
                    "next_steps": {
                        "suggestions": next_steps,
                        "enabled": bool(next_steps),
                        "prompt_style": "Do you want me to..."
                    },
                    "enhanced_chat_response": True,
                    "original_query": current_query
                }

            logger.log(f"Generated market commentary: {commentary[:200]}...")

            return LogicUnitOutput(
                enhanced_result,
                True,
                "Market commentary generated successfully",
                {"content_type": "enhanced_result", "commentary_length": len(commentary)}
            )

        except Exception as e:
            logger.log(f"Error generating market commentary: {str(e)}")
            return LogicUnitOutput(input, True, f"Market commentary failed: {str(e)}")

    def _generate_market_commentary(self, executed_result: Any, code: str, query: str, context: PipelineContext, logger: Logger) -> str:
        """Generate market-style commentary for the executed result with materialized values"""

        # Build Harmony messages for commentary generation
        messages = HarmonyMessages(reasoning_level="medium")

        # Core identity for market commentary
        messages.add_core_identity(
            "You are a seasoned market analyst providing clear, insightful commentary on data analysis results. "
            "Transform executed code results with actual values into conversational market-style insights.",
            "medium"
        )

        # Format the executed result for commentary
        result_summary = self._format_result_for_commentary(executed_result)

        # Task context with both code and actual results
        messages.add_task_context(
            f"# ANALYSIS CONTEXT:\n"
            f"User Query: {query}\n"
            f"Generated Code:\n```python\n{code}\n```\n"
            f"Executed Result: {result_summary}\n\n"
            f"Transform this analysis into market commentary that explains what was found and "
            f"what the actual values mean in business terms. Focus on the insights from the executed results."
        )

        # Output format for commentary
        messages.add_output_format(
            "Provide market-style commentary that:\n"
            "1. Summarizes what analysis was performed\n"
            "2. Explains the key insights in business terms\n"
            "3. Uses clear, logical structure\n"
            "4. Maintains professional yet conversational tone\n"
            "Return ONLY the commentary text, no code blocks or technical jargon."
        )

        # Start conversation and add user request
        messages.start_conversation_history()
        messages.add_user_message(f"Generate market commentary for this analysis: {query}")

        try:
            # Generate commentary using LLM
            commentary_messages = messages.get_messages_for_llm()
            commentary = context.config.llm.chat_completion(commentary_messages)
            return commentary.strip()

        except Exception as e:
            logger.log(f"LLM call failed for market commentary: {str(e)}")
            # Fallback to simple commentary
            return self._generate_fallback_commentary(executed_result, code, query)

    def _format_result_for_commentary(self, result: Any) -> str:
        """Format executed result for use in commentary generation"""
        try:
            if isinstance(result, dict):
                if result.get("type") == "number":
                    return f"Number: {result.get('value')}"
                elif result.get("type") == "string":
                    return f"Text: '{result.get('value')}'"
                elif result.get("type") == "dataframe":
                    return f"DataFrame with {len(result.get('value', []))} rows returned"
                elif result.get("type") == "plot":
                    return "Visualization/plot generated"
                else:
                    return f"Result: {result}"
            else:
                return f"Value: {str(result)[:200]}"
        except Exception:
            return "Result generated successfully"

    def _generate_fallback_commentary(self, executed_result: Any, code: str, query: str) -> str:
        """Generate simple fallback commentary when LLM is unavailable"""

        # Format the executed result
        result_summary = self._format_result_for_commentary(executed_result)

        # Basic analysis with actual results
        commentary_parts = [
            f"Analysis completed for: {query}",
            f"Result: {result_summary}",
            "",
            "Key insights:"
        ]

        # Analysis based on code and results
        if "mean" in code.lower() and isinstance(executed_result, dict) and executed_result.get("type") == "number":
            commentary_parts.append(f"• Average value calculated: {executed_result.get('value')}")
        elif "sum" in code.lower() and isinstance(executed_result, dict) and executed_result.get("type") == "number":
            commentary_parts.append(f"• Total sum computed: {executed_result.get('value')}")
        elif "count" in code.lower():
            commentary_parts.append("• Count analysis performed showing data volume")
        elif "groupby" in code.lower():
            commentary_parts.append("• Data segmentation analysis completed")
        elif "plot" in code.lower():
            commentary_parts.append("• Visual representation created for pattern analysis")

        if "f\"" in code or "f'" in code:
            commentary_parts.append("• Results formatted using modern Python f-string standards")

        commentary_parts.extend([
            "",
            "This analysis provides actionable insights for data-driven decision making."
        ])

        return "\n".join(commentary_parts)

    def _generate_next_steps(self, executed_result: Any, code: str, query: str, commentary: str, context: "PipelineContext", logger: Logger) -> str:
        """Generate concise next steps suggestions"""

        # Build messages for next steps generation
        messages = HarmonyMessages(reasoning_level="low")

        # Core identity for next steps
        messages.add_core_identity(
            "You are a strategic advisor providing actionable next steps for data analysis.",
            "low"
        )

        # Format result for context
        result_summary = self._format_result_for_commentary(executed_result)

        # Task context with actual results
        messages.add_task_context(
            f"# ANALYSIS CONTEXT:\n"
            f"Original Query: {query}\n"
            f"Executed Result: {result_summary}\n"
            f"Analysis Commentary: {commentary}\n\n"
            f"Generate 3-5 concise, actionable next steps that logically follow from these specific results."
        )

        # Output format
        messages.add_output_format(
            "Provide a numbered list of 3-5 specific, actionable next steps. "
            "Each step should be:\n"
            "- Concise (1-2 lines maximum)\n"
            "- Actionable and specific\n"
            "- Logically connected to the analysis\n"
            "- Require minimal additional reasoning\n"
            "Format: 1. Step description\n2. Step description\n..."
        )

        # Start conversation
        messages.start_conversation_history()
        messages.add_user_message(f"What are the logical next steps after: {query}")

        try:
            # Generate next steps using LLM
            next_steps_messages = messages.get_messages_for_llm()
            next_steps = context.config.llm.chat_completion(next_steps_messages)
            return next_steps.strip()

        except Exception as e:
            logger.log(f"LLM call failed for next steps: {str(e)}")
            # Fallback to simple next steps
            return self._generate_fallback_next_steps(executed_result, code, query)

    def _generate_fallback_next_steps(self, executed_result: Any, code: str, query: str) -> str:
        """Generate simple fallback next steps when LLM is unavailable"""

        fallback_steps = [
            "1. Validate and review the analysis results for accuracy",
            "2. Consider additional data sources or time periods for comparison",
            "3. Share findings with relevant stakeholders for feedback"
        ]

        # Add context-specific steps based on code analysis
        if "plot" in code.lower() or "chart" in code.lower():
            fallback_steps.append("4. Explore different visualization formats for better insights")

        if "group" in code.lower():
            fallback_steps.append("4. Investigate outliers or anomalies in the grouped data")

        if "correlation" in code.lower() or "relationship" in code.lower():
            fallback_steps.append("4. Analyze potential causal relationships in the data")

        return "\n".join(fallback_steps[:5])  # Limit to 5 steps