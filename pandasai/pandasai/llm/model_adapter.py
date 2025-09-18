"""Model Adapter for handling model-specific message formatting and context management.

This module provides abstractions for different model formats while maintaining
compatibility with the pandas-ai architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from ..helpers.memory import Memory


class ModelConfig:
    """Configuration class for model-specific parameters."""
    
    def __init__(self, **kwargs):
        """Initialize model configuration with arbitrary parameters."""
        self.params = kwargs
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration parameter."""
        return self.params.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration parameter."""
        self.params[key] = value


class ModelAdapter(ABC):
    """Abstract base class for model-specific message formatting."""
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """Initialize the adapter with optional configuration."""
        self.config = config or ModelConfig()
    
    @abstractmethod
    def format_messages(self, prompt: str, memory: Optional[Memory] = None) -> List[Dict[str, str]]:
        """
        Format messages according to the model's expected format.
        
        Args:
            prompt (str): The current user prompt
            memory (Optional[Memory]): Conversation history
            
        Returns:
            List[Dict[str, str]]: Formatted messages for the model
        """
        pass
    
    @abstractmethod
    def extract_content(self, response: Any) -> str:
        """
        Extract the relevant content from the model's response.
        
        Args:
            response: Model response object
            
        Returns:
            str: Extracted content
        """
        pass


class OpenAIAdapter(ModelAdapter):
    """Standard OpenAI format adapter."""
    
    def format_messages(self, prompt: str, memory: Optional[Memory] = None) -> List[Dict[str, str]]:
        """Format messages in standard OpenAI format."""
        messages = memory.to_openai_messages() if memory else []
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def extract_content(self, response: Any) -> str:
        """Extract content from OpenAI response."""
        return response.choices[0].message.content


class HarmonyAdapter(ModelAdapter):
    """Harmony Chat Format adapter for gpt-oss family models."""
    
    def format_messages(self, prompt: str, memory: Optional[Memory] = None) -> List[Dict[str, str]]:
        """Format messages using Harmony Chat Format for optimal gpt-oss performance."""
        messages = []
        
        # System message with reasoning level and available tools
        system_content = self._build_system_message()
        messages.append({"role": "system", "content": system_content})
        
        # Developer message for function schemas if needed
        developer_content = self._build_developer_message()
        if developer_content:
            messages.append({"role": "developer", "content": developer_content})
        
        # Add pruned conversation history
        if memory:
            history_messages = self._get_pruned_history(memory)
            messages.extend(history_messages)
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def extract_content(self, response: Any) -> str:
        """Extract final content from Harmony format response."""
        content = response.choices[0].message.content
        
        # Extract only the 'final' channel content for user display
        if "final:" in content.lower():
            lines = content.split('\n')
            final_content = []
            in_final = False
            
            for line in lines:
                if line.lower().strip().startswith('final:'):
                    in_final = True
                    # Add content after "final:" on same line if present
                    after_colon = line.split(':', 1)[1].strip()
                    if after_colon:
                        final_content.append(after_colon)
                elif in_final and (line.lower().strip().startswith(('analysis:', 'commentary:')) or 
                                 line.startswith('##')):
                    # Stop when we hit another channel or section
                    break
                elif in_final:
                    final_content.append(line)
            
            if final_content:
                return '\n'.join(final_content).strip()
        
        return content
    
    def _build_system_message(self) -> str:
        """Build the system message with reasoning level and tool availability."""
        reasoning_level = self.config.get("reasoning_level", "high")
        available_tools = self.config.get("available_tools", [])
        persona = self.config.get("persona", "You are a helpful data analysis assistant.")
        
        system_parts = [persona]
        
        # Add reasoning level
        system_parts.append(f"Reasoning: {reasoning_level}.")
        
        # Add available tools
        if available_tools:
            tools_str = ", ".join(available_tools)
            system_parts.append(f"Tools available: {tools_str}.")
        
        return " ".join(system_parts)
    
    def _build_developer_message(self) -> Optional[str]:
        """Build developer message with function schemas or task-specific context."""
        function_schemas = self.config.get("function_schemas", [])
        task_context = self.config.get("task_context", "")
        
        developer_parts = []
        
        if function_schemas:
            for schema in function_schemas:
                developer_parts.append(f"Function schema for '{schema['name']}': {schema}")
        
        if task_context:
            developer_parts.append(task_context)
        
        return " ".join(developer_parts) if developer_parts else None
    
    def _get_pruned_history(self, memory: Memory) -> List[Dict[str, str]]:
        """
        Get conversation history with analysis and commentary channels pruned.
        
        This implements the context efficiency strategy from the research:
        - Keep user messages
        - Keep only 'final' content from assistant messages
        - Remove 'analysis' (CoT) and 'commentary' (tool use) channels
        """
        messages = []
        
        for msg in memory.all():
            if msg["is_user"]:
                messages.append({"role": "user", "content": msg["message"]})
            else:
                # For assistant messages, extract only the final content
                pruned_content = self._extract_final_content_from_history(msg["message"])
                if pruned_content:
                    messages.append({"role": "assistant", "content": pruned_content})
        
        return messages
    
    def _extract_final_content_from_history(self, content: str) -> str:
        """Extract only final content from previous assistant responses."""
        if "final:" in content.lower():
            lines = content.split('\n')
            final_content = []
            in_final = False
            
            for line in lines:
                if line.lower().strip().startswith('final:'):
                    in_final = True
                    after_colon = line.split(':', 1)[1].strip()
                    if after_colon:
                        final_content.append(after_colon)
                elif in_final and (line.lower().strip().startswith(('analysis:', 'commentary:')) or
                                 line.startswith('##')):
                    break
                elif in_final:
                    final_content.append(line)
            
            return '\n'.join(final_content).strip()
        
        # If no channels detected, return the full content (backwards compatibility)
        return content


class AdapterFactory:
    """Factory for creating appropriate model adapters."""
    
    @staticmethod
    def create_adapter(model_name: str, config: Optional[ModelConfig] = None) -> ModelAdapter:
        """
        Create appropriate adapter based on model name.
        
        Args:
            model_name (str): Name of the model
            config (Optional[ModelConfig]): Model configuration
            
        Returns:
            ModelAdapter: Appropriate adapter for the model
        """
        model_lower = model_name.lower()
        
        if "gpt-oss" in model_lower or "gpt5" in model_lower:
            return HarmonyAdapter(config)
        else:
            return OpenAIAdapter(config)