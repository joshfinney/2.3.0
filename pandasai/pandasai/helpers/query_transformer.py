"""
Query Transformation Module

Implements intelligent query preprocessing that preserves user intent while optimizing
downstream pipeline interpretation. Designed for production environments with strict
separation of concerns between user-facing and internal transformations.

Architecture:
- Minimal surface area: integrates at pipeline entry point
- Backward compatible: graceful degradation for legacy systems
- Scalable: modular design for extensibility
- Maintainable: clear separation of transformation stages
"""

from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re


class QueryType(Enum):
    """Classification of query types for targeted transformation"""
    STATISTICAL = "statistical"
    VISUALIZATION = "visualization"
    FILTERING = "filtering"
    AGGREGATION = "aggregation"
    DESCRIPTIVE = "descriptive"
    COMPARATIVE = "comparative"
    TEMPORAL = "temporal"
    GENERAL = "general"


class TransformationIntent(Enum):
    """Intent preservation levels"""
    PRESERVE_EXACT = "preserve_exact"  # No transformation
    ENHANCE_CLARITY = "enhance_clarity"  # Clarify ambiguous terms
    OPTIMIZE_STRUCTURE = "optimize_structure"  # Restructure for better understanding
    ENRICH_CONTEXT = "enrich_context"  # Add contextual information


@dataclass
class QueryTransformationResult:
    """
    Result of query transformation with full traceability

    Attributes:
        original_query: The unmodified user input
        transformed_query: The optimized query for pipeline processing
        query_type: Classified query type
        intent_level: Applied transformation intent
        metadata: Internal metadata for pipeline optimization (not user-facing)
        confidence_score: Transformation confidence (0.0-1.0)
        user_facing_hints: Optional hints that can be displayed to user
    """
    original_query: str
    transformed_query: str
    query_type: QueryType
    intent_level: TransformationIntent
    metadata: Dict[str, Any]
    confidence_score: float
    user_facing_hints: Optional[str] = None

    def should_apply_transformation(self) -> bool:
        """Determine if transformation should be applied based on confidence"""
        return self.confidence_score >= 0.7 and self.transformed_query != self.original_query

    def get_query_for_pipeline(self) -> str:
        """Get the appropriate query version for pipeline processing"""
        return self.transformed_query if self.should_apply_transformation() else self.original_query


class QueryTransformer:
    """
    Production-grade query transformer with strategic intent preservation

    Design Principles:
    1. Minimal intervention: Only transform when confidence is high
    2. Intent preservation: Never alter the core meaning
    3. Context enrichment: Add implicit information for better results
    4. Scalable patterns: Extensible transformation rules
    """

    # Statistical operation synonyms for normalization
    STATISTICAL_PATTERNS = {
        r'\b(avg|average)\b': 'mean',
        r'\b(total|sum up)\b': 'sum',
        r'\b(count|number of|how many)\b': 'count',
        r'\b(middle value)\b': 'median',
        r'\b(most common|most frequent)\b': 'mode',
        r'\b(spread|variability)\b': 'standard deviation',
    }

    # Visualization keywords for type detection
    VISUALIZATION_KEYWORDS = [
        'plot', 'chart', 'graph', 'visualize', 'show', 'display',
        'histogram', 'bar chart', 'line graph', 'scatter', 'pie chart'
    ]

    # Temporal patterns
    TEMPORAL_KEYWORDS = [
        'trend', 'over time', 'time series', 'daily', 'monthly', 'yearly',
        'before', 'after', 'during', 'between'
    ]

    # Comparative patterns
    COMPARATIVE_KEYWORDS = [
        'compare', 'difference', 'versus', 'vs', 'against', 'between',
        'higher than', 'lower than', 'greater than', 'less than'
    ]

    def __init__(
        self,
        enable_normalization: bool = True,
        enable_context_enrichment: bool = True,
        enable_ambiguity_resolution: bool = True,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize query transformer with configuration

        Args:
            enable_normalization: Normalize statistical terminology
            enable_context_enrichment: Add implicit contextual information
            enable_ambiguity_resolution: Resolve ambiguous references
            confidence_threshold: Minimum confidence for applying transformations
        """
        self.enable_normalization = enable_normalization
        self.enable_context_enrichment = enable_context_enrichment
        self.enable_ambiguity_resolution = enable_ambiguity_resolution
        self.confidence_threshold = confidence_threshold

    def transform(
        self,
        query: str,
        context_metadata: Optional[Dict[str, Any]] = None
    ) -> QueryTransformationResult:
        """
        Transform query while preserving intent

        Args:
            query: User's original query
            context_metadata: Optional metadata about available dataframes, columns, etc.

        Returns:
            QueryTransformationResult with transformation details
        """
        if not query or not query.strip():
            return QueryTransformationResult(
                original_query=query,
                transformed_query=query,
                query_type=QueryType.GENERAL,
                intent_level=TransformationIntent.PRESERVE_EXACT,
                metadata={},
                confidence_score=1.0
            )

        # Stage 1: Classify query type
        query_type = self._classify_query(query)

        # Stage 2: Apply transformations
        transformed_query = query
        transformation_metadata = {
            "transformations_applied": [],
            "detected_entities": {},
            "optimization_hints": []
        }

        if self.enable_normalization:
            transformed_query, norm_metadata = self._normalize_terminology(
                transformed_query, query_type
            )
            transformation_metadata["transformations_applied"].extend(
                norm_metadata.get("applied", [])
            )

        if self.enable_context_enrichment and context_metadata:
            transformed_query, enrich_metadata = self._enrich_with_context(
                transformed_query, query_type, context_metadata
            )
            transformation_metadata["detected_entities"].update(
                enrich_metadata.get("entities", {})
            )

        if self.enable_ambiguity_resolution:
            transformed_query, resolution_metadata = self._resolve_ambiguities(
                transformed_query, query_type, context_metadata
            )
            transformation_metadata["optimization_hints"].extend(
                resolution_metadata.get("hints", [])
            )

        # Stage 3: Calculate confidence and determine intent level
        confidence = self._calculate_confidence(
            query, transformed_query, query_type, transformation_metadata
        )

        intent_level = self._determine_intent_level(
            query, transformed_query, confidence
        )

        # Stage 4: Generate user-facing hints (if significant transformation occurred)
        user_facing_hints = None
        if confidence >= 0.8 and query != transformed_query:
            user_facing_hints = self._generate_user_hints(
                query, transformed_query, query_type
            )

        return QueryTransformationResult(
            original_query=query,
            transformed_query=transformed_query,
            query_type=query_type,
            intent_level=intent_level,
            metadata=transformation_metadata,
            confidence_score=confidence,
            user_facing_hints=user_facing_hints
        )

    def _classify_query(self, query: str) -> QueryType:
        """Classify query into type for targeted transformation"""
        query_lower = query.lower()

        # Check for visualization intent
        if any(kw in query_lower for kw in self.VISUALIZATION_KEYWORDS):
            return QueryType.VISUALIZATION

        # Check for temporal analysis
        if any(kw in query_lower for kw in self.TEMPORAL_KEYWORDS):
            return QueryType.TEMPORAL

        # Check for comparative analysis
        if any(kw in query_lower for kw in self.COMPARATIVE_KEYWORDS):
            return QueryType.COMPARATIVE

        # Check for statistical operations
        stat_pattern = re.compile(
            r'\b(mean|average|sum|count|median|mode|std|variance|min|max)\b',
            re.IGNORECASE
        )
        if stat_pattern.search(query_lower):
            return QueryType.STATISTICAL

        # Check for aggregation
        agg_pattern = re.compile(
            r'\b(group by|aggregate|summarize|total by)\b',
            re.IGNORECASE
        )
        if agg_pattern.search(query_lower):
            return QueryType.AGGREGATION

        # Check for filtering
        filter_pattern = re.compile(
            r'\b(where|filter|only|exclude|select)\b',
            re.IGNORECASE
        )
        if filter_pattern.search(query_lower):
            return QueryType.FILTERING

        # Check for descriptive
        desc_pattern = re.compile(
            r'\b(describe|summary|overview|info|what is|show me)\b',
            re.IGNORECASE
        )
        if desc_pattern.search(query_lower):
            return QueryType.DESCRIPTIVE

        return QueryType.GENERAL

    def _normalize_terminology(
        self, query: str, query_type: QueryType
    ) -> Tuple[str, Dict[str, Any]]:
        """Normalize statistical and analytical terminology"""
        normalized = query
        applied_normalizations = []

        if query_type in [QueryType.STATISTICAL, QueryType.AGGREGATION]:
            for pattern, replacement in self.STATISTICAL_PATTERNS.items():
                if re.search(pattern, normalized, re.IGNORECASE):
                    original = normalized
                    normalized = re.sub(
                        pattern, replacement, normalized, flags=re.IGNORECASE
                    )
                    if original != normalized:
                        applied_normalizations.append(
                            f"normalized_{pattern.strip('\\b()')}_to_{replacement}"
                        )

        metadata = {
            "applied": applied_normalizations,
            "original_had_synonyms": len(applied_normalizations) > 0
        }

        return normalized, metadata

    def _enrich_with_context(
        self,
        query: str,
        query_type: QueryType,
        context_metadata: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Enrich query with implicit contextual information"""
        enriched = query
        detected_entities = {}

        # Extract available columns from context if provided
        available_columns = context_metadata.get("available_columns", [])
        detected_columns = []

        # Detect column references in query
        for column in available_columns:
            # Use case-insensitive matching for column detection
            if re.search(rf'\b{re.escape(column)}\b', query, re.IGNORECASE):
                detected_columns.append(column)

        detected_entities["columns"] = detected_columns
        detected_entities["dataframe_count"] = context_metadata.get("dataframe_count", 0)

        # Add implicit aggregation scope if missing
        if query_type == QueryType.STATISTICAL and "group by" not in query.lower():
            # Check if query implies grouping but doesn't specify
            if any(word in query.lower() for word in ["by", "per", "for each"]):
                # Add optimization hint but don't modify query (preserve intent)
                detected_entities["implied_grouping"] = True

        metadata = {
            "entities": detected_entities,
            "context_used": bool(available_columns)
        }

        return enriched, metadata

    def _resolve_ambiguities(
        self,
        query: str,
        query_type: QueryType,
        context_metadata: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        """Resolve ambiguous references in query"""
        resolved = query
        hints = []

        # Detect ambiguous pronouns (it, this, that, these, those)
        ambiguous_pronouns = re.findall(
            r'\b(it|this|that|these|those)\b',
            query,
            re.IGNORECASE
        )

        if ambiguous_pronouns and context_metadata:
            # Add hint for downstream processing
            hints.append({
                "type": "ambiguous_reference",
                "pronouns": ambiguous_pronouns,
                "suggestion": "Consider using conversation context for resolution"
            })

        # Detect missing explicit dataframe reference in multi-df contexts
        if context_metadata and context_metadata.get("dataframe_count", 0) > 1:
            # Check if query doesn't explicitly mention dataframe index
            if not re.search(r'dfs?\[\d+\]|dataframe \d+', query, re.IGNORECASE):
                hints.append({
                    "type": "implicit_dataframe",
                    "suggestion": "Query may require dataframe context resolution"
                })

        # Detect incomplete temporal specifications
        if query_type == QueryType.TEMPORAL:
            if not re.search(
                r'\d{4}|january|february|march|april|may|june|july|august|'
                r'september|october|november|december|last \w+|this \w+',
                query,
                re.IGNORECASE
            ):
                hints.append({
                    "type": "vague_temporal",
                    "suggestion": "Temporal query lacks specific time reference"
                })

        metadata = {
            "hints": hints,
            "ambiguities_detected": len(hints)
        }

        return resolved, metadata

    def _calculate_confidence(
        self,
        original: str,
        transformed: str,
        query_type: QueryType,
        transformation_metadata: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for transformation quality"""
        base_confidence = 1.0

        # Reduce confidence if too many transformations applied
        num_transformations = len(
            transformation_metadata.get("transformations_applied", [])
        )
        if num_transformations > 3:
            base_confidence -= 0.1 * (num_transformations - 3)

        # Reduce confidence if ambiguities detected
        num_ambiguities = transformation_metadata.get("optimization_hints", [])
        ambiguity_count = sum(
            1 for hint in num_ambiguities
            if isinstance(hint, dict) and hint.get("type") == "ambiguous_reference"
        )
        base_confidence -= 0.05 * ambiguity_count

        # Increase confidence for well-classified queries
        if query_type != QueryType.GENERAL:
            base_confidence += 0.05

        # Ensure confidence stays within bounds
        return max(0.0, min(1.0, base_confidence))

    def _determine_intent_level(
        self, original: str, transformed: str, confidence: float
    ) -> TransformationIntent:
        """Determine the intent level of applied transformations"""
        if original == transformed:
            return TransformationIntent.PRESERVE_EXACT

        # Calculate edit distance ratio
        edit_distance = len(set(original.lower().split()) ^ set(transformed.lower().split()))
        total_words = len(set(original.lower().split()) | set(transformed.lower().split()))
        change_ratio = edit_distance / total_words if total_words > 0 else 0

        if change_ratio < 0.1 and confidence > 0.8:
            return TransformationIntent.ENHANCE_CLARITY
        elif change_ratio < 0.3:
            return TransformationIntent.OPTIMIZE_STRUCTURE
        else:
            return TransformationIntent.ENRICH_CONTEXT

    def _generate_user_hints(
        self, original: str, transformed: str, query_type: QueryType
    ) -> Optional[str]:
        """Generate user-facing hints about query interpretation"""
        # Only generate hints for significant transformations
        if original.lower() == transformed.lower():
            return None

        # For now, return None as user-facing hints are optional
        # This can be expanded based on UX requirements
        return None


class QueryTransformerFactory:
    """Factory for creating configured QueryTransformer instances"""

    @staticmethod
    def create_default() -> QueryTransformer:
        """Create transformer with default production settings"""
        return QueryTransformer(
            enable_normalization=True,
            enable_context_enrichment=True,
            enable_ambiguity_resolution=True,
            confidence_threshold=0.7
        )

    @staticmethod
    def create_conservative() -> QueryTransformer:
        """Create transformer with conservative settings (minimal intervention)"""
        return QueryTransformer(
            enable_normalization=False,
            enable_context_enrichment=False,
            enable_ambiguity_resolution=True,
            confidence_threshold=0.9
        )

    @staticmethod
    def create_aggressive() -> QueryTransformer:
        """Create transformer with aggressive optimization"""
        return QueryTransformer(
            enable_normalization=True,
            enable_context_enrichment=True,
            enable_ambiguity_resolution=True,
            confidence_threshold=0.5
        )

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> QueryTransformer:
        """Create transformer from configuration dictionary"""
        return QueryTransformer(
            enable_normalization=config.get("enable_normalization", True),
            enable_context_enrichment=config.get("enable_context_enrichment", True),
            enable_ambiguity_resolution=config.get("enable_ambiguity_resolution", True),
            confidence_threshold=config.get("confidence_threshold", 0.7)
        )
