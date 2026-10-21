"""
OpenAI-compatible Chat Completions client for the AI summary.

One request, one read, no retries and no streaming. Transport failures are
raised as the AI error taxonomy so the summary service can degrade the section
without failing the report.
"""

from __future__ import annotations

import json
import logging
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from importlib.metadata import version
from typing import Protocol

from ..config import AISummaryConfig
from ..exceptions import (
    AIContractError,
    AIHTTPError,
    AITimeoutError,
    AITransportError,
    AITruncationError,
    DataValidationError,
)

logger = logging.getLogger(__name__)

MAX_TOKENS = 8000
CONTRACT_REASON = "response did not match the summary contract"
# Cloudflare in front of the default endpoint rejects the stdlib default
# (``Python-urllib/*``), so the client identifies itself.
USER_AGENT = f"ff-awards/{version('ff-awards')}"


@dataclass(frozen=True)
class AIRequest:
    """The data the summary service sends, and the fake client can record."""

    system_prompt: str
    user_message: str
    max_tokens: int = MAX_TOKENS

    def __post_init__(self) -> None:
        """Validate the request after construction."""
        if not self.system_prompt.strip():
            raise DataValidationError("System prompt cannot be empty")
        if not self.user_message.strip():
            raise DataValidationError("User message cannot be empty")
        if self.max_tokens <= 0:
            raise DataValidationError(f"Max tokens must be positive: {self.max_tokens}")


class AIClient(Protocol):
    """A provider client the summary service can talk to."""

    def complete(self, request: AIRequest) -> str:
        """Return the provider's message content for this request."""
        ...


class HTTPTransport(Protocol):
    """One HTTP POST, returning the response body."""

    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes:
        """Perform the request and read the body."""
        ...


def _urlopen(request: urllib.request.Request, timeout: int) -> bytes:
    """Default transport: one request, one read, no retries."""
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body


class OpenAICompatibleClient:
    """Chat Completions client for any OpenAI-compatible endpoint."""

    def __init__(
        self, config: AISummaryConfig, transport: HTTPTransport | None = None
    ) -> None:
        """
        Initialize the client.

        Args:
            config: Provider settings (base URL, model, key, timeout).
            transport: Override for tests; defaults to ``_urlopen``.
        """
        self._config = config
        self._transport: HTTPTransport = transport or _urlopen

    @property
    def _host(self) -> str:
        """The endpoint host: the only URL fragment allowed in a reason."""
        return urllib.parse.urlsplit(self._config.base_url).hostname or self._config.base_url

    def complete(self, request: AIRequest) -> str:
        """
        Send the request and return the message content.

        Args:
            request: Prompts and token budget.

        Returns:
            The model's message content, still to be parsed as JSON.

        Raises:
            AIHTTPError: Non-2xx status.
            AITransportError: The request never reached the provider.
            AITimeoutError: A socket operation exceeded the timeout.
            AITruncationError: ``finish_reason`` was ``length``.
            AIContractError: The response envelope was not Chat Completions.
        """
        started = time.monotonic()
        http_request = urllib.request.Request(
            self._completions_url(),
            data=self._body(request),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
        )

        raw = self._send(http_request)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        content, finish_reason = self._parse_envelope(raw)
        logger.info(
            "AI summary provider answer: model=%s status=200 latency_ms=%d finish_reason=%s",
            self._config.model,
            elapsed_ms,
            finish_reason,
        )

        # finish_reason is the authority: a reasoning model can burn the whole
        # budget and come back with null or empty content, which is truncation,
        # not a bad shape.
        if finish_reason == "length":
            raise AITruncationError()
        if content is None or not content.strip():
            raise AIContractError(CONTRACT_REASON)
        return content

    def _completions_url(self) -> str:
        """Build the completions URL from the configured root."""
        return f"{self._config.base_url.rstrip('/')}/chat/completions"

    def _body(self, request: AIRequest) -> bytes:
        """Serialise the Chat Completions request body."""
        payload = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "max_tokens": request.max_tokens,
        }
        return json.dumps(payload).encode("utf-8")

    def _send(self, http_request: urllib.request.Request) -> bytes:
        """Perform the request, mapping transport failures onto the taxonomy."""
        try:
            return self._transport(http_request, self._config.timeout)
        except urllib.error.HTTPError as e:
            self._discard(e)
            logger.warning("AI summary provider returned HTTP %s from %s", e.code, self._host)
            raise AIHTTPError(status=e.code, host=self._host, model=self._config.model) from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                logger.warning(
                    "AI summary provider timed out after %ss", self._config.timeout
                )
                raise AITimeoutError(self._config.timeout) from None
            raise AITransportError(self._host) from None
        except (TimeoutError, socket.timeout):
            logger.warning("AI summary provider timed out after %ss", self._config.timeout)
            raise AITimeoutError(self._config.timeout) from None

    @staticmethod
    def _discard(error: urllib.error.HTTPError) -> None:
        """Read and drop the error body: it may echo the request and is never logged."""
        try:
            error.read()
        finally:
            error.close()

    def _parse_envelope(self, raw: bytes) -> tuple[str | None, str]:
        """
        Extract the message content and finish reason from the response.

        Only the two decode failures are caught here; every other rejection is
        an explicit check, so an unanticipated shape crashes rather than
        masquerading as a provider fault.
        """
        try:
            decoded = raw.decode("utf-8")
            payload: object = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise AIContractError(CONTRACT_REASON) from e

        if not isinstance(payload, dict):
            raise AIContractError(CONTRACT_REASON)
        envelope: dict[str, object] = payload

        choices = envelope.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AIContractError(CONTRACT_REASON)
        choice = choices[0]
        if not isinstance(choice, dict):
            raise AIContractError(CONTRACT_REASON)
        first_choice: dict[str, object] = choice

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise AIContractError(CONTRACT_REASON)
        message_dict: dict[str, object] = message

        content = message_dict.get("content")
        if content is not None and not isinstance(content, str):
            raise AIContractError(CONTRACT_REASON)

        finish_reason = first_choice.get("finish_reason")
        if not isinstance(finish_reason, str):
            raise AIContractError(CONTRACT_REASON)

        self._log_usage(envelope)
        return content, finish_reason

    @staticmethod
    def _log_usage(envelope: dict[str, object]) -> None:
        """Log token counts at DEBUG only — never the content or the request."""
        usage = envelope.get("usage")
        if not isinstance(usage, dict):
            return
        usage_dict: dict[str, object] = usage
        prompt_tokens = usage_dict.get("prompt_tokens")
        completion_tokens = usage_dict.get("completion_tokens")
        logger.debug(
            "AI summary tokens: prompt=%s completion=%s", prompt_tokens, completion_tokens
        )
