#!/usr/bin/env python3
"""
Example showing how prompts work in Legacy vs Harmony format
"""

import sys
sys.path.insert(0, '/Users/josh/Desktop/coding/pandas-ai-2.3.0/pandasai')

def show_prompt_comparison():
    print("🔍 PROMPT COMPARISON: Legacy vs Harmony Format")
    print("="*60)

    # Create mock context
    from pandasai.pipelines.pipeline_context import PipelineContext
    from pandasai.schemas.df_config import Config
    from pandasai.connectors.pandas import PandasConnector
    from pandasai.helpers.memory import Memory
    import pandas as pd

    # Sample data
    df = pd.DataFrame({
        'name': ['Alice', 'Bob'],
        'salary': [50000, 60000]
    })

    # Create context
    connector = PandasConnector({"original_df": df})
    config = Config()
    memory = Memory(memory_size=5)
    memory.add("What is the average salary?", True)

    context = PipelineContext(
        dfs=[connector],
        config=config,
        memory=memory
    )

    # Create prompt instance
    from pandasai.prompts.generate_python_code import GeneratePythonCodePrompt

    prompt = GeneratePythonCodePrompt(
        context=context,
        last_code_generated="",
        viz_lib="matplotlib",
        output_type=""
    )

    print("📋 LEGACY FORMAT (Current .tmpl files)")
    print("-"*40)
    legacy_prompt = prompt.to_string()
    print(f"Single large prompt: {len(legacy_prompt)} characters")
    print("Content preview:")
    print(legacy_prompt[:300] + "...")

    print("\n🎯 HARMONY FORMAT (Strategic separation)")
    print("-"*40)
    harmony_messages = prompt.to_harmony_messages(context)
    llm_messages = harmony_messages.get_messages_for_llm()

    print(f"Total messages: {len(llm_messages)}")
    for i, msg in enumerate(llm_messages):
        role = msg['role'].upper()
        content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
        print(f"  {i+1}. {role}: {content_preview}")

    print(f"\n📊 COMPARISON:")
    print(f"  Legacy: 1 large message ({len(legacy_prompt)} chars)")
    print(f"  Harmony: {len(llm_messages)} focused messages ({harmony_messages.get_token_estimate()} tokens est.)")
    print(f"  System messages: {len(harmony_messages.get_system_messages())}")
    print(f"  Conversation messages: {len(harmony_messages.get_conversation_only())}")

if __name__ == "__main__":
    show_prompt_comparison()