from __future__ import annotations

from serve import main as serve_main
from web import main as web_main


def test_web_wrapper_delegates_to_serve():
    assert web_main is serve_main
