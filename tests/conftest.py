"""Unit tests are not a live cabinet — do not block mutating helpers."""

import os

os.environ.setdefault("TG_ADS_WRITE_GATE", "open")
# Never reach GitHub from tests; update-check tests opt back in with a mocked fetch.
os.environ["TG_ADS_DISABLE_UPDATE_CHECK"] = "1"
