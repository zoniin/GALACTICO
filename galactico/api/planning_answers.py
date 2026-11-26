"""Answer sentences and page hand-offs for Squad depth and Signings (2017/18 archive).

Every page opens with one sentence that answers its question. R10 keeps football sentences out
of the browser, so the server composes each one here, from the same numbers the page already
shows, and every sentence passes the copy guard before it leaves (``api.runtime.finalize``).
The endpoints here add to the frozen lab APIs; they never change what those return.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()
