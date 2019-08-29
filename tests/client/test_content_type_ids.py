def test_can_get_content_type_ids(client, requests_mocker):
    """get_content_type_ids obtains type info from Pulp API as expected."""
    requests_mocker.get(
        "https://pulp.example.com/pulp/api/v2/plugins/types/",
        json=[{"id": "type2"}, {"id": "type1"}],
    )

    type_ids = client.get_content_type_ids().result()

    # It should have returned the supported type IDs
    assert type_ids == ["type1", "type2"]
