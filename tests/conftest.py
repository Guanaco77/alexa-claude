# -*- coding: utf-8 -*-
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lambda"))

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


@pytest.fixture
def load_event():
    def _load(name):
        with open(os.path.join(FIXTURES, name + ".json"), encoding="utf-8") as f:
            return json.load(f)

    return _load
