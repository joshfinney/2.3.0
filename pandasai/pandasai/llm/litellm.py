"""LiteLLM API

This module integrates LiteLLM for model-agnostic LLM API calls with optimal
support for various models including gpt-oss family.

Example:
    Use below example to call LiteLLM with gpt-oss model:

    >>> from pandasai.llm.litellm import LiteLLM
    >>> from pandasai.llm.model_adapter import ModelConfig
    >>> 
    >>> config = ModelConfig(
    ...     reasoning_level="high",
    ...     available_tools=["python"],
    ...     persona="You are an expert data analyst."
    ... )
    >>> llm = LiteLLM(model="gpt-oss-120b", config=config)
"""

import os
from typing import Optional

try:
    import litellm
except ImportError:
    raise ImportError(
        "LiteLLM is required for this functionality. "
        "Please install it with: pip install litellm"
    )

from ..exceptions import APIKeyNotFoundError
from ..helpers import load_dotenv
from ..helpers.memory import Memory
from .base import LLM
from .model_adapter import ModelConfig, AdapterFactory

load_dotenv()


class LiteLLM(LLM):
    """LiteLLM implementation with model adapter support.

    This class provides a model-agnostic interface using LiteLLM while
    maintaining optimal performance for specific models through adapters.
    """

    model: str = "gpt-4o-mini"
    temperature: float = 0
    max_tokens: int = 1000
    top_p: float = 1
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        config: Optional[ModelConfig] = None,
        **kwargs
    ):
        """
        Initialize LiteLLM with model adapter support.

        Args:
            model (str): Model identifier (e.g., "gpt-oss-120b", "gpt-4", etc.)
            api_key (Optional[str]): API key for the model provider
            api_base (Optional[str]): Base URL for API calls
            config (Optional[ModelConfig]): Model-specific configuration
            **kwargs: Additional parameters for LiteLLM
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_base = api_base or os.getenv("OPENAI_API_BASE")
        
        # Set additional parameters
        self.temperature = kwargs.get("temperature", self.temperature)
        self.max_tokens = kwargs.get("max_tokens", self.max_tokens)
        self.top_p = kwargs.get("top_p", self.top_p)
        
        # Store additional LiteLLM parameters
        self.litellm_params = {k: v for k, v in kwargs.items() 
                             if k not in ["temperature", "max_tokens", "top_p"]}
        
        # Initialize model adapter
        self.config = config or ModelConfig()
        self.adapter = AdapterFactory.create_adapter(self.model, self.config)
        
        # Configure LiteLLM if needed
        if self.api_key:
            os.environ["OPENAI_API_KEY"] = self.api_key
        if self.api_base:
            os.environ["OPENAI_API_BASE"] = self.api_base

    @property
    def type(self) -> str:
        """Return the type identifier for this LLM."""
        return "litellm"

    def call(self, instruction, context=None) -> str:
        """
        Execute the LLM with given prompt using model adapter.

        Args:
            instruction: A prompt object with instruction for LLM
            context: PipelineContext with memory and other context

        Returns:
            str: LLM response
        """
        self.last_prompt = instruction.to_string()
        memory = context.memory if context else None
        
        return self._chat_completion(self.last_prompt, memory)

    def _chat_completion(self, prompt: str, memory: Optional[Memory] = None) -> str:
        """
        Execute chat completion using the model adapter.

        Args:
            prompt (str): The user prompt
            memory (Optional[Memory]): Conversation history

        Returns:
            str: Model response
        """
        # Use adapter to format messages appropriately for the model
        messages = self.adapter.format_messages(prompt, memory)
        
        # Prepare LiteLLM parameters
        completion_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            **self.litellm_params
        }
        
        # Call LiteLLM
        try:
            response = litellm.completion(**completion_params)
            
            # Use adapter to extract content appropriately
            return self.adapter.extract_content(response)
            
        except Exception as e:
            # Handle various API errors that might occur
            error_msg = str(e)
            if "api key" in error_msg.lower():
                raise APIKeyNotFoundError(f"API key error: {error_msg}")
            else:
                raise Exception(f"LiteLLM completion failed: {error_msg}")

    def update_config(self, **kwargs):
        """
        Update model configuration dynamically.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            self.config.set(key, value)
        
        # Recreate adapter with updated config
        self.adapter = AdapterFactory.create_adapter(self.model, self.config)


# Helper function for easy gpt-oss setup
def create_gpt_oss_llm(
    model: str = "gpt-oss-120b",
    reasoning_level: str = "high",
    available_tools: list = None,
    persona: str = "You are an expert data analyst specialized in pandas operations.",
    **kwargs
) -> LiteLLM:
    """
    Create a LiteLLM instance optimally configured for gpt-oss models.
    
    Args:
        model (str): GPT-OSS model variant
        reasoning_level (str): Reasoning level (low, medium, high)
        available_tools (list): List of available tools
        persona (str): System persona
        **kwargs: Additional parameters
        
    Returns:
        LiteLLM: Configured LiteLLM instance
    """
    available_tools = available_tools or ["python"]
    
    config = ModelConfig(
        reasoning_level=reasoning_level,
        available_tools=available_tools,
        persona=persona
    )
    
    return LiteLLM(model=model, config=config, **kwargs)