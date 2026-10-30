"""A new collection batch must not hide earlier pending project photos."""

from playwright.sync_api import expect

from conftest import add_reference
from ref_lab.models import JobInput
from test_ui_components import component_factory  # noqa: F401 - shared Chromium bridge fixture


def test_project_stats_return_from_batch_and_selected_to_all_pending(component_factory, client, library, project):
    old = add_reference(client, project, 101)
    job = library.create_job(project['id'], JobInput(kind='collection', notes='第二批'))
    first = add_reference(client, project, 102, job_id=job['id'])
    second = add_reference(client, project, 103, job_id=job['id'])
    kept = client.patch(f"/api/references/{second['id']}", json={
        'expected_revision': second['revision'], 'decision': 'keep', 'lane': 'field',
    })
    assert kept.status_code == 200, kept.text

    page = component_factory(f"view=references&project={project['id']}&job={job['id']}")
    expect(page.locator('#page-count')).to_have_text('1–2 / 2')
    expect(page.locator('#stats')).to_contain_text('待挑选')
    page.get_by_role('button', name='查看待挑选，2张').click()
    page.wait_for_function('(oldId) => !state.jobId && state.decision === "pending" && state.refs.some(ref => ref.id === oldId)', arg=old['id'])
    assert {item['id'] for item in page.evaluate('state.refs')} == {old['id'], first['id']}
    assert page.evaluate('state.jobId') == ''
    assert page.evaluate('state.decision') == 'pending'

    page.get_by_role('button', name='查看角色精选，1张').click()
    expect(page.locator('#page-count')).to_have_text('1–1 / 1')
    page.get_by_role('button', name='查看待挑选，2张').click()
    page.wait_for_function('(oldId) => state.view === "references" && state.decision === "pending" && state.refs.some(ref => ref.id === oldId)', arg=old['id'])
    assert {item['id'] for item in page.evaluate('state.refs')} == {old['id'], first['id']}

    page.evaluate('(job) => candidateQueueDialog(job.id, job)', job)
    page.get_by_role('button', name='查看本项目全部待挑选').click()
    assert {item['id'] for item in page.evaluate('state.refs')} == {old['id'], first['id']}
