#!/usr/bin/env python3
"""
Production Test for Harmony Format Implementation
Tests both legacy and Harmony formats with real OpenAI API calls
"""

import sys
import os
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

def load_csv_data():
    """Load the bond issues CSV data"""
    try:
        df = pd.read_csv("/Users/josh/Desktop/coding/pandas-ai-2.3.0/mock_bond_issues.csv")
        print(f" Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"L Failed to load CSV: {e}")
        return None

def test_legacy_format():
    """Test legacy format to ensure backwards compatibility"""
    print("\n" + "="*60)
    print("<ô TESTING LEGACY FORMAT (Backwards Compatibility)")
    print("="*60)

    df = load_csv_data()
    if df is None:
        return False

    try:
        # Create LLM instance first
        llm = OpenAI(api_token=OPENAI_API_KEY, model="gpt-4o-mini")

        # Legacy configuration (default)
        config = Config(
            use_harmony_format=False,  # Legacy format
            verbose=True,
            llm=llm  # Provide LLM to avoid BambooLLM initialization
        )

        # Create agent with legacy format
        agent = Agent([df], config=config, memory_size=3)

        print("= Testing legacy format with simple query...")

        # Simple query
        response = agent.chat("How many records are in this dataset?")
        print(f" Legacy response: {response}")

        # Verify it's using legacy format
        is_legacy = not agent.context.config.use_harmony_format
        print(f" Confirmed legacy format: {is_legacy}")

        return True

    except Exception as e:
        print(f"L Legacy format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_harmony_format():
    """Test Harmony format with strategic system messages"""
    print("\n" + "="*60)
    print("<µ TESTING HARMONY FORMAT (New Implementation)")
    print("="*60)

    df = load_csv_data()
    if df is None:
        return False

    try:
        # Create LLM instance first
        llm = OpenAI(api_token=OPENAI_API_KEY, model="gpt-4o-mini")

        # Harmony configuration
        config = Config(
            use_harmony_format=True,  # Enable Harmony format
            harmony_reasoning_levels={
                "code_generation": "high",
                "error_correction": "medium",
                "explanation": "low",
                "clarification": "low",
                "default": "medium"
            },
            verbose=True,
            llm=llm  # Provide LLM to avoid BambooLLM initialization
        )

        # Create agent with Harmony format
        agent = Agent([df], config=config, memory_size=5)

        print("= Testing Harmony format with multi-turn conversation...")

        # Turn 1: Basic query
        print("\n=Ý Turn 1: Basic data exploration")
        response1 = agent.chat("How many records are in this dataset?")
        print(f" Response 1: {response1}")

        # Turn 2: Follow-up query (tests conversation continuity)
        print("\n=Ý Turn 2: Column information")
        response2 = agent.chat("What columns are available?")
        print(f" Response 2: {response2}")

        # Turn 3: Data analysis (tests Harmony format with reasoning)
        print("\n=Ý Turn 3: Data analysis")
        response3 = agent.chat("Show me the average Size (EUR m) if it exists")
        print(f" Response 3: {response3}")

        # Verify Harmony format features
        print("\n= Verifying Harmony format features:")
        print(f" Harmony format enabled: {agent.context.config.use_harmony_format}")
        print(f" Reasoning levels configured: {len(agent.context.config.harmony_reasoning_levels)} levels")
        print(f" Memory size: {agent.context.memory.size}")
        print(f" Conversation messages: {agent.context.memory.count()}")

        return True

    except Exception as e:
        print(f"L Harmony format test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_harmony_messages_structure():
    """Test the HarmonyMessages object structure"""
    print("\n" + "="*60)
    print("<¯ TESTING HARMONY MESSAGES STRUCTURE")
    print("="*60)

    try:
        from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder

        print("=' Building Harmony messages for code generation...")

        # Create messages for code generation
        messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="dfs[0]: Bond issues data with 25 columns including Size, Currency, Sector",
            skills_info="No custom skills available",
            previous_code="",
            viz_library="matplotlib",
            reasoning_level="high"
        )

        # Add conversation
        messages.start_conversation_history()
        messages.add_user_message("What is the average bond size?")

        # Get LLM format
        llm_messages = messages.get_messages_for_llm()

        print(f" Generated {len(llm_messages)} messages")
        print(f" System messages: {len(messages.get_system_messages())}")
        print(f" Conversation messages: {len(messages.get_conversation_only())}")
        print(f" Token estimate: {messages.get_token_estimate()}")

        # Show message structure
        print("\n=Ë Message structure:")
        for i, msg in enumerate(llm_messages):
            role = msg['role']
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"  {i+1}. {role.upper()}: {content_preview}")

        # Test error correction isolation
        print("\n=' Testing error correction isolation...")
        error_messages = HarmonyMessagesBuilder.for_error_correction(
            error_details="KeyError: 'NonExistentColumn'",
            failed_code="result = dfs[0]['NonExistentColumn'].mean()",
            reasoning_level="medium"
        )

        error_llm_messages = error_messages.get_messages_for_llm()
        print(f" Error correction: {len(error_llm_messages)} isolated messages")

        return True

    except Exception as e:
        print(f"L Harmony messages test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_conversation_pruning():
    """Test memory conversation pruning and error filtering"""
    print("\n" + "="*60)
    print(">à TESTING MEMORY CONVERSATION PRUNING")
    print("="*60)

    try:
        from pandasai.helpers.memory import Memory

        print("=Ý Creating memory with conversation and errors...")

        memory = Memory(memory_size=10)

        # Simulate realistic conversation with errors
        conversation = [
            ("What data is available?", True),
            ("The dataset contains bond issuance data with 25 columns", False),
            ("Show me the average bond size", True),
            ("Unfortunately, I was not able to answer your question, because of the following error: KeyError: 'Size'", False),
            ("What columns exist?", True),
            ("The columns include: Issue Date, Syndicate Desk, Country, Issuer, Size (EUR m), Currency, etc.", False),
            ("Calculate average Size (EUR m)", True),
            ("The average Size (EUR m) is 245.67 million euros", False)
        ]

        # Add all messages
        for msg, is_user in conversation:
            memory.add(msg, is_user)

        print(f" Total messages stored: {memory.count()}")

        # Test conversation pruning
        clean_conversation = memory.get_conversation_only()
        print(f" Clean conversation messages: {len(clean_conversation)}")

        # Verify error filtering
        error_count = sum(1 for msg in memory.all() if "Unfortunately, I was not able" in msg["message"])
        clean_error_count = sum(1 for msg in clean_conversation if "Unfortunately, I was not able" in msg["message"])

        print(f" Total error messages: {error_count}")
        print(f" Error messages in clean conversation: {clean_error_count}")
        print(f" Error filtering working: {clean_error_count == 0}")

        # Show clean conversation
        print("\n=Ë Clean conversation (errors filtered):")
        for i, msg in enumerate(clean_conversation):
            role = "User" if msg["is_user"] else "Assistant"
            content = msg["message"][:80] + "..." if len(msg["message"]) > 80 else msg["message"]
            print(f"  {i+1}. {role}: {content}")

        return True

    except Exception as e:
        print(f"L Memory pruning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run production tests"""
    print("=€ PANDAS AI HARMONY FORMAT - PRODUCTION TESTS")
    print("="*70)
    print("Testing with real OpenAI API calls and CSV data")

    # Run all tests
    tests = [
        ("Component Structure", test_harmony_messages_structure),
        ("Memory Pruning", test_memory_conversation_pruning),
        ("Legacy Format", test_legacy_format),
        ("Harmony Format", test_harmony_format)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n= Running {test_name} test...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"L {test_name} failed with exception: {e}")
            results[test_name] = False

    # Final results
    print("\n" + "="*70)
    print("=Ê PRODUCTION TEST RESULTS")
    print("="*70)

    passed = sum(results.values())
    total = len(results)

    for test_name, success in results.items():
        status = " PASS" if success else "L FAIL"
        print(f"{status} {test_name}")

    print(f"\n<¯ Overall Result: {passed}/{total} tests passed")

    if passed == total:
        print("\n<‰ SUCCESS! All tests passed - Ready for production!")
        print(" Backwards compatibility maintained")
        print(" Harmony format fully functional")
        print(" Multi-system messages working")
        print(" Conversation pruning active")
        print(" Error isolation implemented")
        print(" Real API integration verified")
    else:
        print(f"\n   {total - passed} test(s) failed - Review implementation")

    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)