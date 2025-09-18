# 🎯 Harmony Format Prompts: No Template Rewriting Required

## ❓ **Common Question**
> "Do I need to rewrite all the original prompts for Harmony format? Where do I set the new prompts?"

## ✅ **Simple Answer: No Rewriting Needed!**

The Harmony format implementation is designed to be **minimally disruptive** and **backwards compatible**. You don't need to rewrite any existing templates.

## 🔄 **How Both Formats Work**

### **🏴 Legacy Format (Default - No Changes)**
```python
config = Config()  # use_harmony_format=False (default)
```

**What happens:**
- ✅ Uses existing `.tmpl` files **unchanged**
- ✅ Renders single large prompt as before
- ✅ All current Jinja2 templates work perfectly
- ✅ **Zero modifications required**

**Template files used:**
- `prompts/templates/generate_python_code.tmpl` - **Works as-is**
- `prompts/templates/correct_error_prompt.tmpl` - **Works as-is**
- All other `.tmpl` files - **Work exactly the same**

### **🎵 Harmony Format (Automatic Restructuring)**
```python
config = Config(use_harmony_format=True)
```

**What happens:**
- ✅ **Extracts content** from the same context data
- ✅ **Strategically separates** into focused system messages
- ✅ **No template changes needed**

## 🏗️ **Harmony Format Architecture**

Instead of one large prompt, the system automatically creates:

```
System Message 1: Core Identity
├── "You are an expert Python data analyst..."
├── "Reasoning: high"

System Message 2: Task Context
├── "# AVAILABLE DATAFRAMES:"
├── "dfs[0]: [extracted from context.dfs]"
├── "# AVAILABLE SKILLS:"
├── "[extracted from context.skills_manager]"
├── "# PREVIOUS CODE CONTEXT:"
├── "[extracted from last_code_generated]"

System Message 3: Safety Guards
├── "SECURITY: Never import os, subprocess..."
├── "Reasoning: low"

System Message 4: Output Format
├── "Return executable Python code only..."
├── "Declare 'result' variable as dict..."
├── "For visualizations, use matplotlib..."
├── "Reasoning: low"

User Message: Clean Query
├── "What is the average salary?"  # Just the user's question
```

## 🔧 **Technical Implementation**

### **Content Extraction (Not Template Replacement)**

The `to_harmony_messages()` method **extracts the same information** that templates would render:

```python
def to_harmony_messages(self, context):
    # Extract dataframe info (same as {% for df in context.dfs %})
    dataframes_info = ""
    for i, df in enumerate(context.dfs):
        dataframes_info += f"dfs[{i}]: {df.head_csv}\n"

    # Extract skills info (same as {% if context.skills_manager.has_skills() %})
    skills_info = ""
    if context.skills_manager and context.skills_manager.has_skills():
        skills_info = context.skills_manager.prompt_display()

    # Extract previous code (same as {% if last_code_generated %})
    previous_code = self.props.get("last_code_generated", "")

    # Build strategic system messages
    return HarmonyMessagesBuilder.for_code_generation(
        dataframes_info=dataframes_info,
        skills_info=skills_info,
        previous_code=previous_code,
        # ... other extracted content
    )
```

### **Routing Logic**

The system automatically chooses the format:

```python
def call(self, instruction: BasePrompt, context: PipelineContext = None):
    if context and context.config.use_harmony_format:
        return self._call_harmony_format(instruction, context)  # Strategic messages
    else:
        return self.chat_completion(instruction.to_string(), memory)  # Legacy template
```

## 📊 **Content Comparison**

### **Legacy Format Output**
```
Single Message (User Role):
<dataframe>
dfs[0]:10000x25
Issue Date,Syndicate Desk,Country...
</dataframe>

Update this initial code:
```python
# TODO: import the required dependencies
import pandas as pd
# Write code here
```

### QUERY
What is the average salary?

Variable `dfs: list[pd.DataFrame]` is already declared.
At the end, declare "result" variable as a dictionary...
Generate python code and return full updated code:
```

### **Harmony Format Output**
```
Message 1 (System): You are an expert Python data analyst...
Message 2 (System): # AVAILABLE DATAFRAMES: dfs[0]: 10000x25...
Message 3 (System): SECURITY: Never import os, subprocess...
Message 4 (System): Return executable Python code only...
Message 5 (User): What is the average salary?
```

## 🎯 **Key Benefits**

### **For Developers**
- ✅ **No template rewriting required**
- ✅ **Backwards compatibility maintained**
- ✅ **Existing code works unchanged**
- ✅ **Gradual adoption possible**

### **For LLMs**
- ✅ **Strategic message separation** improves comprehension
- ✅ **Focused system messages** provide clear boundaries
- ✅ **Clean user queries** reduce confusion
- ✅ **Configurable reasoning levels** per message type

## 🚀 **Migration Path**

### **Phase 1: Keep Everything As-Is**
```python
# No changes needed - legacy format continues working
config = Config()  # use_harmony_format=False (default)
```

### **Phase 2: Enable Harmony for gpt-5-nano**
```python
# Automatic restructuring - no template changes
config = Config(use_harmony_format=True)
```

### **Phase 3: Optimize (Optional)**
```python
# Create Harmony-specific templates if desired (completely optional)
# But the automatic extraction works perfectly fine
```

## 🔍 **What You Don't Need to Do**

❌ **Rewrite existing `.tmpl` files**
❌ **Create new template files**
❌ **Modify prompt rendering logic**
❌ **Change existing API calls**
❌ **Update configuration for existing users**

## ✅ **What Happens Automatically**

✅ **Content extraction from existing context**
✅ **Strategic system message generation**
✅ **Format routing based on configuration**
✅ **Backwards compatibility preservation**
✅ **Error isolation and conversation pruning**

## 💡 **Bottom Line**

The Harmony format is an **additive enhancement**, not a replacement. It:

1. **Preserves all existing functionality** (default: legacy format)
2. **Automatically restructures content** when Harmony is enabled
3. **Requires zero template modifications**
4. **Works with the same context data** your templates already use

**You can enable Harmony format immediately without changing a single template file!** 🎉

## 🔗 **Related Files**

- `pandasai/prompts/base.py` - Base class with Harmony support
- `pandasai/prompts/generate_python_code.py` - Example Harmony implementation
- `pandasai/helpers/harmony_messages.py` - Strategic message builder
- `pandasai/schemas/df_config.py` - Configuration options

---

**The key insight: Harmony format extracts and restructures the same content your templates already generate - no rewriting required!**