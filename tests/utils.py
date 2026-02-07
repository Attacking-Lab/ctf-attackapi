from pathlib import Path
from unittest import IsolatedAsyncioTestCase


class BaseTestCase(IsolatedAsyncioTestCase):
    _res: Path = Path(__file__).parent / "res"
