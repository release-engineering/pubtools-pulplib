from pubtools.pulplib import FakeController


def test_default_content_type_ids():
    """Fake client by default supports various common types."""
    controller = FakeController()
    client = controller.client

    type_ids = client.get_content_type_ids()

    # Type IDs should include this common content types.
    assert "rpm" in type_ids
    assert "erratum" in type_ids
    assert "modulemd" in type_ids

    # Type IDs reported by client should match controller.
    assert sorted(type_ids) == sorted(controller.content_type_ids)


def test_set_content_type_ids():
    """Fake controller can be used to set content type IDs."""
    controller = FakeController()
    client = controller.client

    controller.set_content_type_ids(["a", "b", "c"])

    type_ids = client.get_content_type_ids()
    assert sorted(type_ids) == ["a", "b", "c"]
