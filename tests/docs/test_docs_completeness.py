import os

import pytest

import pubtools.pulplib


def public_symbols():
    symbols = dir(pubtools.pulplib)
    return [sym for sym in symbols if not sym.startswith("_")]


@pytest.fixture(params=public_symbols())
def any_public_symbol(request):
    return request.param


@pytest.fixture(scope="module")
def all_doc_content():
    """Yields the entirety of sphinx docs in this repo as one big string."""
    docs_path = os.path.join(os.path.dirname(__file__), "../../docs")

    # Sanity check that we're looking in the right place
    assert os.path.exists(os.path.join(docs_path, "index.rst"))

    doc_lines = []
    for dirpath, _, filenames in os.walk(docs_path):
        for filename in filenames:
            if not filename.endswith(".rst"):
                continue
            with open(os.path.join(dirpath, filename), "rt") as f:
                doc_lines.extend(f)
                doc_lines.append("")

    return "\n".join(doc_lines)


def test_doc_references_symbol(any_public_symbol, all_doc_content):
    """Any public symbol in pubtools.pulplib must be mentioned at least once
    within the documentation for this project.
    """
    seeking = "pubtools.pulplib.%s" % any_public_symbol
    assert seeking in all_doc_content, '"%s" is not documented!' % seeking
