from .base import BasePrompt


class GeneratePythonCodePrompt(BasePrompt):
    """Prompt to generate Python code from a dataframe."""

    template_path = "generate_python_code.tmpl"
    
    def __init__(self, tools_prompt: str = None, **kwargs):
        super().__init__(**kwargs)
        self.props["tools_prompt"] = tools_prompt or ""

    def to_json(self):
        context = self.props["context"]
        viz_lib = self.props["viz_lib"]
        output_type = self.props["output_type"]
        tools_prompt = self.props.get("tools_prompt", "")
        memory = context.memory
        conversations = memory.to_json()

        system_prompt = memory.get_system_prompt()

        # prepare datasets
        datasets = [dataset.to_json() for dataset in context.dfs]

        return {
            "datasets": datasets,
            "conversation": conversations,
            "system_prompt": system_prompt,
            "prompt": self.to_string(),
            "tools_prompt": tools_prompt,
            "config": {
                "direct_sql": context.config.direct_sql,
                "viz_lib": viz_lib,
                "output_type": output_type,
            },
        }
