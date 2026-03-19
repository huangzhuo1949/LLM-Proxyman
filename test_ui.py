import json

def test_json():
    # just making sure the python parsing block inside our backend handles custom tools correctly
    from main import LlmInterceptor
    interceptor = LlmInterceptor(None, None)
    
    cases = [
        ({"User-Agent": "OpenAI/v1 PythonBindings/0.27.0"}, ""),
        ({"user-agent": "Codex-VSCode-Extension/1.0.0"}, "codex"),
        ({"User-Agent": "Claude-Code/0.1"}, "claude"),
        ({"X-Client-Id": "OpenCode-Agent"}, "opencode"),
        ({"User-Agent": "Gemini-CLI/1.0"}, "gemini")
    ]
    
    for headers, expected in cases:
        result = interceptor._detect_client_tool(headers)
        assert result == expected, f"Failed on {headers}, got {result} expected {expected}"
    print("User-Agent detection tests passed!")
test_json()
