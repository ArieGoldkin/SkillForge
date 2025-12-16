"""Unit tests for response_helpers module."""

from app.domains.tutor.workflows.nodes.response_helpers import extract_string_content

@pytest.mark.unit


class TestExtractStringContent:
    """Test extract_string_content function."""

    def test_extract_from_object_without_content_attribute(self):
        """Test extraction from object without content attribute (line 24)."""

        # Test with a plain object
        class SimpleObject:
            def __str__(self):
                return "simple object string"

        obj = SimpleObject()
        result = extract_string_content(obj)
        assert result == "simple object string"

        # Test with primitive types
        result = extract_string_content(42)
        assert result == "42"

        result = extract_string_content(3.14)
        assert result == "3.14"

    def test_extract_from_string_content(self):
        """Test extraction when content is already a string."""

        class MockResponse:
            def __init__(self, content: str):
                self.content = content

        response = MockResponse("Hello, world!")
        result = extract_string_content(response)
        assert result == "Hello, world!"

    def test_extract_from_list_with_strings(self):
        """Test extraction from list containing strings (lines 33-37)."""

        class MockResponse:
            def __init__(self, content: list):
                self.content = content

        response = MockResponse(["Hello", " ", "world", "!"])
        result = extract_string_content(response)
        assert result == "Hello world!"

    def test_extract_from_list_with_text_dicts(self):
        """Test extraction from list with dicts containing 'text' key (lines 38-41)."""

        class MockResponse:
            def __init__(self, content: list):
                self.content = content

        response = MockResponse(
            [
                "Start: ",
                {"text": "middle part"},
                " End",
            ]
        )
        result = extract_string_content(response)
        assert result == "Start: middle part End"

    def test_extract_from_list_with_content_dicts(self):
        """Test extraction from list with dicts containing 'content' key (lines 42-43)."""

        class MockResponse:
            def __init__(self, content: list):
                self.content = content

        response = MockResponse(
            [
                "Prefix: ",
                {"content": "main content"},
                " suffix",
            ]
        )
        result = extract_string_content(response)
        assert result == "Prefix: main content suffix"

    def test_extract_from_list_with_other_dicts(self):
        """Test extraction from list with dicts without text/content keys (lines 44-45)."""

        class MockResponse:
            def __init__(self, content: list):
                self.content = content

        response = MockResponse(
            [
                "Item: ",
                {"type": "message", "value": 123},
            ]
        )
        result = extract_string_content(response)
        assert "Item:" in result
        assert "type" in result or "123" in result  # Dict should be stringified

    def test_extract_from_list_mixed_types(self):
        """Test extraction from list with mixed content types (lines 33-46)."""

        class MockResponse:
            def __init__(self, content: list):
                self.content = content

        response = MockResponse(
            [
                "Hello ",
                {"text": "beautiful"},
                " ",
                {"content": "world"},
                " and ",
                {"other": "stuff"},
            ]
        )
        result = extract_string_content(response)
        assert "Hello" in result
        assert "beautiful" in result
        assert "world" in result

    def test_extract_from_dict_with_text_key(self):
        """Test extraction from dict with 'text' key (lines 49-51)."""

        class MockResponse:
            def __init__(self, content: dict):
                self.content = content

        response = MockResponse({"text": "This is the text content"})
        result = extract_string_content(response)
        assert result == "This is the text content"

    def test_extract_from_dict_with_content_key(self):
        """Test extraction from dict with 'content' key (lines 52-53)."""

        class MockResponse:
            def __init__(self, content: dict):
                self.content = content

        response = MockResponse({"content": "This is the content"})
        result = extract_string_content(response)
        assert result == "This is the content"

    def test_extract_from_dict_without_text_or_content(self):
        """Test extraction from dict without text/content keys (line 54)."""

        class MockResponse:
            def __init__(self, content: dict):
                self.content = content

        response = MockResponse({"type": "response", "value": "data"})
        result = extract_string_content(response)
        # Should return string representation of dict
        assert "type" in result or "response" in result

    def test_extract_from_other_types(self):
        """Test extraction from other content types (line 57)."""

        class MockResponse:
            def __init__(self, content):
                self.content = content

        # Test with integer content
        response = MockResponse(42)
        result = extract_string_content(response)
        assert result == "42"

        # Test with None content
        response = MockResponse(None)
        result = extract_string_content(response)
        assert result == "None"

        # Test with custom object
        class CustomContent:
            def __str__(self):
                return "custom content string"

        response = MockResponse(CustomContent())
        result = extract_string_content(response)
        assert result == "custom content string"

    def test_extract_from_empty_list(self):
        """Test extraction from empty list."""

        class MockResponse:
            def __init__(self, content: list):
                self.content = content

        response = MockResponse([])
        result = extract_string_content(response)
        assert result == ""

    def test_extract_from_empty_dict(self):
        """Test extraction from empty dict."""

        class MockResponse:
            def __init__(self, content: dict):
                self.content = content

        response = MockResponse({})
        result = extract_string_content(response)
        assert result == "{}"

    def test_extract_preserves_numeric_text_in_dicts(self):
        """Test that numeric values in dicts are properly converted to strings."""

        class MockResponse:
            def __init__(self, content: dict):
                self.content = content

        response = MockResponse({"text": 123})
        result = extract_string_content(response)
        assert result == "123"

        response = MockResponse({"content": 456.78})
        result = extract_string_content(response)
        assert result == "456.78"
