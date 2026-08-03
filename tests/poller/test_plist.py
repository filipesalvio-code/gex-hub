import plistlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLIST = Path(__file__).parents[2] / "poller" / "com.gexhub.poller.plist"
VENV_PYTHON = "/Users/filipesalvio/gex-hub/.venv/bin/python3"


def test_plist_valid_and_complete():
    d = plistlib.loads(PLIST.read_bytes())
    assert d["Label"] == "com.gexhub.poller"
    assert d["StartInterval"] == 900
    assert d["ProgramArguments"][0] == VENV_PYTHON
    assert "-m" in d["ProgramArguments"] and "poller.poll" in d["ProgramArguments"]
    assert d["WorkingDirectory"].endswith("gex-hub")
    assert "StandardOutPath" in d and "StandardErrorPath" in d
