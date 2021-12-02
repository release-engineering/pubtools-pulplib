from pubtools.pulplib import Criteria, Matcher, FileUnit


def test_stringify_complex_criteria():
    crit = Criteria.and_(
        Criteria.with_field("must-exist", Matcher.exists()),
        Criteria.with_field("foo", Matcher.equals("bar")),
        Criteria.true(),
        Criteria.or_(
            Criteria.with_field("foo", Matcher.regex("quux")),
            Criteria.with_field("other", Matcher.in_(["x", "y", "z"])),
            Criteria.with_field("num", Matcher.less_than(9000)),
        ),
        Criteria.with_unit_type(FileUnit),
    )

    assert (
        str(crit) == "((must-exist EXISTS) AND foo=='bar' AND TRUE "
        "AND (foo=~/quux/ OR (other IN ['x', 'y', 'z']) OR num<9000) "
        "AND (content_type_id IN ['iso']))"
    )


def test_stringify_noop_and():
    assert str(Criteria.and_()) == "<empty AND>"


def test_stringify_noop_or():
    assert str(Criteria.or_()) == "<empty OR>"


def test_stringify_simplify_and():
    assert str(Criteria.and_(Criteria.with_field("x", 123))) == "x==123"


def test_stringify_simplify_or():
    assert str(Criteria.or_(Criteria.with_field("x", 123))) == "x==123"
