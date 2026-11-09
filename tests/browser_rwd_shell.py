"""Stage 3A: three-column desktop shell, stage-first mobile view and real controls."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / 'index.html'


class ResponsiveShellBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        opts = {'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            opts.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                        args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**opts)
        cls.html = HTML.read_text(encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1440,'height':900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e:self.errors.append(str(e)))
        self.page.set_content(self.html, wait_until='load')
        self.page.locator('#autoFeed').uncheck()

    def tearDown(self):
        try:
            self.assertEqual(self.errors,[], 'Unexpected JavaScript errors')
        finally:
            self.context.close()

    def layout(self):
        return self.page.evaluate("""() => {
          const r={width:innerWidth,scrollWidth:document.documentElement.scrollWidth};
          for(const [k,sel] of Object.entries({brand:'.app-brand',quick:'.quick-nav',
            tools:'.sidebar',stage:'.stage',below:'.below',directory:'.archive',
            inspector:'.inspector',footer:'.foot'})){
             const e=document.querySelector(sel),b=e.getBoundingClientRect();
             r[k]={x:b.x,y:b.y,width:b.width,height:b.height,
                   shown:getComputedStyle(e).display!=='none'};
          }
          return r;
        }""")

    def mobile(self,width=390):
        self.page.set_viewport_size({'width':width,'height':844})

    def no_overflow(self):
        r=self.layout()
        self.assertLessEqual(r['scrollWidth'],r['width']+1)

    def test_desktop_has_left_tools_center_canvas_right_directory(self):
        r=self.layout()
        self.assertLess(r['tools']['x'],r['stage']['x'])
        self.assertLess(r['stage']['x'],r['directory']['x'])
        self.assertAlmostEqual(r['stage']['y'],r['directory']['y'],delta=2)
        self.assertGreaterEqual(r['inspector']['y'],r['below']['y']+r['below']['height'])
        self.assertGreater(r['inspector']['width'],r['stage']['width'])
        self.assertFalse(r['quick']['shown'])
        self.no_overflow()

    def test_tablet_emphasizes_canvas_directory_and_places_tools_below(self):
        for width in [768,1024,1199]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width,'height':900})
                r=self.layout()
                self.assertLess(r['stage']['x'],r['directory']['x'])
                self.assertGreater(r['tools']['y'],r['stage']['y'])
                self.assertGreater(r['inspector']['y'],r['tools']['y'])
                self.assertFalse(r['quick']['shown'])
                self.no_overflow()

    def test_mobile_source_order_matches_visual_stage_priority(self):
        for width in [320,390,600,767]:
            with self.subTest(width=width):
                self.mobile(width)
                r=self.layout()
                self.assertTrue(r['quick']['shown'])
                order=['brand','quick','stage','below','directory','tools','inspector']
                for a,b in zip(order,order[1:]):
                    self.assertLess(r[a]['y'],r[b]['y'])
                self.no_overflow()
        self.assertTrue(self.page.evaluate("""() => [...document.querySelectorAll(
          '.quick-links a')].every(a=>a.getBoundingClientRect().height>=44)"""))
        self.assertEqual(self.page.evaluate("""() => [...document.querySelector(
          'main.layout').children].map(n=>n.className).slice(0,5)"""),
          ['brand app-brand','quick-nav','content','sidebar','panel inspector'])

    def test_mobile_navigation_and_return_to_canvas_use_native_links(self):
        self.mobile(390)
        self.page.locator('a.quick-link[href="#feedPanel"]').click()
        self.assertEqual(self.page.evaluate('location.hash'),'#feedPanel')
        self.assertTrue(self.page.locator('#feedText').is_visible())
        self.page.locator('a.quick-link[href="#archivePanel"]').click()
        self.assertEqual(self.page.evaluate('location.hash'),'#archivePanel')
        self.assertTrue(self.page.locator('.back-to-stage').is_visible())
        self.page.locator('.back-to-stage').click()
        self.assertEqual(self.page.evaluate('location.hash'),'#world')
        self.no_overflow()

    def test_mobile_counts_stay_synced_with_real_environment(self):
        self.mobile(390)
        self.page.locator('[data-tool-toggle="controlPanel"]').click()
        self.page.locator('#pauseBtn').click()
        self.page.locator('a.quick-link[href="#genePanel"]').click()
        self.page.locator('#geneText').fill('MobileABC')
        born=int(self.page.locator('#births').inner_text())
        self.page.locator('#createBtn').click()
        self.assertEqual(self.page.locator('#quickBirths').inner_text(),str(born+1))
        self.assertEqual(self.page.locator('#quickLiving').inner_text(),
                         self.page.locator('#living').inner_text())
        self.page.locator('a.quick-link[href="#feedPanel"]').click()
        self.page.locator('#feedText').fill('ABC')
        self.page.locator('#feedBtn').click()
        self.assertEqual(self.page.locator('#quickFood').inner_text(),
                         self.page.locator('#foodCount').inner_text())
        self.assertGreater(int(self.page.locator('#quickFood').inner_text()),0)
        self.page.locator('#clearFoodBtn').click()
        self.assertEqual(self.page.locator('#quickFood').inner_text(),'0')
        self.page.locator('#clearBtn').click()
        for key in ['quickLiving','quickFood','quickBirths']:
            self.assertEqual(self.page.locator('#'+key).inner_text(),'0')

    def test_mobile_archive_four_tabs_and_canvas_return(self):
        self.mobile(390)
        self.page.locator('[data-tool-toggle="controlPanel"]').click()
        self.page.locator('#pauseBtn').click()
        self.page.locator('a.quick-link[href="#genePanel"]').click()
        self.page.locator('#geneText').fill('GeneMobile')
        self.page.locator('#createBtn').click()
        self.page.locator('#archiveFilter').select_option('all')
        self.page.locator('#archiveList [data-open-creature]').first.click()
        self.assertIn('生物 #',self.page.locator('#archiveDetailTitle').inner_text())
        self.assertTrue(self.page.locator('#archiveSpecimenCanvas').is_visible())
        for tab in ['gene','life','kin','status']:
            self.page.locator(f'[data-archive-tab="{tab}"]').click()
            self.assertTrue(self.page.locator('#archiveTabBody').is_visible())
        self.page.locator('[data-detail-close="stage"]').click()
        self.assertEqual(self.page.evaluate('document.activeElement.id'),'world')
        self.no_overflow()

    def test_keyboard_native_navigation_preserves_focus_and_controls(self):
        self.mobile(390)
        link=self.page.locator('a.quick-link[href="#genePanel"]')
        link.focus()
        self.page.keyboard.press('Enter')
        self.assertEqual(self.page.evaluate('location.hash'),'#genePanel')
        self.assertTrue(self.page.locator('#createBtn').is_visible())
        self.page.locator('#geneText').fill('KeyboardGene')
        self.page.locator('#createBtn').click()
        self.assertGreaterEqual(int(self.page.locator('#living').inner_text()),4)
        self.no_overflow()

    def test_resizing_keeps_creature_identity_and_real_interactions(self):
        self.page.locator('#pauseBtn').click()
        self.page.locator('#geneText').fill('UniqueResponsiveGene')
        self.page.locator('#createBtn').click()
        born=self.page.locator('#births').inner_text()
        self.page.locator('#archiveFilter').select_option('all')
        self.assertIn('UniqueResponsiveGene',self.page.locator('#archiveList').inner_text())
        for width in [320,390,768,1024,1440]:
            self.page.set_viewport_size({'width':width,'height':900})
            self.assertEqual(self.page.locator('#births').inner_text(),born)
            self.assertIn('UniqueResponsiveGene',self.page.locator('#archiveList').inner_text())
            self.no_overflow()
        self.page.locator('#archiveList [data-open-creature]').first.click()
        self.assertIn('生物 #',self.page.locator('#archiveDetailTitle').inner_text())


if __name__ == '__main__':
    unittest.main()
