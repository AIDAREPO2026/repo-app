"""Workflow: router layer.

HTTP routes only. Each route parses input, calls one service function and renders a response.
"""

from fastapi import APIRouter

router = APIRouter(tags=["workflow"])
