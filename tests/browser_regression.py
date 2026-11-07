"""Browser-level regression checks for the unmodified v2 index.html.

Local: CHROMIUM_EXECUTABLE=/usr/bin/chromium python -m unittest discover -s tests -p 'browser_*.py' -v
GitHub Actions uses the Playwright-managed Chromium.
"""

import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / "index.html"


class V2BrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        executable = os.environ.get("CHROMIUM_EXECUTABLE")
        launch = {"headless": True}
        if executable:
            launch["executable_path"] = executable
            launch["args"] = ["--no-sandbox", "--disable-gpu"]
        cls.browser = cls.playwright.chromium.launch(**launch)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1360, "height": 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.set_content(HTML.read_text(encoding="utf-8"), wait_until="load")
        self.page.wait_for_function("document.querySelector('#living').textContent === '3'")

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], "JavaScript page error(s) occurred")
        finally:
            self.context.close()

    def count(self, element_id):
        return int(self.page.locator(f"#{element_id}").inner_text())

    def empty(self):
        self.page.locator("#clearBtn").click()
        self.assertEqual(self.count("living"), 0)
        self.assertEqual(self.count("foodCount"), 0)
        self.assertEqual(self.count("births"), 0)
        self.assertEqual(self.page.locator("#startMode").input_value(), "empty")

    def test_demo_empty_modes_and_auto_feed_without_life(self):
        self.assertEqual(self.count("living"), 3)
        self.assertEqual(self.count("births"), 3)
        self.assertEqual(self.count("foodCount"), 24)
        self.empty()
        self.assertTrue(self.page.locator("#autoFeed").is_checked())
        self.page.wait_for_timeout(3100)  # exceeds v2 automatic feeding interval
        self.assertEqual(self.count("foodCount"), 0)
        self.page.locator("#demoBtn").click()
        self.assertEqual((self.count("living"), self.count("births")), (3, 3))
        self.page.locator("#startMode").select_option("empty")
        self.page.locator("#resetBtn").click()
        self.assertEqual((self.count("living"), self.count("foodCount")), (0, 0))

    def test_five_morphologies_are_observable_from_genes(self):
        self.empty()
        for initial, expected in zip("ABCDE", ("浮游鐘", "甲殼盤", "星刺體", "節環蟲", "翼葉體")):
            with self.subTest(initial=initial):
                gene = initial + "qMZkyLpRST"
                self.page.locator("#geneText").fill(gene)
                self.assertIn(expected, self.page.locator("#previewName").inner_text())
                self.assertEqual(self.page.locator("#traitGrid .trait").count(), 11)
                self.assertEqual(self.page.locator("#traceBody tr").count(), len(gene))
                self.assertIn(f"{initial} / {ord(initial)}", self.page.locator("#traceBody tr").first.inner_text())
        self.assertEqual(self.count("living"), 0, "Preview must not create creatures")

    def test_extra_gene_character_modifies_morphology_trace(self):
        self.empty()
        self.page.locator("#geneText").fill("AqMZkyLpRST")
        self.assertIn("浮游鐘", self.page.locator("#previewName").inner_text())
        self.page.locator("#geneText").fill("AqMZkyLpRSTB")
        self.assertIn("甲殼盤", self.page.locator("#previewName").inner_text())
        self.assertEqual(self.page.locator("#traceBody tr").count(), 12)
        self.assertIn("修飾", self.page.locator("#traceBody tr").last.inner_text())

    def test_invalid_unicode_does_not_enter_genes(self):
        self.empty()
        self.page.locator("#geneText").fill("A 中b\n1")
        self.assertIn("Ab1", self.page.locator("#previewText").inner_text())
        self.assertEqual(self.page.locator("#traceBody tr").count(), 3)
        self.assertIn("1 個非 ASCII", self.page.locator("#geneWarning").inner_text())
        self.assertIn("65", self.page.locator("#traceBody").inner_text())

    def test_create_inspect_and_change_preview_source(self):
        self.empty()
        self.page.locator("#autoFeed").uncheck()
        gene = "CqMZkyLpRST"
        self.page.locator("#geneText").fill(gene)
        self.page.locator("#createBtn").click()
        self.assertEqual((self.count("living"), self.count("births")), (1, 1))
        self.assertIn(gene, self.page.locator("#selectedInfo").inner_text())
        self.assertTrue(self.page.locator("#tabSelected").is_enabled())
        self.page.locator("#tabSelected").click()
        self.assertIn("生物 #1", self.page.locator("#previewName").inner_text())
        self.assertIn(gene, self.page.locator("#previewText").inner_text())
        self.page.locator("#geneText").fill("EqMZkyLpRST")
        self.assertIn("翼葉體", self.page.locator("#previewName").inner_text())
        self.assertEqual(self.count("living"), 1)

    def test_feed_text_and_full_reset_are_separate(self):
        self.empty()
        self.page.locator("#autoFeed").uncheck()
        self.page.locator("#feedText").fill("A a! ")
        self.page.locator("#feedBtn").click()
        self.assertEqual(self.count("foodCount"), 3)
        self.assertEqual(self.count("living"), 0)
        self.page.locator("#clearBtn").click()
        self.assertEqual((self.count("foodCount"), self.count("births")), (0, 0))

    def test_canvas_click_drops_selected_feed_character(self):
        self.empty()
        self.page.locator("#feedText").fill("Z")
        self.page.locator("#scatterBtn").click()
        self.assertEqual(self.count("foodCount"), 0, "Random feed requires a living creature")
        self.page.locator("#world").click(position={"x": 120, "y": 160})
        self.assertEqual(self.count("foodCount"), 1)

    def test_pause_resume_and_speed_display(self):
        self.empty()
        self.page.locator("#pauseBtn").click()
        self.assertIn("模擬已暫停", self.page.locator("#indicator").inner_text())
        self.page.locator("#simSpeed").fill("2.5")
        self.assertIn("2.5 倍", self.page.locator("#speedVal").inner_text())
        self.page.locator("#pauseBtn").click()
        self.assertIn("模擬進行中", self.page.locator("#indicator").inner_text())

    def test_population_and_feed_capacity(self):
        self.empty()
        self.page.locator("#autoFeed").uncheck()
        self.page.locator("#pauseBtn").click()
        self.page.locator("#geneText").fill("AqMZkyLpRST")
        for _ in range(29):
            self.page.locator("#createBtn").click()
        self.assertEqual((self.count("living"), self.count("births")), (28, 28))
        self.page.locator("#feedText").fill("A" * 100)
        for _ in range(3):
            self.page.locator("#feedBtn").click()
        self.assertEqual(self.count("foodCount"), 220)

    def test_mobile_tablet_desktop_no_horizontal_overflow(self):
        self.empty()
        for width, height in [(390, 844), (768, 1024), (1024, 768), (1440, 900)]:
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": height})
                self.page.wait_for_timeout(80)
                actual = self.page.evaluate("document.documentElement.scrollWidth")
                self.assertLessEqual(actual, width + 1, f"Horizontal overflow at width={width}: {actual}px")
                self.assertTrue(self.page.locator("#world").is_visible())
                self.assertTrue(self.page.locator("#inspector").is_visible())


if __name__ == "__main__":
    unittest.main()
