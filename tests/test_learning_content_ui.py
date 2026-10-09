"""Reader relationships and draft ownership, independent of visual accuracy."""
from playwright.sync_api import expect, sync_playwright
import pytest

from test_learning_ui import learning_app, learning_site, _unlock
from conftest import image_bytes

HEIGHT_SKILL = "perspective-skill-height-proportion-diagnosis"


@pytest.mark.parametrize("width", [1440, 390])
def test_notes_training_links_preserve_draft_and_do_not_write_state(learning_site, width):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 900})
        _unlock(page, origin)
        before = page.request.get(origin + "/api/learning-state").json()
        page.goto(origin + "/learning#skill=" + HEIGHT_SKILL)
        expect(page.locator('[role="tab"][data-learning-panel="notes"]')).to_have_attribute("aria-selected", "true")
        expect(page.locator("#skill-practice")).to_be_hidden()
        assert page.locator("[data-learning-note]").count() == 4
        page.locator("#skill-notes").fill("切换笔记与训练时保留我的草稿")
        note = page.locator("[data-learning-note]").first
        note_id = note.get_attribute("data-learning-note")
        forward = note.locator("[data-learning-training-target]").first
        training_id = forward.get_attribute("data-learning-training-target")
        forward.click()
        training = page.locator(f'[data-learning-training="{training_id}"]')
        expect(training).to_be_visible()
        expect(page.locator('[data-learning-panel="training"]')).to_have_attribute("aria-selected", "true")
        expect(training).to_contain_text("依据笔记")
        training.locator(f'[data-learning-note-target="{note_id}"]').click()
        expect(note).to_be_visible()
        expect(page.locator("#skill-notes")).to_have_value("切换笔记与训练时保留我的草稿")
        expect(page.locator("#skill-status")).to_have_value("unassessed")
        assert page.request.get(origin + "/api/learning-state").json() == before
        assert page.url.endswith("#skill=" + HEIGHT_SKILL)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        # Missing private teaching media is visible; it must not be a fake photo.
        expect(note.locator(".learning-media-unavailable").first).to_be_visible()
        page.locator('[data-learning-panel="training"]').click()
        training.locator("[data-training-record]").click()
        assert training.locator("h3").inner_text() in page.locator("#record-text").input_value()
        assert "依据笔记" in page.locator("#record-text").input_value()
        page.locator("#record-cancel").click()
        expect(page.locator("#skill-notes")).to_have_value("切换笔记与训练时保留我的草稿")
        browser.close()


def test_existing_skill_has_separate_honest_reading_and_training(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _unlock(page, origin)
        page.goto(origin + "/learning#skill=perspective-skill-height-vs-pitch")
        expect(page.locator("#skill-learning-notes")).to_be_visible()
        assert page.locator("[data-learning-note]").count() == 0
        expect(page.locator("#skill-learning-notes")).to_contain_text("现有要点")
        page.locator('[data-learning-panel="notes"]').press("ArrowRight")
        expect(page.locator("#skill-practice")).to_be_visible()
        expect(page.locator("#skill-practice")).to_contain_text("依据")
        expect(page.locator("#skill-status")).to_have_value("unassessed")
        browser.close()


def test_teaching_viewer_returns_focus_and_training_log_keeps_origin(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        # Synthetic bytes exercise viewer behavior only; real images are checked separately.
        page.route("**/api/learning-note-media/*", lambda route: route.fulfill(
            status=200, content_type="image/png", body=image_bytes()))
        _unlock(page, origin)
        page.goto(origin + "/learning#skill=" + HEIGHT_SKILL)
        photo = page.locator(".learning-media-open").first
        expect(photo.locator("img")).to_be_visible()
        page.wait_for_function("document.querySelector('.learning-media img').naturalWidth > 0")
        photo.click()
        expect(page.locator("#learning-image-dialog")).to_be_visible()
        expect(page.locator("#learning-image-caption")).not_to_be_empty()
        page.keyboard.press("Escape")
        expect(photo).to_be_focused()
        page.locator('[data-learning-panel="training"]').click()
        page.locator("[data-training-record]").first.click()
        text = page.locator("#record-text").input_value() + "\n距离改变后鼻耳比例更自然。"
        page.locator("#record-text").fill(text)
        page.evaluate("location.hash = '#skill=perspective-skill-height-vs-pitch'")
        expect(page.locator("#skill-title")).to_have_text("区分相机高度与镜头俯仰")
        with page.expect_response(lambda response: response.request.method == "POST" and "/logs" in response.url) as saved:
            page.locator("#record-save").click()
        assert saved.value.status == 201
        stored = page.request.get(origin + "/api/learning-state").json()["skills"]
        assert stored[HEIGHT_SKILL]["logs"][0]["text"] == text
        assert not stored.get("perspective-skill-height-vs-pitch", {}).get("logs")
        browser.close()


def test_authored_notes_without_authored_training_keep_existing_basis_target(learning_site):
    _, _, origin, _ = learning_site
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        def notes_only(route):
            # A legal catalogue combination: no new training yet, original practice remains.
            response = route.fetch()
            payload = response.json()
            payload["learning_content"]["trainings"] = []
            route.fulfill(response=response, json=payload)

        page.route("**/static/learning-atlas.json", notes_only)
        _unlock(page, origin)
        page.goto(origin + "/learning#skill=" + HEIGHT_SKILL)
        page.locator('[data-learning-training-target="existing"]').click()
        expect(page.locator("#skill-practice")).to_be_visible()
        page.locator('#skill-practice [data-learning-note-target="existing"]').click()
        expect(page.locator("#learning-note-existing")).to_be_visible()
        expect(page.locator("#learning-note-existing")).to_be_focused()
        browser.close()
