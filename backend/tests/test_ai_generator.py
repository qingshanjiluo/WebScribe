import pytest
from unittest.mock import Mock, patch
from ai_generator import AIGenerator

def test_ai_generator_init():
    with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test_key'}):
        gen = AIGenerator()
        assert gen.client is not None

@patch('openai.OpenAI')
def test_generate_openapi_spec(mock_openai):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    
    gen = AIGenerator()
    gen.client = mock_client
    
    requests = [
        {"url": "https://api.example.com/data", "method": "GET"},
        {"url": "https://api.example.com/create", "method": "POST", "post_data": {"name": "test"}}
    ]
    
    spec = gen.generate_openapi_spec(requests)
    
    assert "openapi" in spec
    assert spec["openapi"] == "3.0.0"
    assert "paths" in spec
    # 检查路径是否被规范化
    assert "/data" in spec["paths"] or "/{id}" in spec["paths"]

def test_generate_css():
    gen = AIGenerator()
    design_tokens = {
        'colors': {'primary': '#007bff', 'secondary': '#6c757d'},
        'fonts': {'primary': 'Arial, sans-serif'},
        'font_sizes': {'small': 12, 'large': 24},
        'border_radius': {'medium': 8}
    }
    css = gen._generate_css(design_tokens)
    assert ':root' in css
    assert '--color-primary' in css
    assert '--font-primary' in css
    assert 'background-color' in css

def test_generate_fallback_project():
    gen = AIGenerator()
    requests = [{"url": "/api/test", "method": "GET"}]
    design_tokens = {"colors": {"primary": "#007bff"}}
    
    project = gen._generate_fallback_project(requests, design_tokens, "react")
    
    assert "package.json" in project
    assert "src/App.jsx" in project
    assert "src/index.css" in project
    assert "src/api.js" in project
    
    # 检查package.json是有效的JSON
    import json
    package = json.loads(project["package.json"])
    assert package["name"] == "generated-app"