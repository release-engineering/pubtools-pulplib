import re

import pytest

from pubtools.pulplib import Matcher


def test_matcher_regex_invalid():
    """Matcher.regex raises if passed value is not a valid regular expression."""

    with pytest.raises(re.error):
        Matcher.regex("foo [bar")
