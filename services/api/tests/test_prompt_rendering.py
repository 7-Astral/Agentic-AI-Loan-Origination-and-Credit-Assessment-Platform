from agents.prompts.renderer import render_prompt


def test_render_prompt_substitutes_placeholders() -> None:
    template = "You are a loan broker for {{bank_name}}.\nProducts:\n{{products}}"
    rendered = render_prompt(template, {"bank_name": "Demo Mutual Bank", "products": "- Home Loan"})
    assert "Demo Mutual Bank" in rendered
    assert "- Home Loan" in rendered
    assert "{{" not in rendered


def test_render_prompt_leaves_unknown_placeholder_untouched() -> None:
    rendered = render_prompt("Hello {{unknown}}", {})
    assert rendered == "Hello {{unknown}}"
