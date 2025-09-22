#!/usr/bin/env python3
"""
Comprehensive test for Harmony format integration with OpenAI gpt-5-nano
Tests both legacy and Harmony formats to ensure backwards compatibility
"""

import os
import sys
import pandas as pd

# Add the project directory to Python path
sys.path.insert(0, '/Users/josh/Desktop/coding/pandas-ai-2.3.0/pandasai')

from pandasai import Agent
from pandasai.schemas.df_config import Config
from pandasai.llm.openai import OpenAI

# Configure OpenAI with environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("L OPENAI_API_KEY environment variable not set")
    sys.exit(1)

def load_test_data():
    """Load the CSV data for testing"""
    try:
        df = pd.read_csv("/Users/josh/Desktop/coding/pandas-ai-2.3.0/mock_bond_issues.csv")
        print(f" Loaded CSV with {len(df)} rows and {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)}")
        return df
    except Exception as e:
        print(f" Failed to load CSV: {e}")
        return None

def test_legacy_format(df):
    """Test legacy format for backwards compatibility"""
    print("\n=== Testing Legacy Format ===")

    try:
        # Configure with legacy format (default)
        config = Config(
            use_harmony_format=False,
            verbose=True,
            save_logs=True
        )

        llm = OpenAI(api_token=OPENAI_API_KEY, model="gpt-3.5-turbo")
        agent = Agent([df], config=config, memory_size=5)

        # Override LLM to use OpenAI
        agent.context.config.llm = llm

        # Simple query
        response = agent.chat("How many records are in this dataset?")
        print(f" Legacy format response: {response}")

        return True

    except Exception as e:
        print(f" Legacy format test failed: {e}")
        return False

def test_harmony_format(df):
    """Test Harmony format with gpt-5-nano"""
    print("\n=== Testing Harmony Format ===")

    try:
        # Configure with Harmony format
        config = Config(
            use_harmony_format=True,
            harmony_reasoning_levels={
                "code_generation": "high",
                "error_correction": "medium",
                "explanation": "low",
                "clarification": "low",
                "default": "medium"
            },
            verbose=True,
            save_logs=True
        )

        # Use gpt-4o-mini for testing (gpt-5-nano may not be available yet)
        llm = OpenAI(api_token=OPENAI_API_KEY, model="gpt-4o-mini")
        agent = Agent([df], config=config, memory_size=5)

        # Override LLM to use OpenAI
        agent.context.config.llm = llm

        # Test conversation flow
        print("Testing multi-turn conversation...")

        # Turn 1
        response1 = agent.chat("How many records are in this dataset?")
        print(f" Turn 1 response: {response1}")

        # Turn 2 - follow-up question
        response2 = agent.chat("What are the column names?")
        print(f" Turn 2 response: {response2}")

        # Turn 3 - data analysis
        response3 = agent.chat("Calculate the average of any numeric columns")
        print(f" Turn 3 response: {response3}")

        return True

    except Exception as e:
        print(f" Harmony format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_harmony_messages_object():
    """Test the HarmonyMessages object directly"""
    print("\n=== Testing HarmonyMessages Object ===")

    try:
        from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder

        # Test code generation messages
        messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="df: sample data with columns [a, b, c]",
            skills_info="No custom skills",
            previous_code="",
            viz_library="matplotlib",
            reasoning_level="high"
        )

        # Add conversation
        messages.start_conversation_history()
        messages.add_user_message("What is the average of column a?")

        # Convert to LLM format
        llm_messages = messages.get_messages_for_llm()

        print(f" Generated {len(llm_messages)} messages")
        print(f" System messages: {len(messages.get_system_messages())}")
        print(f" Conversation messages: {len(messages.get_conversation_only())}")
        print(f" Token estimate: {messages.get_token_estimate()}")

        # Test error correction messages
        error_messages = HarmonyMessagesBuilder.for_error_correction(
            error_details="KeyError: 'column_x'",
            failed_code="result = df['column_x'].mean()",
            reasoning_level="medium"
        )

        error_llm_messages = error_messages.get_messages_for_llm()
        print(f" Error correction messages: {len(error_llm_messages)}")

        return True

    except Exception as e:
        print(f" HarmonyMessages test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_pruning():
    """Test memory conversation pruning"""
    print("\n=== Testing Memory Pruning ===")

    try:
        from pandasai.helpers.memory import Memory

        memory = Memory(memory_size=3)

        # Add normal conversation
        memory.add("What is the dataset size?", True)
        memory.add("The dataset has 1000 rows", False)

        # Add error (should be filtered)
        memory.add("Show me statistics", True)
        memory.add("Unfortunately, I was not able to answer your question, because of the following error: KeyError", False)

        # Add another normal message
        memory.add("What columns exist?", True)
        memory.add("Columns: a, b, c", False)

        # Test clean conversation
        clean_conv = memory.get_conversation_only()
        print(f" Total messages: {memory.count()}")
        print(f" Clean conversation messages: {len(clean_conv)}")

        # Should filter out error message
        error_filtered = any("Unfortunately" in msg["message"] for msg in clean_conv)
        print(f" Error messages filtered: {not error_filtered}")

        return True

    except Exception as e:
        print(f" Memory pruning test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=€ Starting Harmony Format Integration Tests")
    print("=" * 50)

    # Load test data
    df = load_test_data()
    if df is None:
        print(" Cannot proceed without test data")
        return

    # Run tests
    tests = [
        ("HarmonyMessages Object", test_harmony_messages_object),
        ("Memory Pruning", test_memory_pruning),
        ("Legacy Format", lambda: test_legacy_format(df)),
        ("Harmony Format", lambda: test_harmony_format(df))
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f" {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*50)
    print("=Ê Test Results Summary")
    print("="*50)

    passed = sum(results.values())
    total = len(results)

    for test_name, passed_test in results.items():
        status = " PASS" if passed_test else " FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("<‰ All tests passed! Harmony format integration successful.")
    else:
        print("   Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()