"""
First-class messages object for Harmony format with strategic multi-system message support.
Provides clean conversation management with deliberate message structuring.
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class MessageRole(Enum):
    """Standard message roles for Harmony format"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class SystemMessageType(Enum):
    """Types of system messages for strategic boundary enforcement"""
    CORE_IDENTITY = "core_identity"        # Base assistant identity and behavior
    TASK_CONTEXT = "task_context"          # Specific task instructions and data context
    SAFETY_GUARD = "safety_guard"          # Security and safety constraints
    OUTPUT_FORMAT = "output_format"        # Response format specifications


@dataclass
class HarmonyMessage:
    """Individual message in Harmony format"""
    role: str
    content: str
    reasoning_level: Optional[str] = None
    message_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for LLM API"""
        msg = {"role": self.role, "content": self.content}
        if self.reasoning_level and self.role == MessageRole.SYSTEM.value:
            msg["content"] += f"\nReasoning: {self.reasoning_level}"
        return msg


class HarmonyMessages:
    """
    First-class messages object for Harmony format conversations.
    Manages multiple system messages strategically for context clarity and risk mitigation.
    """

    def __init__(self, reasoning_level: str = "medium"):
        self._messages: List[HarmonyMessage] = []
        self._default_reasoning = reasoning_level
        self._conversation_start_index = 0  # Track where conversation history starts

    def add_core_identity(self, content: str, reasoning_level: Optional[str] = None) -> None:
        """Add core assistant identity system message"""
        self._messages.append(HarmonyMessage(
            role=MessageRole.SYSTEM.value,
            content=content,
            reasoning_level=reasoning_level or self._default_reasoning,
            message_type=SystemMessageType.CORE_IDENTITY.value
        ))

    def add_task_context(self, content: str, reasoning_level: Optional[str] = None) -> None:
        """Add task-specific context system message"""
        self._messages.append(HarmonyMessage(
            role=MessageRole.SYSTEM.value,
            content=content,
            reasoning_level=reasoning_level or self._default_reasoning,
            message_type=SystemMessageType.TASK_CONTEXT.value
        ))

    def add_safety_guard(self, content: str) -> None:
        """Add safety constraints system message (always low reasoning)"""
        self._messages.append(HarmonyMessage(
            role=MessageRole.SYSTEM.value,
            content=content,
            reasoning_level="low",
            message_type=SystemMessageType.SAFETY_GUARD.value
        ))

    def add_output_format(self, content: str) -> None:
        """Add output format specification system message (always low reasoning)"""
        self._messages.append(HarmonyMessage(
            role=MessageRole.SYSTEM.value,
            content=content,
            reasoning_level="low",
            message_type=SystemMessageType.OUTPUT_FORMAT.value
        ))

    def start_conversation_history(self) -> None:
        """Mark the start of conversation history for clean separation from system messages"""
        self._conversation_start_index = len(self._messages)

    def add_user_message(self, content: str) -> None:
        """Add user message to conversation"""
        self._messages.append(HarmonyMessage(
            role=MessageRole.USER.value,
            content=content
        ))

    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to conversation"""
        # Only add non-error responses to maintain clean conversation flow
        if not self._is_error_response(content):
            self._messages.append(HarmonyMessage(
                role=MessageRole.ASSISTANT.value,
                content=content
            ))

    def get_messages_for_llm(self) -> List[Dict[str, Any]]:
        """Get messages formatted for LLM API call"""
        return [msg.to_dict() for msg in self._messages]

    def get_conversation_only(self) -> List[HarmonyMessage]:
        """Get only conversation messages (user/assistant), excluding system messages"""
        return [msg for msg in self._messages[self._conversation_start_index:]
                if msg.role in [MessageRole.USER.value, MessageRole.ASSISTANT.value]]

    def get_system_messages(self) -> List[HarmonyMessage]:
        """Get only system messages"""
        return [msg for msg in self._messages if msg.role == MessageRole.SYSTEM.value]

    def clear_conversation(self) -> None:
        """Clear conversation history while preserving system messages"""
        system_messages = self.get_system_messages()
        self._messages = system_messages
        self._conversation_start_index = len(self._messages)

    def prune_conversation(self, max_turns: int) -> None:
        """Prune conversation to maintain maximum number of turns while preserving system messages"""
        conversation_msgs = self.get_conversation_only()
        if len(conversation_msgs) > max_turns * 2:  # Each turn = user + assistant
            # Keep system messages + last N turns
            system_messages = self.get_system_messages()
            recent_conversation = conversation_msgs[-(max_turns * 2):]
            self._messages = system_messages + recent_conversation
            self._conversation_start_index = len(system_messages)

    def _is_error_response(self, content: str) -> bool:
        """Check if response is an error message that should not be stored"""
        error_indicators = [
            "Unfortunately, I was not able",
            "because of the following error:",
            "Traceback (most recent call last):",
            "Error occurred"
        ]
        return any(indicator in content for indicator in error_indicators)

    def get_token_estimate(self) -> int:
        """Rough estimate of token usage for monitoring"""
        total_chars = sum(len(msg.content) for msg in self._messages)
        return total_chars // 4  # Rough approximation: 1 token ≈ 4 characters

    def __len__(self) -> int:
        """Return total number of messages"""
        return len(self._messages)

    def __repr__(self) -> str:
        """String representation for debugging"""
        system_count = len(self.get_system_messages())
        conv_count = len(self.get_conversation_only())
        return f"HarmonyMessages(system={system_count}, conversation={conv_count}, tokens≈{self.get_token_estimate()})"


class HarmonyMessagesBuilder:
    """Builder pattern for constructing HarmonyMessages objects for different pipeline stages"""

    @staticmethod
    def for_code_generation(
        dataframes_info: str,
        skills_info: str = "",
        previous_code: str = "",
        viz_library: str = "",
        reasoning_level: str = "high"
    ) -> HarmonyMessages:
        """Build messages for code generation pipeline stage"""
        messages = HarmonyMessages(reasoning_level)

        # Core identity
        messages.add_core_identity(
            "You are an expert Python data analyst. Generate clean, executable code for data analysis tasks.",
            reasoning_level
        )

        # Task context with dataframes and skills
        task_context = f"# AVAILABLE DATAFRAMES:\n{dataframes_info}"
        if skills_info:
            task_context += f"\n\n# AVAILABLE SKILLS:\n{skills_info}"
        if previous_code:
            task_context += f"\n\n# PREVIOUS CODE CONTEXT:\n```python\n{previous_code}\n```"

        messages.add_task_context(task_context, reasoning_level)

        # Safety constraints
        messages.add_safety_guard(
            "SECURITY: Never import os, subprocess, or execute system commands. Only use provided dataframes and approved libraries."
        )

        # Output format
        output_spec = "Return executable Python code only. Declare 'result' variable as dict with 'type' and 'value' keys."
        if viz_library:
            output_spec += f" For visualizations, use {viz_library} and save as PNG."

        messages.add_output_format(output_spec)

        return messages

    @staticmethod
    def for_error_correction(
        error_details: str,
        failed_code: str,
        reasoning_level: str = "medium"
    ) -> HarmonyMessages:
        """Build messages for error correction pipeline stage (isolated context)"""
        messages = HarmonyMessages(reasoning_level)

        # Core identity
        messages.add_core_identity(
            "You are a Python debugging expert. Fix code execution errors efficiently.",
            reasoning_level
        )

        # Safety constraints
        messages.add_safety_guard(
            "SECURITY: Maintain original intent. Never add dangerous imports or system calls."
        )

        # Output format
        messages.add_output_format(
            "Return corrected Python code only. Preserve original logic while fixing the error."
        )

        # No conversation history - isolated debugging context
        messages.start_conversation_history()
        messages.add_user_message(
            f"Fix this code error:\n\n```python\n{failed_code}\n```\n\nError: {error_details}"
        )

        return messages

    @staticmethod
    def for_explanation(reasoning_level: str = "low") -> HarmonyMessages:
        """Build messages for code explanation pipeline stage"""
        messages = HarmonyMessages(reasoning_level)

        # Core identity
        messages.add_core_identity(
            "You are a helpful assistant explaining data analysis code to users.",
            reasoning_level
        )

        # Output format
        messages.add_output_format(
            "Provide clear, step-by-step explanations in plain language. Focus on what the code does and why."
        )

        return messages