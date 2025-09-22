# Template-Based Harmony Messages System

## Overview
This system converts your hardcoded Pandas AI Harmony message generation from basic string construction to using `.tmpl` template files with scalable variable injection.

## Key Benefits

✅ **SCALABLE**: Easy to add new sections via templates
✅ **MAINTAINABLE**: Content separated from logic
✅ **CONSISTENT**: Variable injection ensures uniformity
✅ **EXTENSIBLE**: Custom sections via configuration
✅ **BACKWARD COMPATIBLE**: Existing code continues working
✅ **TESTABLE**: Templates can be tested independently

## File Structure

```
pandasai/helpers/
├── harmony_messages.py                    # Original system with integration
├── template_harmony_builder.py           # New template-based builder
└── harmony_templates/
    ├── code_generation/
    │   ├── core_identity.tmpl            # Section 1: Core assistant identity
    │   ├── task_context.tmpl             # Section 2: Dataframes info
    │   ├── skills_context.tmpl           # Section 3: Skills (conditional)
    │   ├── previous_code_context.tmpl    # Section 4: Previous code (conditional)
    │   ├── safety_guard.tmpl             # Section 5: Security constraints
    │   └── output_format.tmpl            # Section 6: Response format
    └── error_correction/
        ├── core_identity.tmpl            # Debugging expert identity
        ├── safety_guard.tmpl             # Error correction security
        ├── output_format.tmpl            # Fix format instructions
        └── error_message.tmpl            # User message with error details
```

## Usage Examples

### 1. Drop-In Replacement (Backward Compatible)

```python
# Your existing code continues to work exactly as before
messages = HarmonyMessagesBuilder.for_code_generation(
    dataframes_info="dfs[0]: sales_data.csv",
    skills_info="data_analysis, visualization",
    previous_code="df = dfs[0].dropna()",
    viz_library="matplotlib",
    reasoning_level="high"
    # use_templates=True is the default
)
```

### 2. Explicit Template Control

```python
# Force template usage
template_messages = HarmonyMessagesBuilder.for_code_generation(
    dataframes_info="dfs[0]: customers.csv",
    skills_info="aggregation",
    use_templates=True  # Use new template system
)

# Force hardcoded fallback
hardcoded_messages = HarmonyMessagesBuilder.for_code_generation(
    dataframes_info="dfs[0]: customers.csv",
    skills_info="aggregation",
    use_templates=False  # Use original hardcoded system
)
```

### 3. Advanced Custom Configuration

```python
from pandasai.helpers.template_harmony_builder import TemplateHarmonyBuilder

builder = TemplateHarmonyBuilder()

# Define custom section sequence
config = {
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
        # Add custom data quality section
        {
            "type": "task_context",
            "template": "code_generation/data_quality.tmpl",
            "condition": "has_quality_checks"  # Only render if this variable is truthy
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
    "quality_checks": ["Check nulls", "Validate ranges"],
    "has_quality_checks": True,
    "viz_library": "plotly",
    "has_viz_library": True
}

messages = builder.build_from_config(config, variables)
```

## Adding New Sections

### Step 1: Create Template File

Create `/pandasai/helpers/harmony_templates/code_generation/my_new_section.tmpl`:

```jinja2
# MY CUSTOM SECTION:
{% if custom_var %}
Custom content: {{ custom_var }}
{% endif %}

{% for item in custom_list %}
- {{ item }}
{% endfor %}
```

### Step 2: Add to Configuration

```python
config = {
    "reasoning_level": "medium",
    "sections": [
        # ... existing sections ...
        {
            "type": "task_context",  # Choose appropriate message type
            "template": "code_generation/my_new_section.tmpl",
            "condition": "has_custom_content"  # Optional condition
        }
    ]
}

variables = {
    # ... existing variables ...
    "custom_var": "My value",
    "custom_list": ["item1", "item2", "item3"],
    "has_custom_content": True
}
```

## Variable Injection System

The template system uses Jinja2 for powerful variable injection:

### Basic Variables
```jinja2
{{ dataframes_info }}     # Simple variable substitution
{{ viz_library }}         # String variables
```

### Conditional Rendering
```jinja2
{% if has_skills %}
# AVAILABLE SKILLS:
{{ skills_info }}
{% endif %}
```

### Loops
```jinja2
{% for check in quality_checks %}
- {{ check }}
{% endfor %}
```

### Built-in Variables
- `dataframes_info`: Information about available dataframes
- `skills_info`: Available skills description
- `previous_code`: Previously generated code
- `viz_library`: Visualization library to use
- `has_skills`: Boolean indicating if skills are available
- `has_previous_code`: Boolean indicating if previous code exists
- `has_viz_library`: Boolean indicating if viz library is specified

## Migration Path

### Phase 1: No Changes Required ✅
- Your existing code continues working
- Template system is automatically used when available
- Fallback to hardcoded approach if templates fail

### Phase 2: Template Customization (Optional)
- Modify existing `.tmpl` files to customize content
- Add new template files for custom sections
- Use `TemplateHarmonyBuilder` directly for advanced configurations

### Phase 3: Advanced Extensions (Future)
- Create domain-specific template sets
- Build template inheritance hierarchies
- Add template validation and testing

## Current Seven Sections Mapped

1. **Core Identity** → `core_identity.tmpl`
   - Assistant behavior and role definition

2. **Context Data Understanding** → `task_context.tmpl`
   - Available dataframes information

3. **Fuzzy Entity Matching** → `skills_context.tmpl`
   - Available skills and capabilities

4. **Data Set Sampling** → `previous_code_context.tmpl`
   - Previous code context for iteration

5. **F-string Data Generation** → `safety_guard.tmpl`
   - Security constraints and limitations

6. **Core Code Implementation** → `output_format.tmpl`
   - Response format specifications

7. **Conversation History** → Managed by `start_conversation_history()` + user/assistant messages

## Testing

Run the example to verify the system:

```bash
python template_harmony_example.py
```

The test demonstrates:
- Template vs hardcoded output comparison
- Error correction workflow
- Custom section addition
- Extensibility patterns

This approach transforms your static string-based harmony generation into a flexible, maintainable template system while preserving full backward compatibility.