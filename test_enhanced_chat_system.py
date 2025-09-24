"""
Production-grade tests for the enhanced chat system with Harmony format improvements
Tests cover all new features: f-strings, market commentary, vector store, fuzzy matching, and configuration
"""
import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the components to test
from pandasai.helpers.vector_store import VectorStore, QueryCodePair, ColumnContext
from pandasai.helpers.harmony_config import HarmonyFormatSettings, HarmonyConfigManager, ResponseStyle, ReasoningLevel
from pandasai.helpers.harmony_messages import HarmonyMessages, HarmonyMessagesBuilder
from pandasai.pipelines.chat.market_commentary import MarketCommentary
from pandasai.pipelines.logic_unit_output import LogicUnitOutput


class TestVectorStore:
    """Test cases for VectorStore functionality"""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for testing"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def vector_store(self, temp_storage):
        """Create VectorStore instance for testing"""
        return VectorStore(temp_storage)

    def test_vector_store_initialization(self):
        """Test VectorStore initialization"""
        store = VectorStore()
        assert store.query_code_pairs == []
        assert store.column_contexts == {}

    def test_add_query_code_pair(self, vector_store):
        """Test adding query-code pairs"""
        vector_store.add_query_code_pair(
            query="What is the mean of column A?",
            code="result = {'type': 'number', 'value': df['A'].mean()}",
            success=True,
            result_type="number"
        )

        assert len(vector_store.query_code_pairs) == 1
        pair = vector_store.query_code_pairs[0]
        assert pair.query == "What is the mean of column A?"
        assert pair.success is True
        assert pair.result_type == "number"

    def test_find_similar_queries(self, vector_store):
        """Test fuzzy matching for similar queries"""
        # Add some test data
        vector_store.add_query_code_pair("Calculate mean of sales", "df['sales'].mean()", True)
        vector_store.add_query_code_pair("Show total revenue", "df['revenue'].sum()", True)
        vector_store.add_query_code_pair("Average of prices", "df['price'].mean()", True)

        # Test finding similar queries
        similar = vector_store.find_similar_queries("Calculate average sales", top_k=2)

        assert len(similar) > 0
        # Should find the "Calculate mean of sales" as most similar
        assert any("sales" in pair.query.lower() for pair in similar)

    def test_column_context_extraction(self, vector_store):
        """Test column context extraction from dataframes"""
        # Create mock dataframe
        mock_df = Mock()
        mock_df.columns = ['A', 'B', 'C']
        mock_df.dtypes = {'A': 'int64', 'B': 'float64', 'C': 'object'}
        mock_df.__len__ = Mock(return_value=100)

        # Mock column operations
        mock_col_a = Mock()
        mock_col_a.dtype = 'int64'
        mock_col_a.isnull.return_value.sum.return_value = 5
        mock_col_a.nunique.return_value = 50
        mock_col_a.dropna.return_value.unique.return_value[:5] = [1, 2, 3, 4, 5]

        mock_df.__getitem__ = Mock(return_value=mock_col_a)

        # Test extraction
        columns = vector_store._analyze_dataframe_columns(mock_df)

        assert len(columns) == 3
        assert all(isinstance(col, ColumnContext) for col in columns)
        assert columns[0].name == 'A'

    def test_few_shot_context_generation(self, vector_store):
        """Test few-shot context generation"""
        # Add test data
        vector_store.add_query_code_pair(
            "Calculate sum of sales",
            "result = {'type': 'number', 'value': df['sales'].sum()}",
            True,
            result_type="number"
        )

        context = vector_store.generate_few_shot_context("Sum up the sales data")

        assert "SIMILAR QUERY EXAMPLES" in context
        assert "Calculate sum of sales" in context
        assert "df['sales'].sum()" in context

    def test_persistence(self, temp_storage):
        """Test data persistence to file"""
        # Create store and add data
        store1 = VectorStore(temp_storage)
        store1.add_query_code_pair("test query", "test code", True)

        # Create new store from same file
        store2 = VectorStore(temp_storage)
        assert len(store2.query_code_pairs) == 1
        assert store2.query_code_pairs[0].query == "test query"


class TestHarmonyConfig:
    """Test cases for Harmony configuration system"""

    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_default_settings(self):
        """Test default configuration settings"""
        settings = HarmonyFormatSettings()

        assert settings.enable_f_string_enforcement is True
        assert settings.enable_market_commentary is True
        assert settings.response_style == ResponseStyle.CONVERSATIONAL
        assert settings.default_reasoning_level == ReasoningLevel.MEDIUM

    def test_response_style_prompts(self):
        """Test different response style prompts"""
        settings = HarmonyFormatSettings()

        # Test business style
        settings.response_style = ResponseStyle.BUSINESS
        prompt = settings.get_response_style_prompt()
        assert "business" in prompt.lower()

        # Test technical style
        settings.response_style = ResponseStyle.TECHNICAL
        prompt = settings.get_response_style_prompt()
        assert "technical" in prompt.lower()

    def test_custom_messages(self):
        """Test custom system messages"""
        settings = HarmonyFormatSettings()
        custom_identity = "You are a specialized financial analyst."

        settings.custom_core_identity = custom_identity
        assert settings.get_core_identity_message() == custom_identity

    def test_config_serialization(self):
        """Test configuration serialization and deserialization"""
        settings = HarmonyFormatSettings()
        settings.response_style = ResponseStyle.BUSINESS
        settings.enable_f_string_enforcement = False

        # Serialize
        data = settings.to_dict()
        assert data['response_style'] == 'business'
        assert data['enable_f_string_enforcement'] is False

        # Deserialize
        new_settings = HarmonyFormatSettings.from_dict(data)
        assert new_settings.response_style == ResponseStyle.BUSINESS
        assert new_settings.enable_f_string_enforcement is False

    def test_config_manager(self, temp_config_file):
        """Test configuration manager"""
        manager = HarmonyConfigManager(temp_config_file)

        # Update settings
        manager.set_response_style(ResponseStyle.TECHNICAL)
        manager.enable_feature("market_commentary", False)

        # Get settings
        settings = manager.get_settings()
        assert settings.response_style == ResponseStyle.TECHNICAL
        assert settings.enable_market_commentary is False

        # Test persistence
        new_manager = HarmonyConfigManager(temp_config_file)
        new_settings = new_manager.get_settings()
        assert new_settings.response_style == ResponseStyle.TECHNICAL


class TestHarmonyMessages:
    """Test cases for HarmonyMessages functionality"""

    def test_harmony_messages_creation(self):
        """Test HarmonyMessages basic functionality"""
        messages = HarmonyMessages()

        messages.add_core_identity("Test identity")
        messages.add_task_context("Test context")
        messages.add_safety_guard("Test safety")
        messages.add_output_format("Test format")

        assert len(messages) == 4
        assert len(messages.get_system_messages()) == 4

    def test_conversation_management(self):
        """Test conversation history management"""
        messages = HarmonyMessages()
        messages.add_core_identity("Test identity")
        messages.start_conversation_history()

        messages.add_user_message("Hello")
        messages.add_assistant_message("Hi there")

        conversation = messages.get_conversation_only()
        assert len(conversation) == 2
        assert conversation[0].role == "user"
        assert conversation[1].role == "assistant"

    def test_message_pruning(self):
        """Test conversation pruning"""
        messages = HarmonyMessages()
        messages.add_core_identity("Test identity")
        messages.start_conversation_history()

        # Add many conversation turns
        for i in range(10):
            messages.add_user_message(f"User message {i}")
            messages.add_assistant_message(f"Assistant message {i}")

        # Prune to 2 turns
        messages.prune_conversation(2)

        conversation = messages.get_conversation_only()
        assert len(conversation) == 4  # 2 turns = 4 messages

    def test_harmony_messages_builder(self):
        """Test HarmonyMessagesBuilder functionality"""
        messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="df: 100 rows, 3 columns",
            skills_info="No skills available",
            reasoning_level="high"
        )

        system_messages = messages.get_system_messages()
        assert len(system_messages) >= 3  # At least core, task, safety
        assert any("dataframes" in msg.content.lower() for msg in system_messages)


class TestMarketCommentary:
    """Test cases for Market Commentary pipeline step"""

    @pytest.fixture
    def mock_context(self):
        """Create mock pipeline context"""
        context = Mock()
        context.config = Mock()
        context.config.use_harmony_format = True
        context.config.llm = Mock()
        context.config.llm.chat_completion = Mock(return_value="Generated commentary text")
        context.get = Mock(return_value="test query")
        return context

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger"""
        return Mock()

    def test_market_commentary_enabled(self, mock_context, mock_logger):
        """Test market commentary when enabled"""
        commentary_step = MarketCommentary()

        input_data = {
            "type": "number",
            "value": 42
        }

        result = commentary_step.execute(
            input_data,
            context=mock_context,
            logger=mock_logger
        )

        assert result.success is True
        assert "market_commentary" in result.output
        assert result.output["has_commentary"] is True

    def test_market_commentary_disabled(self, mock_context, mock_logger):
        """Test market commentary when disabled"""
        mock_context.config.use_harmony_format = False

        commentary_step = MarketCommentary()
        input_data = {"type": "number", "value": 42}

        result = commentary_step.execute(
            input_data,
            context=mock_context,
            logger=mock_logger
        )

        assert result.success is True
        # Should skip commentary
        assert "Skipped market commentary" in result.message

    def test_fallback_commentary(self, mock_context, mock_logger):
        """Test fallback commentary generation"""
        # Make LLM fail
        mock_context.config.llm.chat_completion.side_effect = Exception("LLM failed")

        commentary_step = MarketCommentary()

        # Test fallback generation
        fallback = commentary_step._generate_fallback_commentary(
            "df.groupby('category').sum()",
            "Calculate sum by category"
        )

        assert "Analysis performed for" in fallback
        assert "Data grouped for aggregate analysis" in fallback

    def test_next_steps_generation(self, mock_context, mock_logger):
        """Test next steps generation"""
        mock_context.config.enable_next_steps_prompt = True
        mock_context.config.llm.chat_completion = Mock(return_value="1. Step one\n2. Step two")

        commentary_step = MarketCommentary()

        next_steps = commentary_step._generate_next_steps(
            "df.plot()", "Create a visualization", "Chart created", mock_context, mock_logger
        )

        assert "Step one" in next_steps


class TestIntegration:
    """Integration tests for the complete enhanced system"""

    @pytest.fixture
    def mock_pipeline_context(self):
        """Create comprehensive mock pipeline context"""
        context = Mock()
        context.config = Mock()
        context.config.use_harmony_format = True
        context.config.enable_few_shot_prompting = True
        context.config.enable_column_context = True
        context.config.enable_market_commentary = True
        context.config.llm = Mock()
        context.config.llm.chat_completion = Mock(return_value="Generated response")

        context.dfs = [Mock()]  # Mock dataframe
        context.dfs[0].head_csv = "col1,col2\n1,2\n3,4"
        context.dfs[0].columns = ['col1', 'col2']
        context.dfs[0].dtypes = {'col1': 'int64', 'col2': 'int64'}

        context.get = Mock(side_effect=lambda key, default=None: {
            'current_user_query': 'Test query',
            'last_code_generated': 'test_code = 42'
        }.get(key, default))

        return context

    def test_f_string_enforcement_in_template(self):
        """Test that f-string enforcement is properly added to templates"""
        # Read the output format template
        template_path = Path("pandasai/pandasai/helpers/harmony_templates/code_generation/output_format.tmpl")

        if template_path.exists():
            with open(template_path, 'r') as f:
                content = f.read()
            assert "f-strings" in content.lower()
            assert "mandatory" in content.lower()

    @patch('pandasai.helpers.vector_store.VectorStore')
    def test_vector_store_integration(self, mock_vector_store, mock_pipeline_context):
        """Test vector store integration in the pipeline"""
        from pandasai.prompts.generate_python_code import GeneratePythonCodePrompt

        # Setup mock vector store
        mock_store_instance = Mock()
        mock_store_instance.generate_few_shot_context.return_value = "Few shot context"
        mock_store_instance.generate_column_context.return_value = "Column context"
        mock_vector_store.return_value = mock_store_instance

        # Create prompt
        prompt = GeneratePythonCodePrompt(context=mock_pipeline_context)

        # Mock get_reasoning_level method
        prompt.get_reasoning_level = Mock(return_value="medium")

        # Get harmony messages
        messages = prompt.to_harmony_messages(mock_pipeline_context)

        # Verify vector store was used
        mock_store_instance.generate_few_shot_context.assert_called_once()
        mock_store_instance.generate_column_context.assert_called_once()

        # Verify messages contain contexts
        system_messages = messages.get_system_messages()
        task_messages = [msg for msg in system_messages if msg.message_type == "task_context"]

        # Should have task context messages
        assert len(task_messages) > 0

    def test_end_to_end_harmony_workflow(self, mock_pipeline_context):
        """Test complete end-to-end workflow with all enhancements"""
        from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder
        from pandasai.helpers.harmony_config import HarmonyFormatSettings

        # Create settings with all features enabled
        settings = HarmonyFormatSettings(
            enable_f_string_enforcement=True,
            enable_market_commentary=True,
            enable_few_shot_prompting=True,
            enable_column_context=True,
            response_style=ResponseStyle.BUSINESS
        )

        # Build messages
        messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="Test dataframe info",
            harmony_settings=settings
        )

        # Verify settings are applied
        system_messages = messages.get_system_messages()
        core_identity = next((msg for msg in system_messages if msg.message_type == "core_identity"), None)

        assert core_identity is not None
        # Should contain business-focused identity due to settings
        assert any(keyword in core_identity.content.lower()
                  for keyword in ["business", "analyst", "expert"])


def test_defensive_programming_features():
    """Test defensive programming features in column context"""
    # Test column context with null values and statistics
    column = ColumnContext(
        name="sales",
        dtype="float64",
        null_count=10,
        total_count=100,
        unique_count=85,
        sample_values=[100.5, 200.0, 150.75],
        statistical_summary={
            'mean': 175.5,
            'std': 45.2,
            'min': 50.0,
            'max': 500.0,
            'median': 165.0
        }
    )

    # Verify defensive programming information is captured
    assert column.null_count == 10
    assert column.statistical_summary['mean'] == 175.5
    assert len(column.sample_values) == 3


@pytest.mark.parametrize("response_style", list(ResponseStyle))
def test_all_response_styles(response_style):
    """Test all response styles work correctly"""
    settings = HarmonyFormatSettings(response_style=response_style)
    prompt = settings.get_response_style_prompt()

    assert isinstance(prompt, str)
    assert len(prompt) > 0
    # Each style should have relevant keywords
    style_keywords = {
        ResponseStyle.TECHNICAL: ["technical", "statistical", "methods"],
        ResponseStyle.BUSINESS: ["business", "actionable", "impact"],
        ResponseStyle.CONVERSATIONAL: ["friendly", "accessible", "plain"],
        ResponseStyle.ANALYTICAL: ["analytical", "reasoning", "insights"],
        ResponseStyle.EXECUTIVE: ["executive", "strategic", "recommendations"]
    }

    expected_keywords = style_keywords.get(response_style, [])
    assert any(keyword in prompt.lower() for keyword in expected_keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])