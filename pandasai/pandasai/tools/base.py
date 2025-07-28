"""
Base classes for PandasAI tool calling system.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Represents a parameter for a tool with enhanced prompt engineering support."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    examples: Optional[List[str]] = None  # Example values for better prompting


class ToolDefinition(BaseModel):
    """Represents a tool definition."""
    name: str
    description: str
    parameters: List[ToolParameter]
    output_schema: Optional[Dict[str, Any]] = None
    
    def to_prompt_format(self, include_examples: bool = True, include_output_schema: bool = True) -> str:
        """Convert tool definition to structured prompt format optimized for LLM understanding."""
        # Use compact, structured format for token efficiency
        params_compact = []
        for p in self.parameters:
            req_marker = "!" if p.required else "?"
            default_val = f"={p.default}" if not p.required and p.default is not None else ""
            params_compact.append(f"{p.name}{req_marker}:{p.type}{default_val}")
        
        params_str = ", ".join(params_compact)
        
        # Structured format following modern prompt engineering
        tool_prompt = f"""
<tool name="{self.name}">
<description>{self.description}</description>
<signature>{self.name}({params_str})</signature>"""
        
        # Add parameters with examples if available
        if self.parameters:
            tool_prompt += "\n<params>"
            for p in self.parameters:
                param_line = f"  {p.name}: {p.description}"
                if include_examples and p.examples:
                    param_line += f" (e.g., {', '.join(p.examples[:2])})"
                tool_prompt += f"\n{param_line}"
            tool_prompt += "\n</params>"
        
        # Add output schema information for LLM understanding
        if include_output_schema:
            tool_prompt += "\n<returns>"
            tool_prompt += f"\n  {self._format_output_schema()}"
            tool_prompt += "\n</returns>"
        
        tool_prompt += "\n</tool>"
        
        return tool_prompt
    
    def _format_output_schema(self) -> str:
        """Format output schema for prompt inclusion."""
        if not self.output_schema:
            return "object: Tool execution result"
        
        schema_type = self.output_schema.get("type", "object")
        schema_desc = self.output_schema.get("description", "Tool execution result")
        
        # Format the output schema in a compact, LLM-friendly way
        formatted = f"{schema_type}: {schema_desc}"
        
        # Add key properties if available
        if "properties" in self.output_schema:
            properties = self.output_schema["properties"]
            key_props = []
            for prop, prop_info in list(properties.items())[:3]:  # Show top 3 properties
                prop_type = prop_info.get("type", "any")
                key_props.append(f"{prop}({prop_type})")
            
            if key_props:
                formatted += f" -> {{{', '.join(key_props)}}}"
                if len(properties) > 3:
                    formatted += f" + {len(properties) - 3} more"
        
        return formatted


class Tool(ABC):
    """Base class for all tools with advanced prompt engineering support."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return the tool description."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Return the tool parameters."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        pass
    
    @property
    def use_cases(self) -> List[str]:
        """Return common use cases for this tool (for prompt engineering)."""
        return []
    
    @property
    def output_schema(self) -> Dict[str, Any]:
        """Return the expected output schema for better prompt engineering."""
        return {"type": "object", "description": "Tool output"}
    
    def get_definition(self) -> ToolDefinition:
        """Get the tool definition."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
            output_schema=self.output_schema
        )


class ToolRegistry:
    """Registry for managing tools with advanced prompt engineering capabilities."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._tool_usage_patterns: Dict[str, List[str]] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, Tool]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def get_tools_prompt(self) -> str:
        """Generate optimized tool prompt using modern prompt engineering principles."""
        if not self._tools:
            return ""
        
        # Header with clear intent and structured format
        tools_prompt = """
<tools>
You have access to these specialized functions for enhanced analysis:

"""
        
        # Add each tool in structured format
        for tool in self._tools.values():
            tools_prompt += tool.get_definition().to_prompt_format()
        
        # Concise, actionable usage instructions
        tools_prompt += """
</tools>

TOOL USAGE RULES:
1. Call tools directly: `result = tool_name(param=value)`
2. Tools return structured data - use results in your analysis
3. Use tools when they enhance accuracy or provide specialized functionality
4. Tool calls are deterministic and cached for consistency

"""
        
        return tools_prompt
    
    def get_contextual_tools_prompt(self, query: str = None, context: str = None) -> str:
        """Generate context-aware tool prompting using modern prompt engineering."""
        if not self._tools:
            return ""
        
        # Analyze query for tool relevance (simple keyword matching for now)
        relevant_tools = self._get_relevant_tools(query) if query else list(self._tools.values())
        
        if not relevant_tools:
            return ""
        
        # Modern structured prompt with few-shot examples
        prompt = f"""
<tools>
Available specialized functions ({len(relevant_tools)} tools):
"""
        
        # Add tools in priority order
        for tool in relevant_tools:
            prompt += tool.get_definition().to_prompt_format()
        
        # Add usage examples and patterns
        prompt += """
</tools>

<tool_integration_patterns>
# Pattern 1: Tool output validation and conditional analysis
validation_result = validate_bond_data(df=dfs[0])
if validation_result['is_valid']:
    # Use the validated data for analysis
    clean_data = dfs[0]
    avg_spread = clean_data['Spread at Launch (bps)'].mean()
    result = {"type": "number", "value": avg_spread}
else:
    # Report data quality issues with specific recommendations
    issues = validation_result['recommendations'][:2]  # Top 2 issues
    result = {"type": "string", "value": f"Data quality issues: {'; '.join(issues)}"}

# Pattern 2: Using tool output metadata for enhanced analysis
validation_result = validate_bond_data(df=dfs[0])
total_rows = validation_result['total_rows']
missing_columns = validation_result['missing_columns']

if len(missing_columns) > 0:
    result = {"type": "string", "value": f"Cannot proceed: Missing columns {missing_columns}"}
else:
    # Enhanced analysis with data quality context
    null_percentages = validation_result['null_percentages']
    high_null_cols = [col for col, pct in null_percentages.items() if pct > 10]
    
    if high_null_cols:
        result = {"type": "string", "value": f"Analysis completed on {total_rows} rows. Note: {', '.join(high_null_cols)} have >10% missing data"}
    else:
        result = {"type": "string", "value": f"Analysis completed on {total_rows} high-quality rows"}
</tool_integration_patterns>

TOOL OUTPUT USAGE PRINCIPLES:
1. Always check tool output structure before accessing properties
2. Use tool metadata (like row counts, quality scores) to enhance analysis context
3. Implement conditional logic based on tool success/failure indicators
4. Extract specific values from tool outputs for calculations
5. Combine tool insights with pandas operations for comprehensive analysis

"""
        return prompt
    
    def _get_relevant_tools(self, query: str) -> List[Tool]:
        """Get tools relevant to the query using simple keyword matching."""
        if not query:
            return list(self._tools.values())
        
        query_lower = query.lower()
        relevant_tools = []
        
        # Score tools based on keyword relevance
        for tool in self._tools.values():
            score = 0
            
            # Check description for relevance
            if any(keyword in tool.description.lower() for keyword in 
                   ['validate', 'check', 'quality', 'data']):
                if any(keyword in query_lower for keyword in 
                       ['validate', 'check', 'quality', 'data', 'structure']):
                    score += 2
            
            # Check tool name relevance
            if any(word in tool.name.lower() for word in query_lower.split()):
                score += 1
            
            if score > 0:
                relevant_tools.append(tool)
        
        # Return all tools if none specifically relevant, or top relevant ones
        return relevant_tools if relevant_tools else list(self._tools.values())
    
    def get_tool_functions(self) -> Dict[str, Any]:
        """Get tool functions for code execution environment."""
        return {
            tool.name: tool.execute
            for tool in self._tools.values()
        }