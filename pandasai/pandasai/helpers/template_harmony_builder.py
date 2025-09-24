"""
Template-based Harmony Messages Builder
Converts hardcoded harmony sections to template-based approach with variable injection
"""
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader

from .harmony_messages import HarmonyMessages


class TemplateHarmonyBuilder:
    """Template-driven builder for HarmonyMessages with scalable variable injection"""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize with template directory"""
        if template_dir is None:
            # Default to harmony_templates directory alongside this file
            current_dir = Path(__file__).parent
            template_dir = current_dir / "harmony_templates"

        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def build_from_config(self, config: Dict[str, Any], variables: Dict[str, Any]) -> HarmonyMessages:
        """
        Build HarmonyMessages from configuration using templates

        Args:
            config: Configuration dict defining sections and their templates
            variables: Variables to inject into templates

        Returns:
            HarmonyMessages object with rendered sections
        """
        reasoning_level = config.get("reasoning_level", "medium")
        messages = HarmonyMessages(reasoning_level)

        # Process each section in order
        for section in config.get("sections", []):
            self._process_section(messages, section, variables)

        return messages

    def _process_section(self, messages: HarmonyMessages, section: Dict[str, Any], variables: Dict[str, Any]) -> None:
        """Process a single section configuration"""
        section_type = section.get("type")
        template_file = section.get("template")
        reasoning_level = section.get("reasoning_level")

        # Skip section if condition is false
        if "condition" in section:
            condition_key = section["condition"]
            if not variables.get(condition_key, False):
                return

        # Special case: conversation_start doesn't need template rendering
        if section_type == "conversation_start":
            messages.start_conversation_history()
            return

        # Render template content for all other section types
        try:
            template = self.env.get_template(template_file)
            content = template.render(**variables)

            # Skip if content is empty after rendering
            if not content.strip():
                return

        except Exception as e:
            raise ValueError(f"Failed to render template {template_file}: {e}")

        # Add to messages based on section type
        if section_type == "core_identity":
            messages.add_core_identity(content, reasoning_level)
        elif section_type == "task_context":
            messages.add_task_context(content, reasoning_level)
        elif section_type == "safety_guard":
            messages.add_safety_guard(content)
        elif section_type == "output_format":
            messages.add_output_format(content)
        elif section_type == "user_message":
            messages.add_user_message(content)
        elif section_type == "assistant_message":
            messages.add_assistant_message(content)
        else:
            raise ValueError(f"Unknown section type: {section_type}")

    def build_for_code_generation(self, **kwargs) -> HarmonyMessages:
        """Build messages for code generation using template configuration"""
        # Default configuration for code generation
        config = {
            "reasoning_level": kwargs.get("reasoning_level", "high"),
            "sections": [
                {
                    "type": "core_identity",
                    "template": "code_generation/core_identity.tmpl",
                    "reasoning_level": kwargs.get("reasoning_level", "high")
                },
                {
                    "type": "task_context",
                    "template": "code_generation/task_context.tmpl",
                    "reasoning_level": kwargs.get("reasoning_level", "high")
                },
                {
                    "type": "task_context",
                    "template": "code_generation/skills_context.tmpl",
                    "condition": "has_skills"
                },
                {
                    "type": "task_context",
                    "template": "code_generation/previous_code_context.tmpl",
                    "condition": "has_previous_code"
                },
                {
                    "type": "task_context",
                    "template": "code_generation/column_context.tmpl",
                    "condition": "has_column_context"
                },
                {
                    "type": "task_context",
                    "template": "code_generation/few_shot_context.tmpl",
                    "condition": "has_few_shot_context"
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

        # Prepare variables for template injection
        variables = {
            "dataframes_info": kwargs.get("dataframes_info", ""),
            "skills_info": kwargs.get("skills_info", ""),
            "previous_code": kwargs.get("previous_code", ""),
            "viz_library": kwargs.get("viz_library", ""),
            "few_shot_context": kwargs.get("few_shot_context", ""),
            "column_context": kwargs.get("column_context", ""),
            "has_skills": bool(kwargs.get("skills_info", "").strip()),
            "has_previous_code": bool(kwargs.get("previous_code", "").strip()),
            "has_viz_library": bool(kwargs.get("viz_library", "").strip()),
            "has_few_shot_context": bool(kwargs.get("few_shot_context", "").strip()),
            "has_column_context": bool(kwargs.get("column_context", "").strip())
        }

        return self.build_from_config(config, variables)

    def build_for_error_correction(self, **kwargs) -> HarmonyMessages:
        """Build messages for error correction using template configuration"""
        config = {
            "reasoning_level": kwargs.get("reasoning_level", "medium"),
            "sections": [
                {
                    "type": "core_identity",
                    "template": "error_correction/core_identity.tmpl",
                    "reasoning_level": kwargs.get("reasoning_level", "medium")
                },
                {
                    "type": "safety_guard",
                    "template": "error_correction/safety_guard.tmpl"
                },
                {
                    "type": "output_format",
                    "template": "error_correction/output_format.tmpl"
                },
                {
                    "type": "conversation_start",
                    "template": ""
                },
                {
                    "type": "user_message",
                    "template": "error_correction/error_message.tmpl"
                }
            ]
        }

        variables = {
            "error_details": kwargs.get("error_details", ""),
            "failed_code": kwargs.get("failed_code", "")
        }

        return self.build_from_config(config, variables)

    def add_custom_section(self, config: Dict[str, Any], section_config: Dict[str, Any]) -> None:
        """Add a custom section to existing configuration"""
        config.setdefault("sections", []).append(section_config)

    def get_available_templates(self) -> Dict[str, list]:
        """Get list of available templates by category"""
        templates = {}

        if self.template_dir.exists():
            for item in self.template_dir.rglob("*.tmpl"):
                category = item.parent.name
                template_name = str(item.relative_to(self.template_dir))
                templates.setdefault(category, []).append(template_name)

        return templates