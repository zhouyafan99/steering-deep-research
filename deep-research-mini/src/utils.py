import os
from jinja2 import Template

def apply_prompt_template(template_name: str, **kwargs) -> str:
    """
    Load a Jinja2 template from src/prompts/templates/{template_name}.jinja-md
    and render it with the provided kwargs.
    """
    # Construct the absolute path to the template
    # Assuming this file (utils.py) is in src/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "prompts", "templates", f"{template_name}.jinja-md")
    
    # DEBUG
    print(f"[DEBUG] Loading template from: {template_path}")
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
        
        template = Template(template_content)
        return template.render(**kwargs)
    except FileNotFoundError:
        raise FileNotFoundError(f"Template not found at: {template_path}")
    except Exception as e:
        raise Exception(f"Error rendering template {template_name}: {str(e)}")
