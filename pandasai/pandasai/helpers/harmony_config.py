"""
Harmony Format Configuration System
Allows users to customize system message structure and behavior
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ResponseStyle(Enum):
    """Different response styles for market commentary"""
    TECHNICAL = "technical"          # Technical analysis focus
    BUSINESS = "business"           # Business insights focus
    CONVERSATIONAL = "conversational"  # Friendly, conversational tone
    ANALYTICAL = "analytical"       # Deep analytical focus
    EXECUTIVE = "executive"         # Executive summary style


class ReasoningLevel(Enum):
    """Reasoning levels for system messages"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class HarmonyFormatSettings:
    """Configuration settings for Harmony format behavior"""

    # Core behavior settings
    enable_f_string_enforcement: bool = True
    enable_market_commentary: bool = True
    enable_few_shot_prompting: bool = True
    enable_column_context: bool = True
    enable_next_steps_prompt: bool = True

    # Response style configuration
    response_style: ResponseStyle = ResponseStyle.CONVERSATIONAL
    default_reasoning_level: ReasoningLevel = ReasoningLevel.MEDIUM

    # Few-shot prompting settings
    few_shot_max_examples: int = 3
    few_shot_min_similarity: float = 60.0
    few_shot_success_only: bool = True

    # Market commentary settings
    commentary_max_length: int = 500
    commentary_include_technical_details: bool = False
    commentary_include_next_steps: bool = True

    # System message customization
    custom_system_messages: Dict[str, str] = field(default_factory=dict)
    custom_core_identity: Optional[str] = None
    custom_safety_constraints: Optional[str] = None
    custom_output_format: Optional[str] = None

    # Advanced settings
    vector_store_path: Optional[str] = None
    enable_defensive_programming: bool = True
    max_column_samples: int = 5
    statistical_summary_for_numeric: bool = True

    def get_response_style_prompt(self) -> str:
        """Get system message content based on response style"""
        style_prompts = {
            ResponseStyle.TECHNICAL: (
                "Focus on technical accuracy, statistical methods, and data science best practices. "
                "Provide detailed technical explanations with methodology insights."
            ),
            ResponseStyle.BUSINESS: (
                "Translate technical results into business implications. "
                "Focus on actionable insights, KPIs, and business impact."
            ),
            ResponseStyle.CONVERSATIONAL: (
                "Use clear, friendly language that's accessible to non-technical users. "
                "Explain concepts in plain language with practical examples."
            ),
            ResponseStyle.ANALYTICAL: (
                "Provide deep analytical insights with thorough reasoning. "
                "Include statistical significance, confidence intervals, and analytical caveats."
            ),
            ResponseStyle.EXECUTIVE: (
                "Provide concise, high-level summaries suitable for executive decision-making. "
                "Focus on key findings, recommendations, and strategic implications."
            )
        }
        return style_prompts.get(self.response_style, style_prompts[ResponseStyle.CONVERSATIONAL])

    def get_core_identity_message(self) -> str:
        """Get core identity system message"""
        if self.custom_core_identity:
            return self.custom_core_identity

        base_identity = "You are an expert Python data analyst. Generate clean, executable code for data analysis tasks."

        if self.response_style == ResponseStyle.BUSINESS:
            return f"{base_identity} Focus on business insights and actionable recommendations."
        elif self.response_style == ResponseStyle.TECHNICAL:
            return f"{base_identity} Emphasize statistical rigor and technical best practices."
        elif self.response_style == ResponseStyle.EXECUTIVE:
            return f"{base_identity} Provide executive-level insights and strategic recommendations."

        return base_identity

    def get_safety_constraints(self) -> str:
        """Get safety constraints system message"""
        if self.custom_safety_constraints:
            return self.custom_safety_constraints

        base_safety = "SECURITY: Never import os, subprocess, or execute system commands. Only use provided dataframes and approved libraries."

        if self.enable_defensive_programming:
            return f"{base_safety} Always validate column existence, handle missing values, and check data types before operations."

        return base_safety

    def get_output_format_requirements(self) -> str:
        """Get output format requirements"""
        if self.custom_output_format:
            return self.custom_output_format

        base_format = "Return executable Python code only. Declare 'result' variable as dict with 'type' and 'value' keys."

        requirements = []
        if self.enable_f_string_enforcement:
            requirements.append("MANDATORY: use f-strings for ALL string formatting (f\"{variable}\" instead of .format() or %)")

        if requirements:
            return f"{base_format} {' '.join(requirements)}"

        return base_format

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization"""
        return {
            "enable_f_string_enforcement": self.enable_f_string_enforcement,
            "enable_market_commentary": self.enable_market_commentary,
            "enable_few_shot_prompting": self.enable_few_shot_prompting,
            "enable_column_context": self.enable_column_context,
            "enable_next_steps_prompt": self.enable_next_steps_prompt,
            "response_style": self.response_style.value,
            "default_reasoning_level": self.default_reasoning_level.value,
            "few_shot_max_examples": self.few_shot_max_examples,
            "few_shot_min_similarity": self.few_shot_min_similarity,
            "few_shot_success_only": self.few_shot_success_only,
            "commentary_max_length": self.commentary_max_length,
            "commentary_include_technical_details": self.commentary_include_technical_details,
            "commentary_include_next_steps": self.commentary_include_next_steps,
            "custom_system_messages": self.custom_system_messages,
            "custom_core_identity": self.custom_core_identity,
            "custom_safety_constraints": self.custom_safety_constraints,
            "custom_output_format": self.custom_output_format,
            "vector_store_path": self.vector_store_path,
            "enable_defensive_programming": self.enable_defensive_programming,
            "max_column_samples": self.max_column_samples,
            "statistical_summary_for_numeric": self.statistical_summary_for_numeric
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HarmonyFormatSettings':
        """Create settings from dictionary"""
        # Handle enum conversion
        if "response_style" in data:
            data["response_style"] = ResponseStyle(data["response_style"])
        if "default_reasoning_level" in data:
            data["default_reasoning_level"] = ReasoningLevel(data["default_reasoning_level"])

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class HarmonyConfigManager:
    """Manager for Harmony format configuration"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager"""
        self.config_path = config_path
        self._settings: Optional[HarmonyFormatSettings] = None

    def get_settings(self) -> HarmonyFormatSettings:
        """Get current settings, loading from file if needed"""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings

    def update_settings(self, **kwargs) -> None:
        """Update specific settings"""
        current_settings = self.get_settings()

        # Update settings
        for key, value in kwargs.items():
            if hasattr(current_settings, key):
                setattr(current_settings, key, value)

        self._save_settings()

    def reset_to_defaults(self) -> None:
        """Reset to default settings"""
        self._settings = HarmonyFormatSettings()
        self._save_settings()

    def set_response_style(self, style: ResponseStyle) -> None:
        """Set response style"""
        self.update_settings(response_style=style)

    def set_reasoning_level(self, level: ReasoningLevel) -> None:
        """Set default reasoning level"""
        self.update_settings(default_reasoning_level=level)

    def enable_feature(self, feature: str, enabled: bool = True) -> None:
        """Enable or disable a specific feature"""
        feature_map = {
            "f_strings": "enable_f_string_enforcement",
            "market_commentary": "enable_market_commentary",
            "few_shot": "enable_few_shot_prompting",
            "column_context": "enable_column_context",
            "next_steps": "enable_next_steps_prompt",
            "defensive_programming": "enable_defensive_programming"
        }

        if feature in feature_map:
            self.update_settings(**{feature_map[feature]: enabled})
        else:
            raise ValueError(f"Unknown feature: {feature}")

    def set_custom_message(self, message_type: str, content: str) -> None:
        """Set custom system message"""
        if message_type == "core_identity":
            self.update_settings(custom_core_identity=content)
        elif message_type == "safety_constraints":
            self.update_settings(custom_safety_constraints=content)
        elif message_type == "output_format":
            self.update_settings(custom_output_format=content)
        else:
            current_settings = self.get_settings()
            current_settings.custom_system_messages[message_type] = content
            self._save_settings()

    def _load_settings(self) -> HarmonyFormatSettings:
        """Load settings from file"""
        if not self.config_path:
            return HarmonyFormatSettings()

        try:
            import json
            from pathlib import Path

            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                return HarmonyFormatSettings.from_dict(data)
        except Exception:
            # Return defaults if loading fails
            pass

        return HarmonyFormatSettings()

    def _save_settings(self) -> None:
        """Save settings to file"""
        if not self.config_path or not self._settings:
            return

        try:
            import json
            from pathlib import Path

            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(config_file, 'w') as f:
                json.dump(self._settings.to_dict(), f, indent=2)
        except Exception:
            # Silently fail if saving is not possible
            pass