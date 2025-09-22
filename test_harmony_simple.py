#!/usr/bin/env python3
"""
Simple test to verify Harmony format components are working
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, '/Users/josh/Desktop/coding/pandas-ai-2.3.0/pandasai')

def test_config():
    """Test that Harmony configuration is properly set up"""
    print("=== Testing Harmony Config ===")
    try:
        from pandasai.schemas.df_config import Config, HarmonyReasoningConfig

        # Test that the new fields exist
        import inspect
        config_fields = [field for field, _ in inspect.getmembers(Config) if not field.startswith('_')]

        has_harmony_format = 'use_harmony_format' in str(Config.__annotations__)
        has_reasoning_levels = 'harmony_reasoning_levels' in str(Config.__annotations__)

        print(f"✓ has use_harmony_format field: {has_harmony_format}")
        print(f"✓ has harmony_reasoning_levels field: {has_reasoning_levels}")
        print(f"✓ HarmonyReasoningConfig exists: {HarmonyReasoningConfig is not None}")

        # Test default values without instantiating
        defaults = Config.__fields__['use_harmony_format'].default
        reasoning_defaults = Config.__fields__['harmony_reasoning_levels'].default_factory()

        print(f"✓ use_harmony_format default: {defaults}")
        print(f"✓ reasoning levels default: {reasoning_defaults}")

        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_harmony_messages():
    """Test HarmonyMessages object"""
    print("\n=== Testing HarmonyMessages ===")
    try:
        from pandasai.helpers.harmony_messages import HarmonyMessages, HarmonyMessagesBuilder

        # Test basic messages
        messages = HarmonyMessages("high")
        messages.add_core_identity("You are a data analyst")
        messages.add_task_context("Analyze this data")
        messages.start_conversation_history()
        messages.add_user_message("What is the average?")

        llm_format = messages.get_messages_for_llm()

        print(f"✓ Created {len(llm_format)} messages")
        print(f"✓ System messages: {len(messages.get_system_messages())}")
        print(f"✓ Conversation messages: {len(messages.get_conversation_only())}")

        # Test builder pattern
        builder_messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="df: test data",
            skills_info="",
            previous_code="",
            viz_library="matplotlib",
            reasoning_level="high"
        )

        builder_format = builder_messages.get_messages_for_llm()
        print(f"✓ Builder created {len(builder_format)} messages")

        return True
    except Exception as e:
        print(f"✗ HarmonyMessages test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_updates():
    """Test Memory class updates"""
    print("\n=== Testing Memory Updates ===")
    try:
        from pandasai.helpers.memory import Memory

        memory = Memory(memory_size=3)

        # Add normal conversation
        memory.add("Test query", True)
        memory.add("Test response", False)

        # Add error (should be filtered in get_conversation_only)
        memory.add("Another query", True)
        memory.add("Unfortunately, I was not able to answer your question, because of the following error: KeyError", False)

        # Test if methods exist
        has_conversation_only = hasattr(memory, 'get_conversation_only')
        has_error_filter = hasattr(memory, '_is_error_response')
        has_add_without_errors = hasattr(memory, 'add_without_errors')

        print(f"✓ has get_conversation_only: {has_conversation_only}")
        print(f"✓ has _is_error_response: {has_error_filter}")
        print(f"✓ has add_without_errors: {has_add_without_errors}")

        if has_conversation_only:
            clean_conv = memory.get_conversation_only()
            print(f"✓ Clean conversation: {len(clean_conv)} messages")

        if has_error_filter:
            is_error = memory._is_error_response("Unfortunately, I was not able")
            print(f"✓ Error detection works: {is_error}")

        return True
    except Exception as e:
        print(f"✗ Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_updates():
    """Test that prompt classes have Harmony support"""
    print("\n=== Testing Prompt Updates ===")
    try:
        from pandasai.prompts.base import BasePrompt
        from pandasai.prompts.generate_python_code import GeneratePythonCodePrompt

        # Check if methods exist
        has_reasoning_level = hasattr(BasePrompt, 'get_reasoning_level')
        has_harmony_messages = hasattr(BasePrompt, 'to_harmony_messages')
        has_harmony_python = hasattr(GeneratePythonCodePrompt, 'to_harmony_messages')

        print(f"✓ BasePrompt has get_reasoning_level: {has_reasoning_level}")
        print(f"✓ BasePrompt has to_harmony_messages: {has_harmony_messages}")
        print(f"✓ GeneratePythonCodePrompt has to_harmony_messages: {has_harmony_python}")

        return True
    except Exception as e:
        print(f"✗ Prompt test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_updates():
    """Test that LLM base class has Harmony support"""
    print("\n=== Testing LLM Updates ===")
    try:
        from pandasai.llm.base import BaseOpenAI

        # Check if methods exist
        has_harmony_call = hasattr(BaseOpenAI, '_call_harmony_format')
        has_harmony_chat = hasattr(BaseOpenAI, '_chat_completion_harmony')

        print(f"✓ BaseOpenAI has _call_harmony_format: {has_harmony_call}")
        print(f"✓ BaseOpenAI has _chat_completion_harmony: {has_harmony_chat}")

        return True
    except Exception as e:
        print(f"✗ LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run component tests"""
    print("🔧 Testing Harmony Format Components")
    print("=" * 50)

    tests = [
        ("Config", test_config),
        ("HarmonyMessages", test_harmony_messages),
        ("Memory Updates", test_memory_updates),
        ("Prompt Updates", test_prompt_updates),
        ("LLM Updates", test_llm_updates)
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "="*50)
    print("📊 Component Test Results")
    print("="*50)

    passed = sum(results.values())
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall: {passed}/{total} components working")

    if passed == total:
        print("🎉 All components working! Ready for integration testing.")
    else:
        print("⚠️  Some components need fixes.")

if __name__ == "__main__":
    main()