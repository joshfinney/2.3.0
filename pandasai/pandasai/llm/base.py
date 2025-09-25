""" Base class to implement a new LLM

This module is the base class to integrate the various LLMs API. This module also
includes the Base LLM classes for OpenAI and Google PaLM.

Example:

    ```
    from .base import BaseOpenAI

    class CustomLLM(BaseOpenAI):

        Custom Class Starts here!!
    ```
"""

from __future__ import annotations

import ast
import re
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Tuple, Union

from pandasai.helpers.memory import Memory
from pandasai.prompts.generate_system_message import GenerateSystemMessagePrompt

from ..exceptions import (
    APIKeyNotFoundError,
    MethodNotImplementedError,
    NoCodeFoundError,
)
from ..helpers.openai import is_openai_v1
from ..helpers.openai_info import openai_callback_var
from ..prompts.base import BasePrompt

if TYPE_CHECKING:
    from pandasai.pipelines.pipeline_context import PipelineContext


class LLM:
    """Base class to implement a new LLM."""

    last_prompt: Optional[str] = None

    def is_pandasai_llm(self) -> bool:
        """
        Return True if the LLM is from pandasAI.

        Returns:
            bool: True if the LLM is from pandasAI

        """
        return True

    @property
    def type(self) -> str:
        """
        Return type of LLM.

        Raises:
            APIKeyNotFoundError: Type has not been implemented

        Returns:
            str: Type of LLM a string

        """
        raise APIKeyNotFoundError("Type has not been implemented")

    def _polish_code(self, code: str) -> str:
        """
        Polish the code by removing the leading "python" or "py",  \
        removing surrounding '`' characters  and removing trailing spaces and new lines.

        Args:
            code (str): A string of Python code.

        Returns:
            str: Polished code.

        """
        if re.match(r"^(python|py)", code):
            code = re.sub(r"^(python|py)", "", code)
        if re.match(r"^`.*`$", code):
            code = re.sub(r"^`(.*)`$", r"\1", code)
        code = code.strip()
        return code

    def _is_python_code(self, string):
        """
        Return True if it is valid python code.
        Args:
            string (str):

        Returns (bool): True if Python Code otherwise False

        """
        if not string or not string.strip():
            return False

        try:
            ast.parse(string.strip())
            return True
        except SyntaxError:
            # Try with minor fixes for common issues
            try:
                # Remove trailing semicolons that might cause issues
                cleaned = string.strip().rstrip(';')
                ast.parse(cleaned)
                return True
            except SyntaxError:
                return False

    def _extract_code(self, response: str, separator: str = "```") -> str:
        """
        Extract the code from the response using multiple robust strategies.

        Args:
            response (str): Response
            separator (str, optional): Separator. Defaults to "```".

        Raises:
            NoCodeFoundError: No code found in the response

        Returns:
            str: Extracted code from the response

        """
        original_response = response.strip()

        # Validate response quality first
        is_valid, validation_issues = self._validate_response_quality(original_response)
        if not is_valid:
            self._log_extraction_attempt(original_response, None, f"Quality validation failed: {validation_issues}")

        # Try multiple extraction strategies in order of reliability
        strategies = [
            ("separator_based", lambda: self._extract_with_separator(original_response, separator)),
            ("python_block", lambda: self._extract_python_block(original_response)),
            ("keyword_detection", lambda: self._extract_with_keywords(original_response)),
            ("multiline_code", lambda: self._extract_multiline_code(original_response)),
            ("relaxed_extraction", lambda: self._extract_relaxed(original_response))
        ]

        for strategy_name, strategy_func in strategies:
            try:
                extracted_code = strategy_func()
                if extracted_code and self._is_python_code(extracted_code):
                    self._log_extraction_attempt(original_response, extracted_code, f"Success with {strategy_name} strategy")
                    return extracted_code
            except Exception as e:
                self._log_extraction_attempt(original_response, None, f"{strategy_name} failed: {str(e)}")
                continue

        # All strategies failed - provide comprehensive error
        error_context = {
            'response_length': len(original_response),
            'contains_code_markers': separator in original_response,
            'validation_issues': validation_issues if not is_valid else None,
            'strategies_attempted': [name for name, _ in strategies],
            'llm_type': getattr(self, 'type', 'unknown') if hasattr(self, 'type') else 'unknown'
        }

        response_preview = original_response[:200] + "..." if len(original_response) > 200 else original_response

        self._log_extraction_attempt(original_response, None, f"All extraction strategies failed: {error_context}")

        raise NoCodeFoundError(
            f"No valid Python code found in LLM response after trying {len(strategies)} extraction strategies. "
            f"Response length: {len(original_response)} chars.",
            response_preview=response_preview,
            debug_info=error_context
        )

    def prepend_system_prompt(self, prompt: BasePrompt, memory: Memory):
        """
        Append system prompt to the chat prompt, useful when model doesn't have messages for chat history
        Args:
            prompt (BasePrompt): prompt for chat method
            memory (Memory): user conversation history
        """
        return self.get_system_prompt(memory) + prompt if memory else prompt

    def get_system_prompt(self, memory: Memory) -> Any:
        """
        Generate system prompt with agent info and previous conversations
        """
        system_prompt = GenerateSystemMessagePrompt(memory=memory)
        return system_prompt.to_string()

    def get_messages(self, memory: Memory) -> Any:
        """
        Return formatted messages
        Args:
            memory (Memory): Get past Conversation from memory
        """
        return memory.get_previous_conversation()

    def _validate_response_quality(self, response: str) -> tuple[bool, list[str]]:
        """
        Validate response quality before attempting code extraction.

        Args:
            response (str): LLM response to validate

        Returns:
            tuple[bool, list[str]]: (is_valid, list_of_issues)
        """
        issues = []

        # Length checks
        if len(response.strip()) < 5:
            issues.append("Response too short (< 5 characters)")

        # Content analysis
        response_lower = response.lower()

        # Check for refusal patterns
        refusal_patterns = [
            'sorry, i cannot', 'i apologize', 'as an ai', 'i cannot provide',
            'error occurred', 'unable to', 'cannot help', 'not possible'
        ]
        if any(pattern in response_lower for pattern in refusal_patterns):
            issues.append("Response contains refusal/error patterns")

        # Check for code indicators
        code_indicators = [
            'import ', 'from ', 'def ', '=', 'print', 'df', 'pd.', '.plot', '.head',
            '.describe', 'pandas', 'numpy', 'matplotlib'
        ]
        if not any(indicator in response_lower for indicator in code_indicators):
            issues.append("No recognizable code patterns found")

        # Format validation
        if '```' in response and response.count('```') % 2 != 0:
            issues.append("Unbalanced code block markers")

        return len(issues) == 0, issues

    def _extract_with_separator(self, response: str, separator: str) -> str:
        """Extract code using traditional separator method."""
        if separator in response:
            parts = response.split(separator)
            if len(parts) > 1:
                code_part = parts[1]
                return self._polish_code(code_part)
        return self._polish_code(response)

    def _extract_python_block(self, response: str) -> str:
        """Extract code specifically marked as python blocks."""
        import re
        pattern = r'```(?:python|py)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
        if matches:
            return self._polish_code(matches[0])
        return None

    def _extract_with_keywords(self, response: str) -> str:
        """Extract code starting from Python keywords."""
        lines = response.split('\n')
        code_lines = []
        code_started = False

        python_keywords = [
            'import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ', 'try:',
            'except', 'with ', 'pd.', 'df.', 'plt.', 'np.', 'print('
        ]

        for line in lines:
            stripped_line = line.strip()
            if not code_started:
                if any(stripped_line.startswith(kw) for kw in python_keywords) or '=' in stripped_line:
                    code_started = True

            if code_started:
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines)
        return None

    def _extract_multiline_code(self, response: str) -> str:
        """Extract the longest block of consecutive code-like lines."""
        lines = response.split('\n')
        best_block = []
        current_block = []

        for line in lines:
            if self._looks_like_code_line(line):
                current_block.append(line)
            else:
                if len(current_block) > len(best_block):
                    best_block = current_block[:]
                current_block = []

        if len(current_block) > len(best_block):
            best_block = current_block

        return '\n'.join(best_block) if best_block else None

    def _extract_relaxed(self, response: str) -> str:
        """Last resort: try to extract any Python-like content."""
        import re
        cleaned = re.sub(r'^(Sure,?\s*)?[Hh]ere\'?s?\s+(the\s+)?(python\s+)?code\s*:?\s*', '', response, flags=re.MULTILINE | re.IGNORECASE)
        cleaned = re.sub(r'^(Certainly!?\s*)?[Hh]ere\'?s?\s+what\s+you\s+need\s*:?\s*', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        cleaned = re.sub(r'```(?:python|py)?\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
        return self._polish_code(cleaned) if cleaned.strip() else None

    def _looks_like_code_line(self, line: str) -> bool:
        """Determine if a line looks like Python code."""
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return True

        code_indicators = [
            lambda l: '=' in l and not l.startswith('='),
            lambda l: any(l.startswith(kw) for kw in ['import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except']),
            lambda l: l.endswith(':'),
            lambda l: any(func in l for func in ['.plot(', '.head(', '.tail(', '.describe(', 'print(', 'df.', 'pd.']),
            lambda l: l.startswith(('    ', '\t')),
            lambda l: any(op in l for op in ['+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=']),
        ]

        return any(indicator(stripped) for indicator in code_indicators)

    def _log_extraction_attempt(self, original_response: str, extracted_code: str, message: str):
        """Log code extraction attempts for debugging."""
        if hasattr(self, '_logger') and self._logger:
            log_data = {
                'operation': 'code_extraction',
                'success': extracted_code is not None,
                'message': message,
                'response_length': len(original_response),
                'response_preview': original_response[:100] + '...' if len(original_response) > 100 else original_response,
                'extracted_length': len(extracted_code) if extracted_code else 0
            }
            self._logger.log(f"[CODE_EXTRACTION] {log_data}")

    def _extract_tag_text(self, response: str, tag: str) -> str:
        """
        Extracts the text between two tags in the response.

        Args:
            response (str): Response
            tag (str): Tag name

        Returns:
            (str or None): Extracted text from the response
        """

        if match := re.search(
            f"(<{tag}>)(.*)(</{tag}>)",
            response,
            re.DOTALL | re.MULTILINE,
        ):
            return match[2]
        return None

    @abstractmethod
    def call(self, instruction: BasePrompt, context: PipelineContext = None) -> str:
        """
        Execute the LLM with given prompt.

        Args:
            instruction (BasePrompt): A prompt object with instruction for LLM.
            context (PipelineContext, optional): PipelineContext. Defaults to None.

        Raises:
            MethodNotImplementedError: Call method has not been implemented

        """
        raise MethodNotImplementedError("Call method has not been implemented")

    def generate_code(self, instruction: BasePrompt, context: PipelineContext) -> str:
        """
        Generate the code based on the instruction and the given prompt.

        Args:
            instruction (BasePrompt): Prompt with instruction for LLM.
            context (PipelineContext): Pipeline context with configuration and state.

        Returns:
            str: A string of Python code.

        """
        try:
            # Store logger reference for extraction logging
            if hasattr(context, 'logger') and context.logger:
                self._logger = context.logger

            response = self.call(instruction, context)

            # Log the raw response for debugging
            if hasattr(self, '_logger') and self._logger:
                self._logger.log(f"[LLM_RESPONSE] Type: {getattr(self, 'type', 'unknown')}, Length: {len(response)}, Preview: {response[:200]}...")

            return self._extract_code(response)

        except NoCodeFoundError as e:
            # Log the failure with additional context
            if hasattr(self, '_logger') and self._logger:
                debug_summary = e.get_debug_summary() if hasattr(e, 'get_debug_summary') else {'error': str(e)}
                self._logger.log(f"[CODE_GENERATION_FAILED] {debug_summary}")
            raise


class BaseOpenAI(LLM):
    """Base class to implement a new OpenAI LLM.

    LLM base class, this class is extended to be used with OpenAI API.

    """

    api_token: str
    api_base: str = "https://api.openai.com/v1"
    temperature: float = 0
    max_tokens: int = 1000
    top_p: float = 1
    frequency_penalty: float = 0
    presence_penalty: float = 0.6
    best_of: int = 1
    n: int = 1
    stop: Optional[str] = None
    request_timeout: Union[float, Tuple[float, float], Any, None] = None
    max_retries: int = 2
    seed: Optional[int] = None
    # support explicit proxy for OpenAI
    openai_proxy: Optional[str] = None
    default_headers: Union[Mapping[str, str], None] = None
    default_query: Union[Mapping[str, object], None] = None
    # Configure a custom httpx client. See the
    # [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
    http_client: Union[Any, None] = None
    client: Any
    _is_chat_model: bool

    def _set_params(self, **kwargs):
        """
        Set Parameters
        Args:
            **kwargs: ["model", "deployment_name", "temperature","max_tokens",
            "top_p", "frequency_penalty", "presence_penalty", "stop", "seed"]

        Returns:
            None.

        """

        valid_params = [
            "model",
            "deployment_name",
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "seed",
        ]
        for key, value in kwargs.items():
            if key in valid_params:
                setattr(self, key, value)

    @property
    def _default_params(self) -> Dict[str, Any]:
        """Get the default parameters for calling OpenAI API."""
        params: Dict[str, Any] = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "seed": self.seed,
            "stop": self.stop,
            "n": self.n,
        }

        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens

        # Azure gpt-35-turbo doesn't support best_of
        # don't specify best_of if it is 1
        if self.best_of > 1:
            params["best_of"] = self.best_of

        return params

    @property
    def _invocation_params(self) -> Dict[str, Any]:
        """Get the parameters used to invoke the model."""
        openai_creds: Dict[str, Any] = {}
        if not is_openai_v1():
            openai_creds |= {
                "api_key": self.api_token,
                "api_base": self.api_base,
            }

        return {**openai_creds, **self._default_params}

    @property
    def _client_params(self) -> Dict[str, any]:
        return {
            "api_key": self.api_token,
            "base_url": self.api_base,
            "timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "default_headers": self.default_headers,
            "default_query": self.default_query,
            "http_client": self.http_client,
        }

    def completion(self, prompt: str, memory: Memory) -> str:
        """
        Query the completion API

        Args:
            prompt (str): A string representation of the prompt.

        Returns:
            str: LLM response.

        """
        prompt = self.prepend_system_prompt(prompt, memory)

        params = {**self._invocation_params, "prompt": prompt}

        if self.stop is not None:
            params["stop"] = [self.stop]

        response = self.client.create(**params)

        if openai_handler := openai_callback_var.get():
            openai_handler(response)

        self.last_prompt = prompt

        return response.choices[0].text

    def chat_completion(self, value: str, memory: Memory) -> str:
        """
        Query the chat completion API

        Args:
            value (str): Prompt

        Returns:
            str: LLM response.

        """
        messages = memory.to_openai_messages() if memory else []

        # adding current prompt as latest query message
        messages.append(
            {
                "role": "user",
                "content": value,
            },
        )

        params = {
            **self._invocation_params,
            "messages": messages,
        }

        if self.stop is not None:
            params["stop"] = [self.stop]

        response = self.client.create(**params)

        if openai_handler := openai_callback_var.get():
            openai_handler(response)

        return response.choices[0].message.content

    def call(self, instruction: BasePrompt, context: PipelineContext = None):
        """
        Call the OpenAI LLM.

        Args:
            instruction (BasePrompt): A prompt object with instruction for LLM.
            context (PipelineContext): context to pass.

        Raises:
            UnsupportedModelError: Unsupported model

        Returns:
            str: Response
        """
        self.last_prompt = instruction.to_string()

        memory = context.memory if context else None

        return (
            self.chat_completion(self.last_prompt, memory)
            if self._is_chat_model
            else self.completion(self.last_prompt, memory)
        )


class BaseGoogle(LLM):
    """Base class to implement a new Google LLM

    LLM base class is extended to be used with
    """

    temperature: Optional[float] = 0
    top_p: Optional[float] = 0.8
    top_k: Optional[int] = 40
    max_output_tokens: Optional[int] = 1000

    def _valid_params(self):
        return ["temperature", "top_p", "top_k", "max_output_tokens"]

    def _set_params(self, **kwargs):
        """
        Dynamically set Parameters for the object.

        Args:
            **kwargs:
                Possible keyword arguments: "temperature", "top_p", "top_k",
                "max_output_tokens".

        Returns:
            None.

        """

        valid_params = self._valid_params()
        for key, value in kwargs.items():
            if key in valid_params:
                setattr(self, key, value)

    def _validate(self):
        """Validates the parameters for Google"""

        if self.temperature is not None and not 0 <= self.temperature <= 1:
            raise ValueError("temperature must be in the range [0.0, 1.0]")

        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be in the range [0.0, 1.0]")

        if self.top_k is not None and not 0 <= self.top_k <= 100:
            raise ValueError("top_k must be in the range [0.0, 100.0]")

        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero")

    @abstractmethod
    def _generate_text(self, prompt: str, memory: Optional[Memory] = None) -> str:
        """
        Generates text for prompt, specific to implementation.

        Args:
            prompt (str): A string representation of the prompt.

        Returns:
            str: LLM response.

        """
        raise MethodNotImplementedError("method has not been implemented")

    def call(self, instruction: BasePrompt, context: PipelineContext = None) -> str:
        """
        Call the Google LLM.

        Args:
            instruction (BasePrompt): Instruction to pass.
            context (PipelineContext): Pass PipelineContext.

        Returns:
            str: LLM response.

        """
        self.last_prompt = instruction.to_string()
        memory = context.memory if context else None
        return self._generate_text(self.last_prompt, memory)
