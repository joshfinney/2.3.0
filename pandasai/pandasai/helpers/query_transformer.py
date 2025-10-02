"""LLM-driven query transformation module.

This module replaces the legacy rule-based transformer with an LLM-orchestrated
design that uses explicit tool calling for schema fuzzy matching. The goal is to
preserve user intent while improving downstream execution reliability and
maintaining backwards compatibility with existing pipeline integrations.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from pandasai.llm.base import LLM
from pandasai.prompts.query_transformation_prompt import QueryTransformationPrompt

try:  # pragma: no cover - exercised in integration environments
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover - fallback for constrained runtimes
    fuzz = None
    process = None


class QueryType(Enum):
    """Classification of query types as consumed by downstream stages."""

    STATISTICAL = "statistical"
    VISUALIZATION = "visualization"
    FILTERING = "filtering"
    AGGREGATION = "aggregation"
    DESCRIPTIVE = "descriptive"
    COMPARATIVE = "comparative"
    TEMPORAL = "temporal"
    GENERAL = "general"


class TransformationIntent(Enum):
    """Intent preservation levels requested from the LLM."""

    PRESERVE_EXACT = "preserve_exact"
    ENHANCE_CLARITY = "enhance_clarity"
    OPTIMIZE_STRUCTURE = "optimize_structure"
    ENRICH_CONTEXT = "enrich_context"


@dataclass
class ToolInvocation:
    """Trace entry for each executed tool."""

    name: str
    args: Dict[str, Any]
    result: Dict[str, Any]


@dataclass
class QueryTransformationResult:
    """Container returned to the pipeline after transformation."""

    original_query: str
    transformed_query: str
    query_type: QueryType
    intent_level: TransformationIntent
    metadata: Dict[str, Any]
    confidence_score: float
    user_facing_hints: Optional[str] = None
    confidence_threshold: float = 0.7

    def should_apply_transformation(self) -> bool:
        """Return True when the optimized query should replace the original."""

        if not self.transformed_query:
            return False
        if self.transformed_query == self.original_query:
            return False
        return self.confidence_score >= self.confidence_threshold

    def get_query_for_pipeline(self) -> str:
        """Return the query string to forward to downstream pipeline stages."""

        return (
            self.transformed_query
            if self.should_apply_transformation()
            else self.original_query
        )


class QueryTransformerError(RuntimeError):
    """Raised when the transformer cannot obtain a valid LLM response."""


class QueryTransformer:
    """LLM-orchestrated query transformer with tool execution support."""

    def __init__(
        self,
        llm: LLM,
        *,
        confidence_threshold: float = 0.7,
        max_tool_iterations: int = 2,
        max_candidates: int = 50,
    ) -> None:
        if llm is None:
            raise ValueError("QueryTransformer requires an LLM instance")

        self._llm = llm
        self._confidence_threshold = confidence_threshold
        self._max_tool_iterations = max(0, max_tool_iterations)
        self._max_candidates = max(1, max_candidates)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def transform(
        self,
        query: str,
        context_metadata: Optional[Dict[str, Any]] = None,
        pipeline_context: Any = None,
    ) -> QueryTransformationResult:
        """Transform the query through an LLM + tool orchestration loop."""

        if not query or not isinstance(query, str) or not query.strip():
            return QueryTransformationResult(
                original_query=query,
                transformed_query=query,
                query_type=QueryType.GENERAL,
                intent_level=TransformationIntent.PRESERVE_EXACT,
                metadata={"llm_bypass_reason": "empty_query"},
                confidence_score=1.0,
                confidence_threshold=self._confidence_threshold,
            )

        context_metadata = context_metadata or {}
        deduped_columns = self._prepare_column_inventory(
            context_metadata.get("available_columns", [])
        )

        tool_invocations: List[ToolInvocation] = []
        final_payload: Optional[Dict[str, Any]] = None
        raw_responses: List[str] = []

        for iteration in range(self._max_tool_iterations + 1):
            tool_history = [
                {
                    "name": invocation.name,
                    "args": invocation.args,
                    "result": invocation.result,
                }
                for invocation in tool_invocations
            ]

            prompt = QueryTransformationPrompt(
                context=pipeline_context,
                query=query,
                column_inventory=deduped_columns,
                dataframe_count=int(context_metadata.get("dataframe_count", 0)),
                tool_invocations=tool_history,
                config={
                    "confidence_threshold": self._confidence_threshold,
                    "max_tool_iterations": self._max_tool_iterations,
                    "column_limit": self._max_candidates,
                },
            )

            response = self._llm.call(prompt, pipeline_context)
            raw_responses.append(str(response))
            parsed = self._parse_llm_payload(response)

            action = parsed.get("action", "final")
            if action == "call_tool":
                if iteration >= self._max_tool_iterations:
                    break
                tool_invocation = self._execute_tool(parsed)
                tool_invocations.append(tool_invocation)
                continue

            if action == "final":
                final_payload = parsed
                break

            raise QueryTransformerError(
                f"Unsupported action '{action}' returned by query transformer LLM"
            )

        if final_payload is None:
            final_payload = {
                "transformed_query": query,
                "query_type": "general",
                "intent": "preserve_exact",
                "confidence": 0.0,
                "reasoning": "LLM did not provide a final response",
            }

        result = self._build_result(
            original_query=query,
            payload=final_payload,
            tool_invocations=tool_invocations,
            raw_responses=raw_responses,
        )

        return result

    # ------------------------------------------------------------------
    # Prompt orchestration utilities
    # ------------------------------------------------------------------
    def _prepare_column_inventory(self, columns: Sequence[Any]) -> List[str]:
        sanitized = []
        seen = set()
        for column in columns:
            col_str = str(column).strip()
            if not col_str or col_str.lower() in seen:
                continue
            sanitized.append(col_str)
            seen.add(col_str.lower())
            if len(sanitized) >= self._max_candidates:
                break
        return sanitized

    def _parse_llm_payload(self, response: Any) -> Dict[str, Any]:
        if not isinstance(response, str):
            response = str(response)

        response = response.strip()
        if "```" in response:
            segments = [segment.strip() for segment in response.split("```") if segment.strip()]
            if segments:
                response = segments[0]
        if response.lower().startswith("json"):
            response = response[4:].lstrip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
            raise QueryTransformerError(
                f"Query transformer LLM produced invalid JSON: {exc}: {response}"
            ) from exc

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------
    def _execute_tool(self, payload: Dict[str, Any]) -> ToolInvocation:
        tool_name = payload.get("tool_name")
        if not tool_name:
            raise QueryTransformerError("Tool request missing 'tool_name'")

        args = payload.get("tool_args", {})
        if tool_name == "rapidfuzz_similarity":
            result = self._rapidfuzz_similarity(**args)
        else:  # pragma: no cover - safeguard for future extensions
            raise QueryTransformerError(f"Unsupported tool '{tool_name}' requested")

        return ToolInvocation(name=tool_name, args=args, result=result)

    def _rapidfuzz_similarity(
        self,
        query: str,
        choices: Sequence[str],
        limit: int = 5,
        scorer: str = "token_sort_ratio",
    ) -> Dict[str, Any]:
        limit = max(1, min(int(limit), self._max_candidates))
        choices_list = [str(choice) for choice in choices][: self._max_candidates]
        engine = "rapidfuzz"

        if process is None or fuzz is None:  # pragma: no cover - fallback path
            engine = "difflib"
            import difflib

            matches = []
            for candidate in choices_list:
                score = difflib.SequenceMatcher(None, query, candidate).ratio() * 100
                matches.append({"choice": candidate, "score": round(score, 2)})
            matches.sort(key=lambda item: item["score"], reverse=True)
            matches = matches[:limit]
        else:
            scorer_fn = getattr(fuzz, scorer, fuzz.token_sort_ratio)
            results = process.extract(
                query,
                choices_list,
                scorer=scorer_fn,
                limit=limit,
            )
            matches = [
                {"choice": candidate, "score": round(float(score), 2)}
                for candidate, score, _ in results
            ]

        return {"engine": engine, "matches": matches}

    # ------------------------------------------------------------------
    # Result construction
    # ------------------------------------------------------------------
    def _build_result(
        self,
        *,
        original_query: str,
        payload: Dict[str, Any],
        tool_invocations: List[ToolInvocation],
        raw_responses: List[str],
    ) -> QueryTransformationResult:
        transformed_query = payload.get("transformed_query", original_query) or original_query
        confidence = self._sanitize_confidence(payload.get("confidence"))
        query_type = self._parse_query_type(payload.get("query_type"))
        intent = self._parse_intent(payload.get("intent"))

        metadata = {
            "llm_reasoning": payload.get("reasoning"),
            "llm_metadata": payload.get("metadata", {}),
            "tool_invocations": [
                {
                    "name": invocation.name,
                    "args": self._redact_tool_args(invocation.args),
                    "result": invocation.result,
                }
                for invocation in tool_invocations
            ],
            "raw_responses": raw_responses,
            "iterations": len(raw_responses),
            "final_payload": self._redact_payload(payload),
        }

        hints = None
        metadata_hints = payload.get("metadata", {}).get("user_hints")
        if isinstance(metadata_hints, str):
            hints = metadata_hints

        return QueryTransformationResult(
            original_query=original_query,
            transformed_query=transformed_query,
            query_type=query_type,
            intent_level=intent,
            metadata=metadata,
            confidence_score=confidence,
            user_facing_hints=hints,
            confidence_threshold=self._confidence_threshold,
        )

    def _sanitize_confidence(self, raw_value: Any) -> float:
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = 0.0
        if math.isnan(value) or math.isinf(value):
            value = 0.0
        return max(0.0, min(1.0, value))

    def _parse_query_type(self, raw_value: Any) -> QueryType:
        if isinstance(raw_value, QueryType):
            return raw_value
        if isinstance(raw_value, str):
            normalized = raw_value.strip().lower()
            for query_type in QueryType:
                if query_type.value == normalized:
                    return query_type
        return QueryType.GENERAL

    def _parse_intent(self, raw_value: Any) -> TransformationIntent:
        if isinstance(raw_value, TransformationIntent):
            return raw_value
        if isinstance(raw_value, str):
            normalized = raw_value.strip().lower()
            for intent in TransformationIntent:
                if intent.value == normalized:
                    return intent
        return TransformationIntent.PRESERVE_EXACT

    def _redact_tool_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        redacted = {}
        for key, value in args.items():
            if key in {"choices", "query"}:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = value
        return redacted

    def _redact_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        allowed_keys = {
            "transformed_query",
            "query_type",
            "intent",
            "confidence",
            "reasoning",
            "metadata",
        }
        return {key: payload.get(key) for key in allowed_keys if key in payload}


class QueryTransformerFactory:
    """Factory helpers used by the pipeline to configure the transformer."""

    @staticmethod
    def create_default(llm: LLM) -> QueryTransformer:
        return QueryTransformer(llm, confidence_threshold=0.7, max_tool_iterations=2)

    @staticmethod
    def create_conservative(llm: LLM) -> QueryTransformer:
        return QueryTransformer(llm, confidence_threshold=0.9, max_tool_iterations=1)

    @staticmethod
    def create_aggressive(llm: LLM) -> QueryTransformer:
        return QueryTransformer(llm, confidence_threshold=0.5, max_tool_iterations=3)

    @staticmethod
    def create_from_config(llm: LLM, config: Dict[str, Any]) -> QueryTransformer:
        return QueryTransformer(
            llm,
            confidence_threshold=float(config.get("confidence_threshold", 0.7)),
            max_tool_iterations=int(config.get("max_tool_iterations", 2)),
            max_candidates=int(config.get("max_candidates", 50)),
        )
