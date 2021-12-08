from pubtools.pulplib import Unit


def test_modulemd_dependencies():
    """
    Modulemd dependecies value comes from expected fields on pulp unit.
    """
    unit = Unit.from_data(
        {
            "_content_type_id": "modulemd",
            "name": "test-modulemd",
            "stream": "1.0",
            "version": 1234,
            "context": "abcd",
            "arch": "x86_64",
            "dependencies": [
                {"platform": ["el8"], "foo-md": ["stream_a", "stream_b"], "bar-md": []}
            ],
        }
    )

    # there should only 3 dependecies
    # foo-md with 2 streams, bar-md with no stream specified
    # platform entry is skipped
    assert len(unit.dependencies) == 3

    sorted_deps = sorted(unit.dependencies, key=lambda x: x.name)

    assert sorted_deps[0].name == "bar-md"
    assert sorted_deps[0].stream is None

    assert sorted_deps[1].name == "foo-md"
    assert sorted_deps[1].stream == "stream_a"

    assert sorted_deps[2].name == "foo-md"
    assert sorted_deps[2].stream == "stream_b"
