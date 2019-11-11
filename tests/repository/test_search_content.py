import pytest
from pubtools.pulplib import Repository, DetachedException, RpmUnit, ModulemdUnit


def test_detached():
    """search_content raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        Repository(id="some-repo").search_content()


class TestSearchContent(object):
    def __init__(self, requests_mocker, client):
        self.repo = Repository(id="some-repo")
        self.repo.__dict__["_client"] = client

        requests_mocker.post(
            "https://pulp.example.com/pulp/api/v2/repositories/some-repo/search/units/",
            json=[
                {
                    "_content_type_id": "iso",
                    "name": "hello.txt",
                    "size": 23,
                    "checksum": "a" * 64,
                },
                {
                    "_content_type_id": "srpm",
                    "name": "bash",
                    "epoch": "0",
                    "version": "4.0",
                    "release": "1",
                    "arch": "x86_64",
                },
                {
                    "_content_type_id": "rpm",
                    "name": "bash",
                    "epoch": "0",
                    "version": "4.0",
                    "release": "1",
                    "arch": "x86_64",
                },
                {
                    "_content_type_id": "modulemd",
                    "name": "m1",
                    "stream": "s1",
                    "version": 1234,
                    "context": "a1b2c3",
                    "arch": "s390x",
                },
                {
                    "_content_type_id": "modulemd_defaults",
                    "name": "m2",
                    "stream": "s2",
                    "version": 1234,
                    "context": "a1b2c3",
                    "arch": "s390x",
                },
            ]
        )

    def test_search_content(self):
        """search_content gets all rpm and modulemd content from the repository"""
        units_f = self.repo.search_content()
        units = [unit for unit in units_f.result().as_iter()]

        assert len(units) == 4
        assert sorted(units)[0].content_type_id == "modulemd"
        assert sorted(units)[1].content_type_id == "modulemd_defaults"
        assert sorted(units)[2].content_type_id == "rpm"
        assert sorted(units)[3].content_type_id == "srpm"

    def test_search_matched_content(self):
        """search_content gets only matching content from the repository"""
        units_f = self.repo.search_content(arch="s390x", stream="s1")
        units = [unit for unit in units_f.result().as_iter()]

        assert len(units) == 1
        assert units[0].content_type_id == "modulemd"

    def test_search_no_matched_content(self):
        """search_content gets no matching content from the repository"""
        units_f = self.repo.search_content(name="hello.txt")
        units = [unit for unit in units_f.result().as_iter()]

        assert len(units) == 0
