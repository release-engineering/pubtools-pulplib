import pytest

from pubtools.pulplib import (
    FakeController,
    YumRepository,
    RpmUnit,
    ModulemdUnit,
    Criteria,
)


def test_can_remove_empty():
    """repo.remove() succeeds with empty result if repo has no content."""
    controller = FakeController()
    client = controller.client

    repo = YumRepository(id="repo1")
    controller.insert_repository(repo)

    remove_tasks = client.get_repository("repo1").remove_content()

    assert len(remove_tasks) == 1
    task = remove_tasks[0]

    # It should have completed successfully
    assert task.completed
    assert task.succeeded

    # But should not have removed any units
    assert not task.units


def test_can_remove_content():
    """repo.remove() succeeds and removes expected units inserted via controller."""
    controller = FakeController()
    client = controller.client

    rpm_units = [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
        RpmUnit(name="glibc", version="5.0", release="1", arch="x86_64"),
    ]
    modulemd_units = [
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        ModulemdUnit(
            name="module1", stream="s1", version=1235, context="a1b2", arch="x86_64"
        ),
    ]
    units = rpm_units + modulemd_units

    repo = YumRepository(id="repo1")
    controller.insert_repository(repo)
    controller.insert_units(repo, units)

    remove_rpms = client.get_repository("repo1").remove_content(type_ids=["rpm"])

    assert len(remove_rpms) == 1
    task = remove_rpms[0]

    # It should have completed successfully
    assert task.completed
    assert task.succeeded

    # It should have removed (only) RPM units
    assert sorted(task.units) == sorted(rpm_units)

    # Now if we ask to remove same content again...
    remove_rpms = client.get_repository("repo1").remove_content(type_ids=["rpm"])

    assert len(remove_rpms) == 1
    task = remove_rpms[0]

    # It should have completed successfully, but no RPMs to remove
    assert task.completed
    assert task.succeeded
    assert not task.units

    # It should still be possible to remove other content
    remove_all = client.get_repository("repo1").remove_content()

    assert len(remove_all) == 1
    task = remove_all[0]

    # It should have completed successfully, and removed the modulemds
    assert task.completed
    assert task.succeeded
    assert sorted(task.units) == sorted(modulemd_units)


def test_remove_deleted_repo_fails():
    """repo.remove() fails if repository doesn't exist."""
    controller = FakeController()
    client = controller.client

    repo = YumRepository(id="repo1")
    controller.insert_repository(repo)

    # Get two references to the same repo
    repo_handle1 = client.get_repository("repo1")
    repo_handle2 = client.get_repository("repo1")

    # Use one of them to delete the repo
    repo_handle1.delete().result()

    # Now if I try to use the other one to remove content...
    remove = repo_handle2.remove_content()

    # It should fail
    assert "Repository id=repo1 not found" in str(remove.exception())


def test_remove_filtered_content():
    """repo.remove_content() succeeds and removes expected units inserted via controller."""
    controller = FakeController()
    client = controller.client

    rpm_units = [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
        RpmUnit(name="glibc", version="5.0", release="1", arch="x86_64"),
    ]
    modulemd_units = [
        ModulemdUnit(
            name="module1", stream="s1", version=1234, context="a1b2", arch="x86_64"
        ),
        ModulemdUnit(
            name="module1", stream="s1", version=1235, context="a1b2", arch="x86_64"
        ),
    ]
    units = rpm_units + modulemd_units

    repo = YumRepository(id="repo1")
    controller.insert_repository(repo)
    controller.insert_units(repo, units)

    criteria = Criteria.and_(
        Criteria.with_unit_type(RpmUnit), Criteria.with_field("name", "bash")
    )
    remove_rpms = client.get_repository("repo1").remove_content(criteria=criteria)

    assert len(remove_rpms) == 1
    task = remove_rpms[0]

    # It should have completed successfully
    assert task.completed
    assert task.succeeded

    # It should have removed the specific rpm
    assert len(task.units) == 1
    assert task.units[0] == sorted(rpm_units)[0]

    # Try removing a module with incorrect type_ids
    criteria = Criteria.and_(
        Criteria.with_unit_type(RpmUnit), Criteria.with_field("name", "module1")
    )
    remove_rpms = client.get_repository("repo1").remove_content(criteria=criteria)

    assert len(remove_rpms) == 1
    task = remove_rpms[0]

    # It should have completed successfully
    assert task.completed
    assert task.succeeded

    # Nothing's removed as criteria isn't fulfilled
    assert len(task.units) == 0

    # Removing module with correct type_ids
    criteria = Criteria.and_(
        Criteria.with_unit_type(ModulemdUnit), Criteria.with_field("name", "module1")
    )
    remove_rpms = client.get_repository("repo1").remove_content(criteria=criteria)

    assert len(remove_rpms) == 1
    task = remove_rpms[0]

    # It should have completed successfully
    assert task.completed
    assert task.succeeded

    # It should have removed both the modules as they
    # match the criteria
    assert len(task.units) == 2
    assert sorted(task.units) == sorted(modulemd_units)


def test_remove_fails_without_type_id():
    """repo.remove_content() fails when a criteria is provided without unit type"""
    controller = FakeController()
    client = controller.client

    rpm_units = [
        RpmUnit(name="bash", version="4.0", release="1", arch="x86_64"),
        RpmUnit(name="glibc", version="5.0", release="1", arch="x86_64"),
    ]

    repo = YumRepository(id="repo1")
    controller.insert_repository(repo)
    controller.insert_units(repo, rpm_units)

    criteria = Criteria.and_(Criteria.with_field("name", "bash"))

    with pytest.raises(ValueError):
        client.get_repository("repo1").remove_content(criteria=criteria)
