"""Example usage of GPT-OSS models with LiteLLM and Harmony Chat Format

This example demonstrates how to use the refactored pandas-ai solution with
gpt-oss models for optimal performance using the Harmony Chat Format.
"""

import pandas as pd
from pandasai import SmartDataframe
from pandasai.llm import LiteLLM, ModelConfig, create_gpt_oss_llm


def example_basic_gpt_oss():
    """Basic example using gpt-oss with helper function."""
    
    # Sample data
    data = {
        'country': ['United States', 'United Kingdom', 'France', 'Germany', 'Italy', 'Spain', 'Canada'],
        'gdp': [19294482071552, 2891615567872, 2411255037952, 3435817336832, 1745433788416, 1189406496768, 1609972147712],
        'happiness_index': [6.94, 7.16, 6.66, 7.07, 6.38, 6.4, 7.23]
    }
    df = pd.DataFrame(data)
    
    # Create gpt-oss LLM using helper function
    llm = create_gpt_oss_llm(
        model="gpt-oss-120b",
        reasoning_level="high",  # Use maximum reasoning for complex analysis
        available_tools=["python", "data_analysis"],
        persona="You are an expert data analyst with deep knowledge of economic indicators and statistical analysis."
    )
    
    # Create smart dataframe
    sdf = SmartDataframe(df, config={"llm": llm})
    
    # Query with complex analysis
    response = sdf.chat("What is the correlation between GDP and happiness index? Provide statistical insights.")
    print(f"GPT-OSS Response: {response}")


def example_manual_configuration():
    """Example with manual configuration for advanced use cases."""
    
    # Sample sales data
    sales_data = {
        'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'product_a': [100, 120, 140, 110, 160, 180],
        'product_b': [80, 90, 120, 140, 130, 150],
        'region': ['North', 'South', 'East', 'West', 'North', 'South']
    }
    df = pd.DataFrame(sales_data)
    
    # Create advanced configuration
    config = ModelConfig(
        reasoning_level="high",
        available_tools=["python", "visualization", "statistical_analysis"],
        persona="You are a senior business analyst specializing in sales performance and trend analysis.",
        function_schemas=[
            {
                "name": "create_visualization",
                "description": "Create charts and graphs for data visualization",
                "parameters": {
                    "chart_type": {"type": "string", "enum": ["bar", "line", "scatter"]},
                    "data_columns": {"type": "array", "items": {"type": "string"}}
                }
            }
        ],
        task_context="Focus on identifying trends and providing actionable business insights."
    )
    
    # Create LiteLLM with manual configuration
    llm = LiteLLM(
        model="gpt-oss-20b",  # Using smaller model for this example
        config=config,
        temperature=0.1,  # Lower temperature for more consistent analysis
        max_tokens=2000
    )
    
    # Create smart dataframe
    sdf = SmartDataframe(df, config={"llm": llm})
    
    # Multi-turn conversation example
    print("=== Multi-turn Conversation Example ===")
    
    # First query
    response1 = sdf.chat("Analyze the sales trends for both products over the months.")
    print(f"First Response: {response1}")
    
    # Follow-up query (will use pruned context)
    response2 = sdf.chat("Which product shows better growth potential?")
    print(f"Follow-up Response: {response2}")


def example_model_comparison():
    """Example comparing different model configurations."""
    
    # Sample data
    data = {
        'category': ['A', 'B', 'C', 'D'],
        'values': [25, 30, 35, 40],
        'scores': [8.5, 7.2, 9.1, 6.8]
    }
    df = pd.DataFrame(data)
    
    # GPT-OSS with high reasoning
    gpt_oss_high = create_gpt_oss_llm(
        model="gpt-oss-120b",
        reasoning_level="high"
    )
    
    # GPT-OSS with medium reasoning (faster)
    gpt_oss_medium = create_gpt_oss_llm(
        model="gpt-oss-20b",
        reasoning_level="medium"
    )
    
    # Standard OpenAI model for comparison
    standard_config = ModelConfig()  # Uses OpenAI adapter
    standard_llm = LiteLLM(model="gpt-4o-mini", config=standard_config)
    
    query = "What patterns do you see in this data?"
    
    print("=== Model Comparison ===")
    
    # Test with different configurations
    for name, llm in [
        ("GPT-OSS-120b (High Reasoning)", gpt_oss_high),
        ("GPT-OSS-20b (Medium Reasoning)", gpt_oss_medium),
        ("GPT-4o-mini (Standard)", standard_llm)
    ]:
        print(f"\n--- {name} ---")
        sdf = SmartDataframe(df, config={"llm": llm})
        try:
            response = sdf.chat(query)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")


def example_dynamic_configuration():
    """Example showing dynamic configuration updates."""
    
    data = {'x': [1, 2, 3, 4, 5], 'y': [2, 4, 6, 8, 10]}
    df = pd.DataFrame(data)
    
    # Create LLM with initial config
    llm = create_gpt_oss_llm(reasoning_level="medium")
    sdf = SmartDataframe(df, config={"llm": llm})
    
    print("=== Dynamic Configuration Example ===")
    
    # First query with medium reasoning
    response1 = sdf.chat("What's the relationship between x and y?")
    print(f"Medium Reasoning: {response1}")
    
    # Update configuration for more detailed analysis
    llm.update_config(
        reasoning_level="high",
        task_context="Provide detailed mathematical analysis including equations and R-squared values."
    )
    
    # Second query with high reasoning
    response2 = sdf.chat("Provide a detailed statistical analysis of this relationship.")
    print(f"High Reasoning: {response2}")


if __name__ == "__main__":
    print("Testing GPT-OSS integration with pandas-ai")
    
    try:
        # Run examples (comment out any that you don't want to test)
        example_basic_gpt_oss()
        print("\n" + "="*50 + "\n")
        
        example_manual_configuration()
        print("\n" + "="*50 + "\n")
        
        example_model_comparison()
        print("\n" + "="*50 + "\n")
        
        example_dynamic_configuration()
        
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install litellm: pip install litellm")
    except Exception as e:
        print(f"Error running examples: {e}")
        print("Make sure you have set your API keys in environment variables.")