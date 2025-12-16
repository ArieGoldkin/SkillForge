from app.shared.services.mcp.exceptions import (

@pytest.mark.unit
    MCPConfigurationError,
    MCPConnectionError,
    MCPError,
    MCPTimeoutError,
    MCPToolError,
)


class TestMCPError:
    def test_mcp_error_base_class(self):
        assert issubclass(MCPError, Exception)

    def test_mcp_error_with_message(self):
        error = MCPError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.server_name is None
        assert error.details == {}

    def test_mcp_error_with_server_name(self):
        error = MCPError("Test error", server_name="github")
        assert str(error) == "[github] Test error"
        assert error.message == "Test error"
        assert error.server_name == "github"

    def test_mcp_error_with_details(self):
        details = {"attempts": 3, "last_error": "Connection refused"}
        error = MCPError("Test error", server_name="github", details=details)
        assert error.details == details
        assert error.details["attempts"] == 3


class TestMCPConnectionError:
    def test_connection_error_inheritance(self):
        assert issubclass(MCPConnectionError, MCPError)

    def test_connection_error_instantiation(self):
        error = MCPConnectionError("Failed to connect", server_name="github")
        assert str(error) == "[github] Failed to connect"
        assert isinstance(error, MCPError)

    def test_connection_error_with_details(self):
        details = {"attempts": 3, "last_error": "Connection refused"}
        error = MCPConnectionError(
            "Failed to connect",
            server_name="github",
            details=details,
        )
        assert error.details["attempts"] == 3


class TestMCPTimeoutError:
    def test_timeout_error_inheritance(self):
        assert issubclass(MCPTimeoutError, MCPError)

    def test_timeout_error_with_tool_name(self):
        error = MCPTimeoutError(
            "Tool timed out",
            server_name="github",
            tool_name="get_repo",
        )
        assert error.tool_name == "get_repo"
        assert error.server_name == "github"

    def test_timeout_error_with_timeout_seconds(self):
        error = MCPTimeoutError(
            "Tool timed out",
            server_name="github",
            tool_name="get_repo",
            timeout_seconds=30.0,
        )
        assert error.timeout_seconds == 30.0

    def test_timeout_error_optional_attributes(self):
        error = MCPTimeoutError("Timeout occurred")
        assert error.tool_name is None
        assert error.timeout_seconds is None


class TestMCPToolError:
    def test_tool_error_inheritance(self):
        assert issubclass(MCPToolError, MCPError)

    def test_tool_error_with_tool_name(self):
        error = MCPToolError(
            "Tool invocation failed",
            server_name="github",
            tool_name="get_repo",
        )
        assert error.tool_name == "get_repo"

    def test_tool_error_with_error_code(self):
        error = MCPToolError(
            "Invalid arguments",
            server_name="npm",
            tool_name="get_package",
            error_code="INVALID_ARGS",
        )
        assert error.error_code == "INVALID_ARGS"

    def test_tool_error_optional_attributes(self):
        error = MCPToolError("Tool failed")
        assert error.tool_name is None
        assert error.error_code is None


class TestMCPConfigurationError:
    def test_configuration_error_inheritance(self):
        assert issubclass(MCPConfigurationError, MCPError)

    def test_configuration_error_instantiation(self):
        error = MCPConfigurationError(
            "Missing required field",
            server_name="github",
        )
        assert str(error) == "[github] Missing required field"


class TestExceptionHierarchy:
    def test_exception_hierarchy(self):
        assert issubclass(MCPError, Exception)
        assert issubclass(MCPConnectionError, MCPError)
        assert issubclass(MCPTimeoutError, MCPError)
        assert issubclass(MCPToolError, MCPError)
        assert issubclass(MCPConfigurationError, MCPError)

    def test_catching_by_base_class(self):
        exceptions = [
            MCPConnectionError("test"),
            MCPTimeoutError("test"),
            MCPToolError("test"),
            MCPConfigurationError("test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except MCPError as e:
                assert isinstance(e, type(exc))
