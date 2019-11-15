import pytest
from pubtools.pulplib import (
    Repository,
    DetachedException,
    InvalidContentTypeException,
    Criteria,
)


def test_detached():
    """search_content raises if called on a detached repo"""
    with pytest.raises(DetachedException):
        Repository(id="some-repo").search_content(type_id="rpm")


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
                    "filename": "bash-x86_64.srpm",
                    "version": "4.0",
                    "release": "1",
                    "arch": "x86_64",
                },
                {
                    "_content_type_id": "rpm",
                    "name": "bash",
                    "epoch": "0",
                    "filename": "bash-x86_64.rpm",
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
                    "repo_id": "some-repo",
                },
            ],
        )

    @pytest.mark.parametrize(
        "type_id", ["rpm", "srpm", "iso", "modulemd", "modulemd_defaults"]
    )
    def test_search_content(self, type_id):
        """search_content gets all content from the repository"""
        units_f = self.repo.search_content(type_id)
        units = [unit for unit in units_f.result().as_iter()]

        assert len(units) == 1
        assert sorted(units)[0].content_type_id == type_id

    def test_search_content_with_criteria(self):
        """search_content gets only matching content from the repository"""
        crit = Criteria.and_(
            Criteria.with_field("arch", "s390x"), Criteria.with_field("stream", "s1")
        )
        units_f = self.repo.search_content(type_id="modulemd", criteria=crit)
        units = [unit for unit in units_f.result().as_iter()]

        assert len(units) == 1
        assert units[0].name == "m1"

    def test_search_content_with_bad_type_id(self):
        """search_content gets no matching content from the repository"""
        with pytest.raises(InvalidContentTypeException):
            self.repo.search_content(type_id="foo")
