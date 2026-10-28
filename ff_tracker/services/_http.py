"""
The one HTTP seam the two AI clients share: one request, one read, no retries.

The provider client and the memory store differ only in the taxonomy they map an
outcome onto, so the transport, the error-body discard and the classification of
every failure live here once. Two copies of this rule is how one copy gets fixed
and the other rots.
"""

from __future__ import annotations

import http.client
import socket
import urllib.error
import urllib.request
from typing import Protocol


class HTTPTransport(Protocol):
    """One HTTP request, returning the response body."""

    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes:
        """Perform the request and read the body."""
        ...


def urlopen(request: urllib.request.Request, timeout: int) -> bytes:
    """Default transport: one request, one read, no retries."""
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body


class HTTPStatusFailure(Exception):
    """The endpoint answered with a non-2xx status."""

    def __init__(self, status: int) -> None:
        self.status = status
        super().__init__(f"HTTP {status}")


class HTTPTimeoutFailure(Exception):
    """A socket read exceeded the timeout."""

    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        super().__init__(f"timed out after {seconds}s")


class HTTPTransportFailure(Exception):
    """The request never reached the endpoint, or the connection died mid-body."""


def send(transport: HTTPTransport, request: urllib.request.Request, timeout: int) -> bytes:
    """
    Perform one request and read its body, classifying every failure.

    ``ValueError`` and ``UnicodeError`` belong beside ``OSError`` because
    ``urlopen`` raises them for reachable inputs: a pasted credential carrying a
    trailing newline is ``Invalid header value``, and a non-ASCII gist id cannot
    be encoded. None of them may reach the caller as a crash.
    """
    try:
        return transport(request, timeout)
    except urllib.error.HTTPError as e:
        _discard(e)
        raise HTTPStatusFailure(e.code) from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            raise HTTPTimeoutFailure(timeout) from None
        raise HTTPTransportFailure() from None
    except (TimeoutError, socket.timeout):
        raise HTTPTimeoutFailure(timeout) from None
    except (OSError, http.client.HTTPException, ValueError, UnicodeError):
        raise HTTPTransportFailure() from None


def _discard(error: urllib.error.HTTPError) -> None:
    """Drain and close an error response without letting its body fail the run."""
    try:
        error.read()
    except (OSError, http.client.HTTPException):
        pass
    finally:
        error.close()
