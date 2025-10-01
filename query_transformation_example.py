"""
Query Transformation System - Usage Examples

This file demonstrates how to use the query transformation system
in various configurations and scenarios.
"""

import pandas as pd
from pandasai import Agent
from pandasai.schemas.df_config import Config
from pandasai.llm import OpenAI

# ============================================================================
# Example 1: Default Configuration (Recommended for most use cases)
# ============================================================================

def example_default_transformation():
    """
    Use query transformation with default settings.
    Provides balanced transformation with normalization and context enrichment.
    """
    # Sample data
    df = pd.DataFrame({
        'region': ['North', 'South', 'East', 'West', 'North', 'South'],
        'sales': [1000, 1500, 1200, 1800, 1100, 1600],
        'revenue': [2000, 2500, 2200, 2800, 2100, 2600]
    })

    # Configure with default transformation (enabled by default)
    config = Config(
        llm=OpenAI(api_token="your-api-key"),
        enable_query_transformation=True,  # Default: True
        query_transformation_mode="default",  # Default: "default"
        verbose=True
    )

    agent = Agent(df, config=config)

    # These queries will be automatically optimized:

    # Query with synonym (average -> mean)
    result1 = agent.chat("What is the average sales by region?")
    print(f"Result 1: {result1}")

    # Query with informal terminology (total -> sum)
    result2 = agent.chat("Show me the total revenue")
    print(f"Result 2: {result2}")

    # Query with ambiguous reference
    result3 = agent.chat("Calculate the sum of this column")
    print(f"Result 3: {result3}")


# ============================================================================
# Example 2: Conservative Mode (Minimal intervention)
# ============================================================================

def example_conservative_transformation():
    """
    Use conservative transformation mode.
    Best for: Production environments with strict query preservation requirements.
    - Minimal normalization
    - High confidence threshold (0.9)
    - Only applies transformations when extremely confident
    """
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=10),
        'price': [100, 105, 103, 107, 110, 108, 112, 115, 113, 118]
    })

    config = Config(
        llm=OpenAI(api_token="your-api-key"),
        enable_query_transformation=True,
        query_transformation_mode="conservative",  # Conservative mode
        verbose=True
    )

    agent = Agent(df, config=config)

    # With conservative mode, most queries pass through unchanged unless
    # transformation is highly confident
    result = agent.chat("Show me the average price over time")
    print(f"Conservative result: {result}")


# ============================================================================
# Example 3: Aggressive Mode (Maximum optimization)
# ============================================================================

def example_aggressive_transformation():
    """
    Use aggressive transformation mode.
    Best for: Research/exploration with maximum query understanding.
    - Full normalization
    - Context enrichment
    - Lower confidence threshold (0.5)
    - More transformations applied
    """
    df = pd.DataFrame({
        'customer': ['A', 'B', 'C', 'D', 'E'],
        'purchases': [5, 3, 8, 2, 6],
        'lifetime_value': [500, 300, 800, 200, 600]
    })

    config = Config(
        llm=OpenAI(api_token="your-api-key"),
        enable_query_transformation=True,
        query_transformation_mode="aggressive",  # Aggressive mode
        verbose=True
    )

    agent = Agent(df, config=config)

    # Aggressive mode will optimize more aggressively
    result = agent.chat("What's the avg lifetime value?")
    print(f"Aggressive result: {result}")


# ============================================================================
# Example 4: Disabled Transformation (Legacy behavior)
# ============================================================================

def example_disabled_transformation():
    """
    Disable query transformation entirely.
    Best for: Debugging or when exact query preservation is critical.
    """
    df = pd.DataFrame({
        'x': [1, 2, 3, 4, 5],
        'y': [2, 4, 6, 8, 10]
    })

    config = Config(
        llm=OpenAI(api_token="your-api-key"),
        enable_query_transformation=False,  # Disabled
        verbose=True
    )

    agent = Agent(df, config=config)

    # Queries will be processed exactly as written
    result = agent.chat("Calculate average of x")
    print(f"No transformation result: {result}")


# ============================================================================
# Example 5: Multi-DataFrame Context
# ============================================================================

def example_multi_dataframe():
    """
    Query transformation with multiple dataframes.
    Demonstrates context-aware transformation with dataframe detection.
    """
    df1 = pd.DataFrame({
        'product': ['A', 'B', 'C'],
        'price': [10, 20, 15]
    })

    df2 = pd.DataFrame({
        'product': ['A', 'B', 'C'],
        'quantity': [100, 200, 150]
    })

    config = Config(
        llm=OpenAI(api_token="your-api-key"),
        enable_query_transformation=True,
        verbose=True
    )

    agent = Agent([df1, df2], config=config)

    # Transformer will detect multi-dataframe context and add hints
    result = agent.chat("What is the average price?")
    print(f"Multi-dataframe result: {result}")


# ============================================================================
# Example 6: Programmatic Access to Transformation Details
# ============================================================================

def example_transformation_metadata():
    """
    Access transformation metadata for debugging or monitoring.
    """
    from pandasai.helpers.query_transformer import (
        QueryTransformer,
        QueryTransformerFactory
    )

    # Create transformer
    transformer = QueryTransformerFactory.create_default()

    # Transform query with context
    context_metadata = {
        "available_columns": ["sales", "revenue", "profit"],
        "dataframe_count": 1
    }

    result = transformer.transform(
        "What is the average sales?",
        context_metadata
    )

    # Access transformation details
    print(f"Original Query: {result.original_query}")
    print(f"Transformed Query: {result.transformed_query}")
    print(f"Query Type: {result.query_type.value}")
    print(f"Intent Level: {result.intent_level.value}")
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Should Apply: {result.should_apply_transformation()}")
    print(f"Pipeline Query: {result.get_query_for_pipeline()}")
    print(f"Metadata: {result.metadata}")


# ============================================================================
# Example 7: Custom Transformer Configuration
# ============================================================================

def example_custom_transformer():
    """
    Create custom transformer with specific settings.
    """
    from pandasai.helpers.query_transformer import (
        QueryTransformer,
        QueryTransformerFactory
    )

    # Create custom transformer
    custom_config = {
        "enable_normalization": True,
        "enable_context_enrichment": False,  # Disable context enrichment
        "enable_ambiguity_resolution": True,
        "confidence_threshold": 0.75  # Custom threshold
    }

    transformer = QueryTransformerFactory.create_from_config(custom_config)

    # Use in transformation
    result = transformer.transform("Calculate average of sales")
    print(f"Custom transformer result: {result.transformed_query}")


# ============================================================================
# Example 8: Integration with Harmony Format
# ============================================================================

def example_with_harmony_format():
    """
    Use query transformation together with Harmony format.
    Demonstrates the complete enhanced chat system.
    """
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=30),
        'stock_price': [100 + i * 2 + (i % 3) for i in range(30)]
    })

    config = Config(
        llm=OpenAI(api_token="your-api-key"),
        # Enable both query transformation and Harmony format
        enable_query_transformation=True,
        query_transformation_mode="default",
        use_harmony_format=True,  # Harmony format enabled
        verbose=True
    )

    agent = Agent(df, config=config)

    # Query transformation will optimize the query first,
    # then Harmony format will structure the LLM conversation
    result = agent.chat("Show me the trend in stock prices over time")
    print(f"Harmony + Transformation result: {result}")


# ============================================================================
# Example 9: A/B Testing Different Modes
# ============================================================================

def example_mode_comparison():
    """
    Compare results across different transformation modes.
    Useful for understanding impact and tuning settings.
    """
    df = pd.DataFrame({
        'category': ['A', 'B', 'A', 'B', 'A'],
        'value': [10, 20, 15, 25, 12]
    })

    query = "What is the average value by category?"

    modes = ["conservative", "default", "aggressive"]
    results = {}

    for mode in modes:
        config = Config(
            llm=OpenAI(api_token="your-api-key"),
            query_transformation_mode=mode,
            verbose=False
        )

        agent = Agent(df, config=config)
        result = agent.chat(query)
        results[mode] = result

    # Compare results
    print("Mode Comparison:")
    for mode, result in results.items():
        print(f"{mode.upper()}: {result}")


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Query Transformation System - Examples")
    print("=" * 80)

    print("\n--- Example 1: Default Configuration ---")
    # example_default_transformation()  # Uncomment to run

    print("\n--- Example 2: Conservative Mode ---")
    # example_conservative_transformation()  # Uncomment to run

    print("\n--- Example 3: Aggressive Mode ---")
    # example_aggressive_transformation()  # Uncomment to run

    print("\n--- Example 4: Disabled Transformation ---")
    # example_disabled_transformation()  # Uncomment to run

    print("\n--- Example 5: Multi-DataFrame Context ---")
    # example_multi_dataframe()  # Uncomment to run

    print("\n--- Example 6: Transformation Metadata ---")
    example_transformation_metadata()  # This one doesn't need API key

    print("\n--- Example 7: Custom Transformer ---")
    example_custom_transformer()  # This one doesn't need API key

    print("\n--- Example 8: With Harmony Format ---")
    # example_with_harmony_format()  # Uncomment to run

    print("\n--- Example 9: Mode Comparison ---")
    # example_mode_comparison()  # Uncomment to run

    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80)
