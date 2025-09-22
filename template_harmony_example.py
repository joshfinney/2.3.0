#!/usr/bin/env python3
"""
Example demonstrating the new template-based Harmony message generation
Shows how to convert from hardcoded strings to scalable template files
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, '/Users/josh/Desktop/coding/pandas-ai-2.3.0/pandasai')

def test_template_system():
    """Test the template-based harmony system"""
    print("=== Template-Based Harmony Messages Demo ===\n")

    try:
        from pandasai.helpers.template_harmony_builder import TemplateHarmonyBuilder
        from pandasai.helpers.harmony_messages import HarmonyMessagesBuilder

        # Test 1: Direct template builder usage
        print("1. Direct Template Builder Usage:")
        print("-" * 40)

        template_builder = TemplateHarmonyBuilder()

        # Custom configuration example
        custom_config = {
            "reasoning_level": "high",
            "sections": [
                {
                    "type": "core_identity",
                    "template": "code_generation/core_identity.tmpl",
                    "reasoning_level": "high"
                },
                {
                    "type": "task_context",
                    "template": "code_generation/task_context.tmpl"
                },
                {
                    "type": "task_context",
                    "template": "code_generation/skills_context.tmpl",
                    "condition": "has_skills"
                },
                {
                    "type": "safety_guard",
                    "template": "code_generation/safety_guard.tmpl"
                },
                {
                    "type": "output_format",
                    "template": "code_generation/output_format.tmpl"
                }
            ]
        }

        variables = {
            "dataframes_info": "dfs[0]: sales_data.csv with columns: product, quantity, price",
            "skills_info": "statistical_analysis, data_visualization, forecasting",
            "previous_code": "",
            "viz_library": "matplotlib",
            "has_skills": True,
            "has_previous_code": False,
            "has_viz_library": True
        }

        custom_messages = template_builder.build_from_config(custom_config, variables)
        llm_format = custom_messages.get_messages_for_llm()

        print(f"Created {len(llm_format)} messages from templates")
        print(f"System messages: {len(custom_messages.get_system_messages())}")
        print(f"Estimated tokens: {custom_messages.get_token_estimate()}")

        # Show the first few messages
        for i, msg in enumerate(llm_format[:3]):
            print(f"\nMessage {i+1} ({msg['role']}):")
            print(f"  {msg['content'][:100]}...")

        print("\n" + "="*50)

        # Test 2: Integrated builder usage (backward compatible)
        print("\n2. Integrated Builder Usage (Backward Compatible):")
        print("-" * 50)

        # Using new template system through existing interface
        template_messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="dfs[0]: customers.csv with 1000 rows",
            skills_info="data_cleaning, aggregation",
            previous_code="df = dfs[0].dropna()",
            viz_library="plotly",
            reasoning_level="medium",
            use_templates=True  # Use template system
        )

        # Using original hardcoded system
        hardcoded_messages = HarmonyMessagesBuilder.for_code_generation(
            dataframes_info="dfs[0]: customers.csv with 1000 rows",
            skills_info="data_cleaning, aggregation",
            previous_code="df = dfs[0].dropna()",
            viz_library="plotly",
            reasoning_level="medium",
            use_templates=False  # Use original hardcoded approach
        )

        print(f"Template-based messages: {len(template_messages.get_messages_for_llm())}")
        print(f"Hardcoded messages: {len(hardcoded_messages.get_messages_for_llm())}")

        # Compare outputs
        template_llm = template_messages.get_messages_for_llm()
        hardcoded_llm = hardcoded_messages.get_messages_for_llm()

        print(f"\nComparison of first system message:")
        print(f"Template: {template_llm[0]['content'][:80]}...")
        print(f"Hardcoded: {hardcoded_llm[0]['content'][:80]}...")

        print("\n" + "="*50)

        # Test 3: Error correction templates
        print("\n3. Error Correction Templates:")
        print("-" * 35)

        error_messages = template_builder.build_for_error_correction(
            error_details="NameError: name 'pandas' is not defined",
            failed_code="result = pandas.DataFrame({'a': [1, 2, 3]})",
            reasoning_level="medium"
        )

        error_llm = error_messages.get_messages_for_llm()
        print(f"Error correction messages: {len(error_llm)}")

        # Show the user message with error details
        user_msg = [msg for msg in error_llm if msg['role'] == 'user'][0]
        print(f"\nError message content:")
        print(f"  {user_msg['content'][:150]}...")

        print("\n" + "="*50)

        # Test 4: Available templates
        print("\n4. Available Templates:")
        print("-" * 25)

        available = template_builder.get_available_templates()
        for category, templates in available.items():
            print(f"{category}: {', '.join(templates)}")

        return True

    except Exception as e:
        print(f"❌ Template system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demonstrate_extensibility():
    """Show how to extend the template system with new sections"""
    print("\n=== Extensibility Demo: Adding Custom Sections ===\n")

    try:
        from pandasai.helpers.template_harmony_builder import TemplateHarmonyBuilder

        # Create a custom template for data quality checks
        data_quality_template = """# DATA QUALITY REQUIREMENTS:
{% if quality_checks %}
{% for check in quality_checks %}
- {{ check }}
{% endfor %}
{% endif %}"""

        # Save to file (in practice, you'd save this to a .tmpl file)
        template_path = "/Users/josh/Desktop/coding/pandas-ai-2.3.0/pandasai/pandasai/helpers/harmony_templates/code_generation/data_quality.tmpl"

        with open(template_path, 'w') as f:
            f.write(data_quality_template.strip())

        # Custom configuration with the new section
        extended_config = {
            "reasoning_level": "high",
            "sections": [
                {
                    "type": "core_identity",
                    "template": "code_generation/core_identity.tmpl"
                },
                {
                    "type": "task_context",
                    "template": "code_generation/task_context.tmpl"
                },
                {
                    "type": "task_context",  # New custom section
                    "template": "code_generation/data_quality.tmpl",
                    "condition": "has_quality_checks"
                },
                {
                    "type": "safety_guard",
                    "template": "code_generation/safety_guard.tmpl"
                },
                {
                    "type": "output_format",
                    "template": "code_generation/output_format.tmpl"
                }
            ]
        }

        variables = {
            "dataframes_info": "dfs[0]: sensor_data.csv",
            "quality_checks": [
                "Check for null values in critical columns",
                "Validate timestamp ranges",
                "Ensure numeric columns are within expected bounds"
            ],
            "has_quality_checks": True,
            "viz_library": "matplotlib",
            "has_viz_library": True
        }

        builder = TemplateHarmonyBuilder()
        extended_messages = builder.build_from_config(extended_config, variables)

        print(f"Extended configuration created {len(extended_messages.get_messages_for_llm())} messages")

        # Show the custom section
        llm_msgs = extended_messages.get_messages_for_llm()
        for msg in llm_msgs:
            if "DATA QUALITY REQUIREMENTS" in msg['content']:
                print(f"\nCustom Data Quality Section:")
                print(f"  {msg['content']}")
                break

        print("\n✅ Extensibility demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Extensibility demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the complete demo"""
    print("🔧 Template-Based Harmony Messages System")
    print("=" * 60)

    success = test_template_system()
    if success:
        success = demonstrate_extensibility()

    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("=" * 60)

    print("""
✅ Benefits of Template-Based System:

1. SCALABLE: Easy to add new sections via templates
2. MAINTAINABLE: Content separated from logic
3. CONSISTENT: Variable injection ensures uniformity
4. EXTENSIBLE: Custom sections via configuration
5. BACKWARD COMPATIBLE: Existing code continues working
6. TESTABLE: Templates can be tested independently

📁 Template Structure:
harmony_templates/
├── code_generation/
│   ├── core_identity.tmpl
│   ├── task_context.tmpl
│   ├── skills_context.tmpl
│   ├── previous_code_context.tmpl
│   ├── safety_guard.tmpl
│   └── output_format.tmpl
└── error_correction/
    ├── core_identity.tmpl
    ├── safety_guard.tmpl
    ├── output_format.tmpl
    └── error_message.tmpl

🎯 Usage:
- Use HarmonyMessagesBuilder.for_code_generation() as before
- Add use_templates=True/False to control template usage
- Extend with TemplateHarmonyBuilder for custom configurations
""")

    if success:
        print("🎉 All demos completed successfully!")
    else:
        print("⚠️  Some demos encountered issues.")

if __name__ == "__main__":
    main()