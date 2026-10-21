"""Tests for the OpenAI-compatible client (FR-003, AC-004, AC-005, AC-007, AC-010)."""

from __future__ import annotations

import io
import json
import logging
import socket
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest
from ai_fakes import FakeTransport, envelope

from ff_tracker.config import DEFAULT_AI_BASE_URL, AISummaryConfig
from ff_tracker.exceptions import (
    AIContractError,
    AIHTTPError,
    AITimeoutError,
    AITransportError,
    AITruncationError,
)
from ff_tracker.services.ai_client import (
    MAX_TOKENS,
    USER_AGENT,
    AIRequest,
    OpenAICompatibleClient,
    _urlopen,
)

API_KEY = "sk-test-SECRET-key"
NARRATIVE = '{"headline": "Beaten again", "leagues": [], "season_note": "Ouch."}'


def _config(
    *,
    api_key: str = API_KEY,
    base_url: str = DEFAULT_AI_BASE_URL,
    model: str = "glm-5.3-flash",
    timeout: int = 120,
) -> AISummaryConfig:
    return AISummaryConfig(
        enabled=True,
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
    )


def _request(user_message: str = '{"week": 6}') -> AIRequest:
    return AIRequest(system_prompt="You are a commissioner.", user_message=user_message)


class TestRequestShape:
    """AC-010: what the provider receives comes from the configuration."""

    def test_url_headers_and_body(self) -> None:
        transport = FakeTransport(envelope(NARRATIVE))
        client = OpenAICompatibleClient(_config(), transport)

        client.complete(_request())

        request, timeout = transport.calls[0]
        assert request.full_url == "https://opencode.ai/inference/openai/v1/chat/completions"
        assert request.get_header("Authorization") == f"Bearer {API_KEY}"
        assert request.get_header("Content-type") == "application/json"
        assert request.get_header("User-agent") == USER_AGENT
        assert USER_AGENT != "Python-urllib"  # the default UA is rejected upstream
        assert timeout == 120

        body = json.loads(request.data.decode("utf-8"))
        assert body["model"] == "glm-5.3-flash"
        assert body["max_tokens"] == MAX_TOKENS == 8000
        assert body["messages"] == [
            {"role": "system", "content": "You are a commissioner."},
            {"role": "user", "content": '{"week": 6}'},
        ]
        assert "response_format" not in body
        assert "stream" not in body

    def test_model_override_is_sent_verbatim(self) -> None:
        transport = FakeTransport(envelope(NARRATIVE))
        OpenAICompatibleClient(_config(model="kimi-k2.6"), transport).complete(_request())
        body = json.loads(transport.calls[0][0].data.decode("utf-8"))
        assert body["model"] == "kimi-k2.6"

    @pytest.mark.parametrize(
        "base_url",
        [DEFAULT_AI_BASE_URL, "https://proxy.example/v1", "https://proxy.example/v1/"],
    )
    def test_base_url_variants_end_at_chat_completions(self, base_url: str) -> None:
        transport = FakeTransport(envelope(NARRATIVE))
        OpenAICompatibleClient(_config(base_url=base_url), transport).complete(_request())
        url = transport.calls[0][0].full_url
        assert url.endswith("/chat/completions")
        assert "//chat" not in url

    def test_scoped_bearer_token_is_the_configured_key(self) -> None:
        transport = FakeTransport(envelope(NARRATIVE))
        OpenAICompatibleClient(_config(api_key="sk-other"), transport).complete(_request())
        assert transport.calls[0][0].get_header("Authorization") == "Bearer sk-other"


class TestResponseHandling:
    """The content is returned; finish_reason gates it."""

    def test_returns_message_content(self) -> None:
        client = OpenAICompatibleClient(_config(), FakeTransport(envelope(NARRATIVE)))
        assert client.complete(_request()) == NARRATIVE

    def test_length_finish_reason_is_truncation_even_with_content(self) -> None:
        transport = FakeTransport(envelope(NARRATIVE, finish_reason="length"))
        client = OpenAICompatibleClient(_config(), transport)
        with pytest.raises(AITruncationError, match="finish_reason=length"):
            client.complete(_request())

    @pytest.mark.parametrize(
        "body",
        [
            b"not json at all",
            b"```json\n{}\n```",
            b'{"choices": []}',
            b'{"choices": [{"message": {}}]}',
            b'{"choices": "nope"}',
            b'{"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]}',
            b'{"choices": [{"message": {"content": "   "}, "finish_reason": "stop"}]}',
            b'{"choices": [{"message": {"content": null}, "finish_reason": "stop"}]}',
            b'{"choices": [{"message": {"content": "x"}, "finish_reason": 7}]}',
        ],
    )
    def test_unexpected_envelope_is_a_contract_failure(self, body: bytes) -> None:
        client = OpenAICompatibleClient(_config(), FakeTransport(body))
        with pytest.raises(AIContractError, match="did not match the summary contract"):
            client.complete(_request())

    @pytest.mark.parametrize("content", [b'""', b"null"])
    def test_length_with_empty_content_is_truncation_not_a_contract_failure(
        self, content: bytes
    ) -> None:
        """A reasoning model can spend the whole budget and return no content."""
        body = (
            b'{"choices": [{"message": {"content": '
            + content
            + b'}, "finish_reason": "length"}]}'
        )
        client = OpenAICompatibleClient(_config(), FakeTransport(body))

        with pytest.raises(AITruncationError, match="finish_reason=length"):
            client.complete(_request())

    def test_usage_is_logged_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        transport = FakeTransport(envelope(NARRATIVE, usage={"prompt_tokens": 12, "completion_tokens": 34}))
        caplog.set_level(logging.DEBUG, logger="ff_tracker.services.ai_client")
        OpenAICompatibleClient(_config(), transport).complete(_request())
        assert "prompt=12 completion=34" in caplog.text


class TestFailureTaxonomy:
    """AC-004/AC-005: every transport failure maps to a reason naming the host."""

    def test_http_error_names_status_model_and_host(self) -> None:
        error = urllib.error.HTTPError(
            "https://opencode.ai/inference/openai/v1/chat/completions",
            410,
            "Gone",
            {},
            io.BytesIO(b"model retired"),
        )
        client = OpenAICompatibleClient(_config(), FakeTransport(error=error))
        with pytest.raises(AIHTTPError) as excinfo:
            client.complete(_request())
        assert excinfo.value.reason == "HTTP 410 (model glm-5.3-flash at opencode.ai)"
        assert "inference" not in excinfo.value.reason

    def test_transport_error(self) -> None:
        error = urllib.error.URLError("connection refused")
        client = OpenAICompatibleClient(_config(), FakeTransport(error=error))
        with pytest.raises(AITransportError, match=r"connection failed \(opencode\.ai\)"):
            client.complete(_request())

    def test_url_error_wrapping_a_timeout(self) -> None:
        error = urllib.error.URLError(socket.timeout("timed out"))
        client = OpenAICompatibleClient(_config(timeout=7), FakeTransport(error=error))
        with pytest.raises(AITimeoutError, match="timed out after 7s"):
            client.complete(_request())

    def test_plain_timeout(self) -> None:
        client = OpenAICompatibleClient(_config(timeout=120), FakeTransport(error=TimeoutError("slow")))
        with pytest.raises(AITimeoutError, match="timed out after 120s"):
            client.complete(_request())

    def test_custom_base_url_host_appears_but_not_its_path(self) -> None:
        error = urllib.error.URLError("nope")
        client = OpenAICompatibleClient(
            _config(base_url="https://proxy.example/secret-path/v1"), FakeTransport(error=error)
        )
        with pytest.raises(AITransportError) as excinfo:
            client.complete(_request())
        assert excinfo.value.reason == "connection failed (proxy.example)"
        assert "secret-path" not in excinfo.value.reason


class TestProductionTransport:
    """The default transport path, which no injected fake exercises."""

    def test_urlopen_wrapper_passes_timeout_and_reads_the_body(self) -> None:
        response = MagicMock()
        response.read.return_value = b'{"ok": true}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=response) as mock_urlopen:
            body = _urlopen(urllib.request.Request("https://opencode.ai/x"), 42)

        assert body == b'{"ok": true}'
        mock_urlopen.assert_called_once()
        assert mock_urlopen.call_args.kwargs["timeout"] == 42
        response.read.assert_called_once()

    def test_client_uses_the_production_transport_by_default(self) -> None:
        response = MagicMock()
        response.read.return_value = envelope(NARRATIVE)
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=response) as mock_urlopen:
            client = OpenAICompatibleClient(_config())
            assert client.complete(_request()) == NARRATIVE

        assert mock_urlopen.call_args.kwargs["timeout"] == 120


class TestLoggingHygiene:
    """AC-006: the key, the request body and the response body never reach a log."""

    MARKER = "MARKER-4f8a2c"

    def _messages(self, caplog: pytest.LogCaptureFixture) -> list[str]:
        return [record.getMessage() for record in caplog.records]

    def _assert_clean(self, caplog: pytest.LogCaptureFixture) -> None:
        joined = "\n".join(self._messages(caplog))
        assert API_KEY not in joined
        assert self.MARKER not in joined
        assert "inference" not in joined  # no path segment of the configured URL
        assert "openai/v1" not in joined

    def test_successful_call_logs_no_body_or_key(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG)
        body = envelope(json.dumps({"headline": self.MARKER}))
        transport = FakeTransport(body)

        OpenAICompatibleClient(_config(), transport).complete(
            _request(user_message=json.dumps({"digest": self.MARKER}))
        )

        assert caplog.records, "the client must log something at DEBUG"
        self._assert_clean(caplog)

    def test_http_error_logs_no_body_or_key(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG)
        error = urllib.error.HTTPError(
            "https://opencode.ai/inference/openai/v1/chat/completions",
            400,
            "Bad Request",
            {},
            io.BytesIO(f"echo: {API_KEY} {self.MARKER}".encode()),
        )
        client = OpenAICompatibleClient(_config(), FakeTransport(error=error))

        with pytest.raises(AIHTTPError):
            client.complete(_request())

        assert caplog.records
        self._assert_clean(caplog)
