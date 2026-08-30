"""Unit tests are not a live cabinet — do not block mutating helpers."""

import os

os.environ.setdefault("TG_ADS_WRITE_GATE", "open")
