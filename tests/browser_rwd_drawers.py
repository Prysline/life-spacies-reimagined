"""Stage 3B-2: desktop inline detail drawer and tablet directory disclosure."""
import unittest
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=Path(__file__).resolve().parents[1].joinpath('index.html').read_text(encoding='utf-8')


class ResponsiveDrawersBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        options={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                           args=['--no-sandbox','--disable-gpu'])
        cls.browser=cls.playwright.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1440,'height':900})
        self.page=self.context.new_page()
        self.errors=[]
        self.page.on('pageerror', lambda error:self.errors.append(str(error)))
        self.page.set_content(HTML,wait_until='load')
        self.page.locator('#pauseBtn').click()

    def tearDown(self):
        try:self.assertEqual(self.errors,[])
        finally:self.context.close()

    def resize(self,width):
        self.page.set_viewport_size({'width':width,'height':900})

    def add(self):
        self.page.locator('#geneText').fill('TestGeneQ')
        self.page.locator('#createBtn').click()
        return self.page.locator('#archiveList [data-open-creature]').first

    def test_desktop_detail_is_closed_until_selected(self):
        self.assertTrue(self.page.locator('#archiveDetail').is_hidden())
        self.add().click()
        self.assertTrue(self.page.locator('#archiveDetail').is_visible())
        self.assertTrue(self.page.locator('[data-detail-close="list"]').is_visible())
        self.assertLess(self.page.locator('.archive-list').evaluate('(e)=>e.getBoundingClientRect().height'),190)
        self.assertLess(self.page.locator('.archive').evaluate('(e)=>e.getBoundingClientRect().right'),1440)
        self.page.locator('[data-archive-tab="gene"]').click()
        self.page.locator('[data-detail-close="list"]').click()
        self.assertTrue(self.page.locator('#archiveDetail').is_hidden())
        self.assertTrue(self.page.locator('#archiveList').is_visible())

    def test_event_link_opens_drawer_and_restores_focus(self):
        self.add()
        self.page.locator('#eventLog .log-creature').first.click()
        self.assertTrue(self.page.locator('#archiveDetail').is_visible())
        self.page.locator('[data-detail-close="list"]').click()
        self.assertEqual(self.page.evaluate(
            'document.activeElement.closest("[data-open-creature]")?.dataset.openCreature'), '4')

    def test_tablet_collapse_expands_canvas(self):
        self.resize(768)
        before=self.page.locator('#world').evaluate('(e)=>e.getBoundingClientRect().width')
        self.page.locator('#tabletDirectoryToggle').click()
        self.assertEqual(self.page.locator('#tabletDirectoryToggle').get_attribute('aria-expanded'),'false')
        self.assertTrue(self.page.locator('#archiveSearch').is_hidden())
        after=self.page.locator('#world').evaluate('(e)=>e.getBoundingClientRect().width')
        self.assertGreater(after,before+100)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),769)
        self.page.locator('#tabletDirectoryToggle').click()
        self.assertTrue(self.page.locator('#archiveSearch').is_visible())

    def test_tablet_event_auto_reopens_directory(self):
        self.resize(1024)
        self.page.locator('#tabletDirectoryToggle').click()
        self.page.locator('#eventLog .log-creature').first.click()
        self.assertEqual(self.page.locator('#tabletDirectoryToggle').get_attribute('aria-expanded'),'true')
        self.assertTrue(self.page.locator('#archiveDetail').is_visible())
        self.page.locator('[data-detail-close="list"]').click()
        self.assertTrue(self.page.locator('#archiveDetail').is_hidden())
        self.assertTrue(self.page.locator('#archiveSearch').is_visible())

    def test_tab_and_genome_survive_resizing(self):
        self.add().click()
        self.page.locator('[data-archive-tab="gene"]').click()
        text=self.page.locator('#archiveTabBody').inner_text()
        self.resize(1024)
        self.assertTrue(self.page.locator('#archiveTabBody').is_visible())
        self.assertEqual(text,self.page.locator('#archiveTabBody').inner_text())
        self.resize(390)
        self.page.locator('#archiveList [data-open-creature]').first.click()
        self.assertTrue(self.page.locator('.specimen-open .archive-detail').is_visible())
        self.page.locator('[data-detail-close="stage"]').click()
        self.assertFalse(self.page.locator('body').evaluate(
            '(e)=>e.classList.contains("specimen-open")'))

    def test_reset_clears_open_detail_and_records(self):
        self.add().click()
        self.page.locator('#clearBtn').click()
        self.assertTrue(self.page.locator('#archiveDetail').is_hidden())
        self.assertIn('0 / 0',self.page.locator('#archiveCount').inner_text())

    def test_all_breakpoints_have_no_horizontal_overflow(self):
        for width in (320,390,767,768,1024,1199,1200,1360,1440):
            with self.subTest(width=width):
                self.resize(width)
                self.assertLessEqual(
                    self.page.evaluate('document.documentElement.scrollWidth'),width+1)


if __name__=='__main__':
    unittest.main()
