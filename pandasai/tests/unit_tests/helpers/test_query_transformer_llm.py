import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

if "pandasai.__version__" not in sys.modules:
    stub_version = types.ModuleType("pandasai.__version__")
    stub_version.__version__ = "0.0.0"
    sys.modules["pandasai.__version__"] = stub_version

sys.modules.setdefault("openai", types.ModuleType("openai"))
pandas_stub = types.ModuleType("pandas")
pandas_stub.DataFrame = type("DataFrame", (), {})
pandas_stub.Series = type("Series", (), {})
sys.modules.setdefault("pandas", pandas_stub)
_pandas_util = types.ModuleType("pandas.util")
_pandas_util_version = types.ModuleType("pandas.util.version")


class _DummyVersion:
    def __init__(self, version: str):
        self.version = version


_pandas_util_version.Version = _DummyVersion
_pandas_util.version = _pandas_util_version
sys.modules.setdefault("pandas.util", _pandas_util)
sys.modules.setdefault("pandas.util.version", _pandas_util_version)
sys.modules.setdefault("numpy", types.ModuleType("numpy"))
dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)
pydantic_stub = types.ModuleType("pydantic")
pydantic_stub.BaseModel = type("BaseModel", (), {})
pydantic_stub.Field = lambda *args, **kwargs: None
pydantic_stub.PrivateAttr = lambda *args, **kwargs: None
pydantic_stub.ValidationError = type("ValidationError", (Exception,), {})

def _validator_stub(*args, **kwargs):
    def decorator(func):
        return func

    return decorator

pydantic_stub.validator = _validator_stub
sys.modules.setdefault("pydantic", pydantic_stub)
sys.modules.setdefault("pydantic.v1", pydantic_stub)

jinja2_stub = types.ModuleType("jinja2")


class _DummyTemplate:
    def __init__(self, template: str):
        self._template = template

    def render(self, **_kwargs):
        return self._template


class _DummyEnvironment:
    def __init__(self, loader=None):
        self.loader = loader

    def from_string(self, template: str):
        return _DummyTemplate(template)

    def get_template(self, _name: str):
        return _DummyTemplate("")


class _DummyLoader:
    def __init__(self, *args, **kwargs):
        pass


jinja2_stub.Environment = _DummyEnvironment
jinja2_stub.FileSystemLoader = _DummyLoader
sys.modules.setdefault("jinja2", jinja2_stub)
sys.modules.setdefault("matplotlib", types.ModuleType("matplotlib"))
sys.modules.setdefault("matplotlib.pyplot", types.ModuleType("matplotlib.pyplot"))
sys.modules.setdefault("yaml", types.ModuleType("yaml"))
sys.modules.setdefault("duckdb", types.ModuleType("duckdb"))
sys.modules.setdefault("sqlglot", types.ModuleType("sqlglot"))
if "sqlalchemy" not in sys.modules:
    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_stub.asc = lambda *args, **kwargs: None
    sqlalchemy_stub.create_engine = lambda *args, **kwargs: None
    sqlalchemy_stub.select = lambda *args, **kwargs: None
    sqlalchemy_stub.text = lambda *args, **kwargs: None
    sys.modules["sqlalchemy"] = sqlalchemy_stub
    engine_stub = types.ModuleType("sqlalchemy.engine")
    engine_stub.Connection = object
    sys.modules["sqlalchemy.engine"] = engine_stub
sys.modules.setdefault("astor", types.ModuleType("astor"))
sys.modules.setdefault("PIL", types.ModuleType("PIL"))
sys.modules.setdefault("PIL.Image", types.ModuleType("PIL.Image"))

from pandasai.helpers.memory import Memory
from pandasai.helpers.query_transformer import (
    QueryTransformer,
    QueryType,
    TransformationIntent,
)
from pandasai.pipelines.chat.query_transformation import QueryTransformationUnit
from pandasai.pipelines.pipeline_context import PipelineContext
from pandasai.llm.base import LLM
from pandasai.llm.fake import FakeLLM
from pandasai.prompts.query_transformation_prompt import QueryTransformationPrompt


class HarmonyAwareLLM(LLM):
    """LLM stub that captures Harmony vs legacy prompt usage."""

    def __init__(self, output: str):
        self._output = output
        self.messages = None

    def call(self, instruction, context=None):
        if context and context.config.use_harmony_format:
            harmony_messages = instruction.to_harmony_messages(context)
            current_query = context.get("current_user_query")
            if current_query:
                harmony_messages.add_user_message(current_query)
            self.messages = harmony_messages.get_messages_for_llm()
        else:
            self.messages = instruction.to_string()
        return self._output

    @property
    def type(self) -> str:  # pragma: no cover - simple property
        return "harmony-aware"


class DummyConfig:
    """Minimal config stub for PipelineContext tests."""

    def __init__(self, *, llm: LLM, use_harmony_format: bool):
        self.llm = llm
        self.use_harmony_format = use_harmony_format
        self.enable_cache = False
        self.enable_query_transformation = True
        self.query_transformation_mode = "default"
        self.harmony_reasoning_levels = {
            "code_generation": "high",
            "error_correction": "medium",
            "explanation": "low",
            "clarification": "low",
            "query_transformation": "medium",
            "default": "medium",
        }
        self.direct_sql = False
        self.data_viz_library = ""


class SequencedLLM(LLM):
    """LLM stub that yields predefined responses for successive calls."""

    def __init__(self, outputs):
        self._outputs = list(outputs)
        self.last_prompt = None

    def call(self, instruction, context=None):
        self.last_prompt = instruction.to_string()
        if not self._outputs:
            raise RuntimeError("SequencedLLM received more calls than expected")
        return self._outputs.pop(0)

    @property
    def type(self) -> str:  # pragma: no cover - simple property
        return "sequenced"


def test_transform_final_without_tool_call():
    response = """```json
    {
      "action": "final",
      "transformed_query": "Calculate mean of sales",
      "query_type": "statistical",
      "intent": "enhance_clarity",
      "confidence": 0.88,
      "reasoning": "Normalized terminology",
      "metadata": {"user_hints": "Mapped average->mean"}
    }
    ```"""

    llm = FakeLLM(output=response)
    transformer = QueryTransformer(llm, confidence_threshold=0.5)

    result = transformer.transform(
        "What is the average sales?",
        {"available_columns": ["sales"], "dataframe_count": 1},
    )

    assert result.transformed_query == "Calculate mean of sales"
    assert result.query_type == QueryType.STATISTICAL
    assert result.intent_level == TransformationIntent.ENHANCE_CLARITY
    assert result.should_apply_transformation() is True
    assert result.metadata["llm_reasoning"] == "Normalized terminology"


def test_transform_executes_tool_call():
    tool_request = """```json
    {
      "action": "call_tool",
      "tool_name": "rapidfuzz_similarity",
      "tool_args": {"query": "rev", "choices": ["revenue", "sales"]},
      "thought": "Match schema column for 'rev'"
    }
    ```"""

    final_response = """```json
    {
      "action": "final",
      "transformed_query": "Show revenue statistics",
      "query_type": "statistical",
      "intent": "optimize_structure",
      "confidence": 0.92,
      "reasoning": "Aligned partial token to revenue column",
      "metadata": {
        "column_alignment": [{"query": "rev", "match": "revenue", "score": 99.0}]
      }
    }
    ```"""

    llm = SequencedLLM([tool_request, final_response])

    with patch("pandasai.helpers.query_transformer.process") as mock_process, \
        patch("pandasai.helpers.query_transformer.fuzz") as mock_fuzz:

        mock_process.extract.return_value = [("revenue", 99.0, None)]
        mock_fuzz.token_sort_ratio = MagicMock(return_value=99.0)

        transformer = QueryTransformer(llm, max_tool_iterations=1)
        result = transformer.transform(
            "rev stats",
            {"available_columns": ["sales", "revenue"], "dataframe_count": 1},
        )

    assert result.transformed_query == "Show revenue statistics"
    assert result.metadata["tool_invocations"]
    assert result.metadata["tool_invocations"][0]["name"] == "rapidfuzz_similarity"
    mock_process.extract.assert_called_once()
    assert result.metadata["final_payload"]["query_type"] == "statistical"


def test_transform_falls_back_when_final_missing():
    tool_request = """```json
    {
      "action": "call_tool",
      "tool_name": "rapidfuzz_similarity",
      "tool_args": {"query": "col", "choices": []}
    }
    ```"""

    llm = SequencedLLM([tool_request])
    transformer = QueryTransformer(llm, max_tool_iterations=0)

    result = transformer.transform("original", {"available_columns": []})

    assert result.transformed_query == "original"
    assert result.confidence_score == 0.0
    assert result.intent_level == TransformationIntent.PRESERVE_EXACT


def test_query_transformation_prompt_harmony_messages_include_history():
    memory = Memory(memory_size=6)
    memory.add_without_errors("Show me the revenue trend", True)
    memory.add_without_errors("Provided summary of revenue trend", False)

    config = DummyConfig(llm=FakeLLM(), use_harmony_format=True)
    context = PipelineContext(dfs=[], config=config, memory=memory)

    prompt = QueryTransformationPrompt(
        context=context,
        query="How about growth?",
        column_inventory=["revenue", "sales", "growth_rate"],
        dataframe_count=1,
        tool_invocations=[{"name": "rapidfuzz_similarity", "args": {"query": "rev"}, "result": {"engine": "rapidfuzz"}}],
        config={
            "confidence_threshold": 0.8,
            "max_tool_iterations": 2,
            "column_limit": 2,
        },
    )

    harmony_messages = prompt.to_harmony_messages(context)

    system_messages = harmony_messages.get_system_messages()
    assert len(system_messages) >= 4

    conversation = harmony_messages.get_conversation_only()
    assert conversation
    assert conversation[0].role == "user"
    assert "revenue trend" in conversation[0].content


def test_query_transformation_unit_harmony_flow_uses_messages_and_sets_query():
    response = """```json
    {
      "action": "final",
      "transformed_query": "What is the total sales?",
      "query_type": "aggregation",
      "intent": "enhance_clarity",
      "confidence": 0.8,
      "reasoning": "Normalized terminology",
      "metadata": {}
    }
    ```"""

    llm = HarmonyAwareLLM(response)
    transformer = QueryTransformer(llm, confidence_threshold=0.5)

    config = DummyConfig(llm=llm, use_harmony_format=True)
    memory = Memory(memory_size=5)
    memory.add_without_errors("Show me the revenue", True)
    memory.add_without_errors("Here is the revenue summary", False)
    context = PipelineContext(dfs=[], config=config, memory=memory)

    class StubLogger:
        def log(self, *_args, **_kwargs):
            pass

    unit = QueryTransformationUnit(transformer=transformer)
    input_payload = SimpleNamespace(query="What is the sales growth?")

    unit.execute(input_payload, context=context, logger=StubLogger())

    assert context.get("current_user_query") == "What is the sales growth?"
    assert isinstance(llm.messages, list)
    assert any(
        msg["role"] == "user" and "Show me the revenue" in msg["content"]
        for msg in llm.messages
    )
    assert any(
        msg["role"] == "user" and "What is the sales growth?" in msg["content"]
        for msg in llm.messages
    )


def test_query_transformation_unit_respects_legacy_prompt_format():
    response = """```json
    {
      "action": "final",
      "transformed_query": "Show revenue summary",
      "query_type": "descriptive",
      "intent": "preserve_exact",
      "confidence": 0.6,
      "reasoning": "No change needed",
      "metadata": {}
    }
    ```"""

    llm = HarmonyAwareLLM(response)
    transformer = QueryTransformer(llm, confidence_threshold=0.5)

    config = DummyConfig(llm=llm, use_harmony_format=False)
    context = PipelineContext(dfs=[], config=config, memory=Memory())

    class StubLogger:
        def log(self, *_args, **_kwargs):
            pass

    unit = QueryTransformationUnit(transformer=transformer)
    input_payload = SimpleNamespace(query="Show revenue summary")

    unit.execute(input_payload, context=context, logger=StubLogger())

    assert isinstance(llm.messages, str)
    assert context.get("query_transformation_prompt_format") == "legacy"
