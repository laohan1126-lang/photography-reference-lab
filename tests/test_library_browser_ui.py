"""Actual Chromium DOM and API bridge with synthetic image fixtures."""
from playwright.sync_api import expect
from conftest import add_reference
from test_ui_components import component_factory, screenshot


def go_gallery(page):
    page.get_by_role('button',name='图库 · 跨项目找图',exact=True).click()
    expect(page.locator('#library-status')).not_to_have_text('正在查找…')


def test_bounded_project_navigation_search_pin_and_directory(component_factory,client,project):
    add_reference(client,project)
    for i in range(34):
        client.post('/api/projects',json={'character':f'检索项目{i:02d}'})
    page=component_factory()
    assert page.locator('#project-list [data-project-open]').count()==8
    page.locator('#project-search').fill('检索项目01')
    assert page.locator('#project-list [data-project-open]').count()==1
    page.locator('#project-list [data-project-pin]').click()
    expect(page.locator('#project-list [data-project-pin]')).to_have_attribute('aria-pressed','true')
    page.locator('#project-list [data-project-open]').click()
    expect(page.locator('#project-header')).to_contain_text('检索项目01')
    page.locator('#project-search').fill('')
    assert page.locator('#project-list [data-project-open]').count()==8
    page.locator('#all-projects').click()
    assert page.locator('#project-directory-list [data-project-open]').count()==30
    assert page.locator('#project-directory-list .project-link strong').first.evaluate('(el)=>getComputedStyle(el).color')=='rgb(24, 48, 57)'
    screenshot(page,'project-directory-synthetic.png')
    page.locator('#project-directory-next').click()
    assert page.locator('#project-directory-list [data-project-open]').count()==5
    page.locator('#project-directory-search').fill('检索项目02')
    assert page.locator('#project-directory-list [data-project-open]').count()==1
    page.locator('#project-directory-list [data-project-open]').click()
    expect(page.locator('#project-header')).to_contain_text('检索项目02')


def test_gallery_combined_filters_saved_search_and_mobile(component_factory,client,project):
    refs=[add_reference(client,project,seed=i) for i in range(3)]
    response=client.put(f"/api/library/assets/{refs[0]['asset_sha']}/annotation",json={'expected_revision':0,'viewpoint':'low_angle','framing':'full_body'})
    assert response.status_code==200
    page=component_factory()
    go_gallery(page)
    expect(page.locator('.library-tile')).to_have_count(3)
    page.locator('#library-filter-form [name=viewpoint]').select_option('low_angle')
    page.locator('#library-filter-form [name=framing]').select_option('full_body')
    page.get_by_role('button',name='查找',exact=True).click()
    expect(page.locator('.library-tile')).to_have_count(1)
    page.locator('#library-save-search').click()
    page.get_by_label('搜索名称',exact=True).fill('仰拍全身')
    page.get_by_role('button',name='保存搜索',exact=True).click()
    expect(page.locator('#editor')).not_to_be_visible()
    expect(page.locator('#library-saved-search option')).to_have_count(2)
    page.locator('#library-reset').click()
    expect(page.locator('.library-tile')).to_have_count(3)
    page.locator('#library-saved-search').select_option(label='仰拍全身')
    expect(page.locator('.library-tile')).to_have_count(1)
    screenshot(page,'library-desktop-synthetic.png')
    fragment=page.evaluate('location.hash')
    reopened=component_factory(fragment)
    expect(reopened.locator('.library-tile')).to_have_count(1)
    expect(reopened.locator('#library-filter-form [name=viewpoint]')).to_have_value('low_angle')
    reopened.set_viewport_size({'width':390,'height':844})
    assert reopened.evaluate('document.documentElement.scrollWidth <= innerWidth')
    expect(reopened.locator('#all-projects')).to_be_visible()
    reopened.locator('#all-projects').click()
    expect(reopened.locator('#project-directory-search')).to_be_visible()
    reopened.locator('#editor-close').click()
    screenshot(reopened,'library-mobile-synthetic.png')
    page.once('dialog',lambda dialog:dialog.accept())
    page.locator('#library-delete-search').click()
    expect(page.locator('#library-saved-search option')).to_have_count(1)
    assert client.get('/api/library/assets').json()['total']==3


def test_gallery_classification_does_not_curate_and_opens_exact_use(component_factory,client,project,library):
    refs=[add_reference(client,project,seed=i) for i in range(4)]
    ref=refs[0]
    before=library.reference(ref['id'])
    page=component_factory()
    go_gallery(page)
    page.locator(f'[data-library-item="{ref["asset_sha"]}"]').click()
    page.locator('#editor select[name=viewpoint]').select_option('high_angle')
    page.get_by_role('button',name='保存摄影分类',exact=True).click()
    expect(page.locator('#editor')).not_to_be_visible()
    assert library.reference(ref['id'])==before
    page.locator(f'[data-library-item="{ref["asset_sha"]}"]').click()
    page.locator(f'[data-library-use="{ref["id"]}"]').click()
    expect(page.locator('#main-image')).to_have_attribute('alt',ref['title'])
    assert page.evaluate('state.activeId')==ref['id']


def test_late_gallery_response_cannot_overwrite_another_view(component_factory,client,project):
    add_reference(client,project)
    page=component_factory()
    go_gallery(page)
    page.evaluate("""() => {
      const original=window.fetch;
      window.fetch=(url,options)=>String(url).startsWith('/api/library/assets?')&&String(url).includes('q=slow')
        ? new Promise(resolve=>window.releaseGallery=()=>original(url,options).then(resolve))
        : original(url,options);
    }""")
    page.get_by_label('跨项目搜索图片',exact=True).fill('slow')
    page.get_by_role('button',name='查找',exact=True).click()
    page.wait_for_function('typeof window.releaseGallery === "function"')
    page.get_by_role('button',name='摄影笔记',exact=True).click()
    page.evaluate('window.releaseGallery()')
    expect(page.locator('#project-header')).to_contain_text('摄影笔记')
    expect(page.locator('#library-grid')).to_have_count(0)

def test_ai_suggestion_is_visible_in_project_detail_and_human_correction_wins(component_factory, client, project, library):
    from ref_lab.classification import ClassificationQueue
    from ref_lab.library_browser import LibraryBrowser
    from test_classification import Analyzer, keep
    ref = keep(client, add_reference(client, project))
    q = ClassificationQueue(LibraryBrowser(library))
    q.discover()
    q.run_one(Analyzer())
    page = component_factory()
    expect(page.locator('#reference-classification-summary')).to_contain_text('仰拍')
    page.locator('#reference-classification-edit').click()
    expect(page.locator('#photo-classification-status')).to_contain_text('AI 初步分类')
    expect(page.locator('#editor [name=pose]')).to_have_value('standing')
    page.locator('#editor [name=viewpoint]').select_option('high_angle')
    page.get_by_role('button',name='保存摄影分类',exact=True).click()
    expect(page.locator('#editor')).not_to_be_visible()
    page.locator('#reference-classification-edit').click()
    expect(page.locator('#photo-classification-status')).to_contain_text('已由你修正')
    expect(page.locator('#editor [name=viewpoint]')).to_have_value('high_angle')
    assert library.reference(ref['id'])['decision'] == 'keep'


def test_editor_merges_late_ai_into_untouched_fields(component_factory, client, project, library):
    from ref_lab.classification import ClassificationQueue
    from ref_lab.library_browser import LibraryBrowser
    from test_classification import Analyzer, keep
    ref = keep(client, add_reference(client, project))
    q = ClassificationQueue(LibraryBrowser(library))
    q.discover()
    page = component_factory()
    page.locator('#reference-classification-edit').click()
    page.locator('#editor [name=viewpoint]').select_option('high_angle')
    q.run_one(Analyzer())
    page.get_by_role('button',name='保存摄影分类',exact=True).click()
    expect(page.locator('#editor')).not_to_be_visible()
    annotation = client.get(f"/api/library/assets/{ref['asset_sha']}/classification").json()['annotation']
    assert annotation['actor'] == 'human'
    assert annotation['viewpoint'] == 'high_angle'
    assert annotation['framing'] == 'full_body' and annotation['pose'] == 'standing'

def test_human_conflict_in_classification_editor_is_not_silently_overwritten(component_factory, client, project, library):
    from ref_lab.library_browser import AnnotationInput, LibraryBrowser
    ref = add_reference(client, project)
    page = component_factory()
    page.locator('#reference-classification-edit').click()
    page.locator('#editor [name=viewpoint]').select_option('high_angle')
    LibraryBrowser(library).annotate(ref['asset_sha'],
        AnnotationInput(expected_revision=0, viewpoint='low_angle'))
    page.get_by_role('button',name='保存摄影分类',exact=True).click()
    expect(page.locator('#toast')).to_contain_text('分类已被其他窗口修改')
    expect(page.locator('#editor')).to_be_visible()
    expect(page.locator('#editor [name=viewpoint]')).to_have_value('high_angle')
    annotation = client.get(f"/api/library/assets/{ref['asset_sha']}/classification").json()['annotation']
    assert annotation['viewpoint'] == 'low_angle'
