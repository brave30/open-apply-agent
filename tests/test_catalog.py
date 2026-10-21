from collections import Counter
from auto_apply.catalog import applications, render_application


def test_catalog_contains_twenty_distinct_forms():
    catalog = applications()
    assert len({app['id'] for app in catalog}) == 20
    assert Counter(app['platform'] for app in catalog) == {'Workday': 5, 'Greenhouse': 5, 'Lever': 5, 'Other': 5}
    for app in catalog:
        page = render_application(app['id'])
        assert app['company'] in page
        assert 'action="/submit"' in page
        assert 'type="file"' in page
        assert len({f['id'] for f in app['fields']}) == len(app['fields'])
    assert 'let step=0' in render_application('workday-1')
    assert 'let step=0' not in render_application('greenhouse-1')


def test_unknown_application_rejected():
    import pytest
    with pytest.raises(ValueError):
        render_application('not-a-real-application')
