#!/usr/bin/env python3
"""
Harmony Format Demo - Shows the difference between legacy and Harmony format message structures
"""

import sys
import pandas as pd

# Add the project directory to Python path
sys.path.insert(0, '/Users/josh/Desktop/coding/pandas-ai-2.3.0/pandasai')

def demo_message_structures():
    """Demonstrate the difference between legacy and Harmony message formats"""
    print("🎯 Harmony Format Demo")
    print("=" * 60)

    # Create sample data
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'salary': [50000, 60000, 70000]
    })

    print("📊 Sample Data:")
    print(df)
    print()

    # Demo 1: HarmonyMessages object structure
    print("1️⃣  HarmonyMessages Object Structure")
    print("-" * 40)

    from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder

    # Build Harmony messages for code generation
    harmony_messages = HarmonyMessagesBuilder.for_code_generation(
        dataframes_info="dfs[0]: Employee data with columns ['name', 'age', 'salary']",
        skills_info="No custom skills available",
        previous_code="",
        viz_library="matplotlib",
        reasoning_level="high"
    )

    # Start conversation
    harmony_messages.start_conversation_history()
    harmony_messages.add_user_message("What is the average salary?")

    # Show the message structure
    messages = harmony_messages.get_messages_for_llm()

    print(f"📨 Generated {len(messages)} messages:")
    for i, msg in enumerate(messages):
        print(f"\n  Message {i+1} ({msg['role']}):")
        if msg['role'] == 'system':
            # Show truncated system content
            content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
            print(f"    Content: {content}")
        else:
            print(f"    Content: {msg['content']}")

    print(f"\n📈 Message Statistics:")
    print(f"  • System messages: {len(harmony_messages.get_system_messages())}")
    print(f"  • Conversation messages: {len(harmony_messages.get_conversation_only())}")
    print(f"  • Estimated tokens: {harmony_messages.get_token_estimate()}")

    # Demo 2: Error correction isolation
    print("\n\n2️⃣  Error Correction Isolation")
    print("-" * 40)

    error_messages = HarmonyMessagesBuilder.for_error_correction(
        error_details="KeyError: 'nonexistent_column'",
        failed_code="result = dfs[0]['nonexistent_column'].mean()",
        reasoning_level="medium"
    )

    error_llm_messages = error_messages.get_messages_for_llm()

    print(f"🔧 Error correction uses {len(error_llm_messages)} messages (isolated context):")
    for i, msg in enumerate(error_llm_messages):
        print(f"\n  Message {i+1} ({msg['role']}):")
        content = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
        print(f"    Content: {content}")

    # Demo 3: Memory conversation pruning
    print("\n\n3️⃣  Memory Conversation Pruning")
    print("-" * 40)

    from pandasai.helpers.memory import Memory

    memory = Memory(memory_size=5)

    # Simulate conversation with errors
    conversation_history = [
        ("What columns are available?", True),
        ("The columns are: name, age, salary", False),
        ("Calculate average salary", True),
        ("Unfortunately, I was not able to answer your question, because of the following error: KeyError", False),
        ("Show me the data", True),
        ("Here is the data: [shows data]", False),
        ("What is the maximum age?", True),
        ("The maximum age is 35", False)
    ]

    for msg, is_user in conversation_history:
        memory.add(msg, is_user)

    print(f"📝 Total messages in memory: {memory.count()}")
    print(f"🧹 Clean conversation messages: {len(memory.get_conversation_only())}")

    clean_messages = memory.get_conversation_only()
    print("\n  Clean conversation (errors filtered):")
    for i, msg in enumerate(clean_messages):
        role = "User" if msg["is_user"] else "Assistant"
        print(f"    {i+1}. {role}: {msg['message']}")

    # Demo 4: Configuration comparison
    print("\n\n4️⃣  Configuration Comparison")
    print("-" * 40)

    from pandasai.schemas.df_config import Config

    # Legacy config
    legacy_config = Config(use_harmony_format=False)
    print(f"🏴 Legacy format: use_harmony_format = {legacy_config.use_harmony_format}")

    # Harmony config
    harmony_config = Config(
        use_harmony_format=True,
        harmony_reasoning_levels={
            "code_generation": "high",      # Complex reasoning for code generation
            "error_correction": "medium",   # Moderate reasoning for debugging
            "explanation": "low",           # Simple reasoning for explanations
            "clarification": "low",         # Simple reasoning for questions
            "default": "medium"
        }
    )

    print(f"🎵 Harmony format: use_harmony_format = {harmony_config.use_harmony_format}")
    print(f"🧠 Reasoning levels:")
    for task, level in harmony_config.harmony_reasoning_levels.items():
        print(f"    • {task}: {level}")

    print("\n\n✨ Key Benefits of Harmony Format:")
    print("  🎯 Multiple strategic system messages for clarity")
    print("  🔒 Safety constraints isolated in dedicated system message")
    print("  🧹 Clean conversation history (errors filtered)")
    print("  ⚡ Isolated error correction (no conversation pollution)")
    print("  🧠 Configurable reasoning levels per task type")
    print("  🔄 Full backwards compatibility with legacy format")

    print("\n" + "=" * 60)
    print("🏁 Demo Complete! Harmony format integration successful.")

if __name__ == "__main__":
    demo_message_structures()