"""
Vector Store for Few-Shot Prompting
Provides semantic similarity search for query-code pairs and column context
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
try:
    from rapidfuzz import fuzz, process
except ImportError:
    # Fallback for simple string matching if rapidfuzz is not available
    class MockFuzz:
        @staticmethod
        def WRatio(a, b):
            # Simple similarity based on common words
            words_a = set(a.lower().split())
            words_b = set(b.lower().split())
            if not words_a or not words_b:
                return 0
            intersection = words_a & words_b
            union = words_a | words_b
            return int(100 * len(intersection) / len(union))

    class MockProcess:
        @staticmethod
        def extract(query, choices, scorer=None, limit=3):
            if not choices:
                return []

            # Simple fallback scoring
            scored = []
            for choice in choices:
                if scorer:
                    score = scorer(query, choice)
                else:
                    score = MockFuzz.WRatio(query, choice)
                scored.append((choice, score, 0))

            # Sort by score and return top results
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:limit]

    fuzz = MockFuzz()
    process = MockProcess()


@dataclass
class QueryCodePair:
    """Represents a query-code pair with metadata"""
    query: str
    code: str
    query_hash: str
    success: bool = True
    execution_time: Optional[float] = None
    result_type: Optional[str] = None
    column_info: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'QueryCodePair':
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ColumnContext:
    """Column metadata with statistics and samples"""
    name: str
    dtype: str
    null_count: int
    total_count: int
    unique_count: Optional[int] = None
    sample_values: Optional[List] = None
    statistical_summary: Optional[Dict] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'ColumnContext':
        return cls(**data)

    def to_dict(self) -> Dict:
        return asdict(self)


class VectorStore:
    """
    Vector store for semantic similarity search using fuzzy matching
    Stores query-code pairs and column context for defensive programming
    """

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize vector store with optional persistent storage"""
        self.storage_path = Path(storage_path) if storage_path else None
        self.query_code_pairs: List[QueryCodePair] = []
        self.column_contexts: Dict[str, List[ColumnContext]] = {}
        self._load_from_storage()

    def add_query_code_pair(self, query: str, code: str, success: bool = True,
                           execution_time: Optional[float] = None,
                           result_type: Optional[str] = None,
                           column_info: Optional[Dict] = None) -> None:
        """Add a query-code pair to the vector store"""
        query_hash = self._hash_query(query)

        pair = QueryCodePair(
            query=query,
            code=code,
            query_hash=query_hash,
            success=success,
            execution_time=execution_time,
            result_type=result_type,
            column_info=column_info
        )

        # Remove existing pair with same hash if exists
        self.query_code_pairs = [p for p in self.query_code_pairs if p.query_hash != query_hash]
        self.query_code_pairs.append(pair)

        # Keep only last 100 pairs to manage memory
        if len(self.query_code_pairs) > 100:
            self.query_code_pairs = self.query_code_pairs[-100:]

        self._save_to_storage()

    def add_column_context(self, dataframe_name: str, columns: List[ColumnContext]) -> None:
        """Add column context for a dataframe"""
        self.column_contexts[dataframe_name] = columns
        self._save_to_storage()

    def find_similar_queries(self, query: str, top_k: int = 3,
                           success_only: bool = True, min_similarity: float = 60.0) -> List[QueryCodePair]:
        """Find similar queries using fuzzy matching"""
        if not self.query_code_pairs:
            return []

        # Filter by success if requested
        candidates = self.query_code_pairs
        if success_only:
            candidates = [p for p in candidates if p.success]

        if not candidates:
            return []

        # Use rapidfuzz for similarity matching
        query_texts = [p.query for p in candidates]
        matches = process.extract(
            query,
            query_texts,
            scorer=fuzz.WRatio,
            limit=top_k
        )

        # Filter by minimum similarity and return corresponding pairs
        similar_pairs = []
        for match_text, similarity, _ in matches:
            if similarity >= min_similarity:
                # Find the corresponding QueryCodePair
                pair = next(p for p in candidates if p.query == match_text)
                similar_pairs.append(pair)

        return similar_pairs

    def get_column_context_for_dataframes(self, dataframe_names: List[str]) -> Dict[str, List[ColumnContext]]:
        """Get column context for specified dataframes"""
        return {name: self.column_contexts.get(name, []) for name in dataframe_names if name in self.column_contexts}

    def extract_column_context_from_dataframes(self, dataframes: List, dataframe_names: List[str]) -> None:
        """Extract and store column context from actual dataframes"""
        for i, df in enumerate(dataframes):
            if i < len(dataframe_names):
                df_name = dataframe_names[i]
                columns = self._analyze_dataframe_columns(df)
                self.add_column_context(df_name, columns)

    def _analyze_dataframe_columns(self, df) -> List[ColumnContext]:
        """Analyze dataframe columns and extract context"""
        columns = []

        try:
            # Handle different dataframe types (pandas, etc.)
            if hasattr(df, 'columns') and hasattr(df, 'dtypes'):
                for col in df.columns:
                    try:
                        dtype = str(df[col].dtype)
                        null_count = int(df[col].isnull().sum()) if hasattr(df[col], 'isnull') else 0
                        total_count = len(df)

                        # Get unique count safely
                        unique_count = None
                        sample_values = None
                        statistical_summary = None

                        try:
                            unique_count = int(df[col].nunique()) if hasattr(df[col], 'nunique') else None
                        except Exception:
                            pass

                        # Get sample values (first 5 non-null unique values)
                        try:
                            if hasattr(df[col], 'dropna'):
                                samples = df[col].dropna().unique()[:5].tolist()
                                sample_values = [str(s) for s in samples]
                        except Exception:
                            pass

                        # Get statistical summary for numeric columns
                        try:
                            if hasattr(df[col], 'describe') and df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                                desc = df[col].describe()
                                statistical_summary = {
                                    'mean': float(desc['mean']) if 'mean' in desc else None,
                                    'std': float(desc['std']) if 'std' in desc else None,
                                    'min': float(desc['min']) if 'min' in desc else None,
                                    'max': float(desc['max']) if 'max' in desc else None,
                                    'median': float(desc['50%']) if '50%' in desc else None
                                }
                        except Exception:
                            pass

                        column_context = ColumnContext(
                            name=str(col),
                            dtype=dtype,
                            null_count=null_count,
                            total_count=total_count,
                            unique_count=unique_count,
                            sample_values=sample_values,
                            statistical_summary=statistical_summary
                        )
                        columns.append(column_context)

                    except Exception as e:
                        # Create minimal context if analysis fails
                        column_context = ColumnContext(
                            name=str(col),
                            dtype="unknown",
                            null_count=0,
                            total_count=len(df) if hasattr(df, '__len__') else 0
                        )
                        columns.append(column_context)
        except Exception as e:
            # Return empty list if dataframe analysis fails
            pass

        return columns

    def generate_few_shot_context(self, query: str, top_k: int = 3) -> str:
        """Generate few-shot prompting context for similar queries"""
        similar_pairs = self.find_similar_queries(query, top_k)

        if not similar_pairs:
            return ""

        context_parts = ["# SIMILAR QUERY EXAMPLES:"]

        for i, pair in enumerate(similar_pairs, 1):
            context_parts.extend([
                f"\n## Example {i}:",
                f"Query: {pair.query}",
                f"Code:",
                "```python",
                pair.code,
                "```"
            ])

            if pair.result_type:
                context_parts.append(f"Result Type: {pair.result_type}")

        return "\n".join(context_parts)

    def generate_column_context(self, dataframe_names: List[str]) -> str:
        """Generate defensive programming context with column information"""
        column_contexts = self.get_column_context_for_dataframes(dataframe_names)

        if not any(column_contexts.values()):
            return ""

        context_parts = ["# DATAFRAME COLUMN CONTEXT:"]

        for df_name, columns in column_contexts.items():
            if not columns:
                continue

            context_parts.extend([
                f"\n## {df_name}:",
                "Columns:"
            ])

            for col in columns:
                col_info = f"- {col.name} ({col.dtype}): {col.total_count - col.null_count}/{col.total_count} non-null"

                if col.unique_count is not None:
                    col_info += f", {col.unique_count} unique"

                if col.sample_values:
                    sample_str = ", ".join(str(v) for v in col.sample_values[:3])
                    col_info += f", samples: [{sample_str}]"

                if col.statistical_summary and any(v is not None for v in col.statistical_summary.values()):
                    stats = col.statistical_summary
                    if stats.get('mean') is not None:
                        col_info += f", mean: {stats['mean']:.2f}"
                    if stats.get('min') is not None and stats.get('max') is not None:
                        col_info += f", range: [{stats['min']:.2f}, {stats['max']:.2f}]"

                context_parts.append(col_info)

        context_parts.extend([
            "\nUse this information to write defensive code that:",
            "- Handles missing values appropriately",
            "- Validates column existence before use",
            "- Uses appropriate data types for operations",
            "- Considers data ranges and constraints"
        ])

        return "\n".join(context_parts)

    def _hash_query(self, query: str) -> str:
        """Generate hash for query deduplication"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()[:12]

    def _save_to_storage(self) -> None:
        """Save vector store to persistent storage"""
        if not self.storage_path:
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "query_code_pairs": [pair.to_dict() for pair in self.query_code_pairs],
                "column_contexts": {k: [col.to_dict() for col in v] for k, v in self.column_contexts.items()}
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Silently fail if storage is not available
            pass

    def _load_from_storage(self) -> None:
        """Load vector store from persistent storage"""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Load query-code pairs
            self.query_code_pairs = [QueryCodePair.from_dict(pair_data)
                                   for pair_data in data.get("query_code_pairs", [])]

            # Load column contexts
            self.column_contexts = {}
            for df_name, cols_data in data.get("column_contexts", {}).items():
                self.column_contexts[df_name] = [ColumnContext.from_dict(col_data)
                                               for col_data in cols_data]
        except Exception:
            # Start fresh if loading fails
            self.query_code_pairs = []
            self.column_contexts = {}