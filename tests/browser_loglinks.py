"""Global event IDs: desktop hover/focus, mouse click, mobile summary and archive links."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_records import instrument_records

HTML = Path(__file__).resolve().parents[1] / 'index.html'


class GlobalEventLinksBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        launch = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            launch.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                          args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**launch)
        fixture = instrument_records(HTML.read_text(encoding='utf-8'))
        cls.fixture = fixture.replace('window.__ecologyTest = {',
                                      'window.__ecologyTest = {writeLog: message => log(message),', 1)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':1360,'height':900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.set_content(self.fixture, wait_until='load')
        self.page.evaluate("document.querySelector('#autoFeed').checked=false")
        self.page.evaluate('window.__ecologyTest.reset("empty")')
        self.page.evaluate('window.__ecologyTest.random(0.5)')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Unexpected JavaScript errors')
        finally:
            self.context.close()

    def birth(self, gene):
        return self.page.evaluate('(g)=>window.__ecologyTest.birth(g,220,230)',gene)

    def link(self, id):
        return self.page.locator(f'#eventLog .log-creature[data-creature-id="{id}"]').first

    def test_birth_hover_has_full_gene_and_click_opens_detail(self):
        self.birth('AqMZkyLpRST')
        link = self.link(1)
        self.assertEqual(link.inner_text(),'#1')
        link.hover()
        tip=self.page.locator('#creaturePreview')
        self.assertTrue(tip.is_visible())
        self.assertEqual(tip.get_attribute('role'),'tooltip')
        self.assertEqual(link.get_attribute('aria-describedby'),'creaturePreview')
        self.assertIn('基因：AqMZkyLpRST',tip.inner_text())
        self.assertIn('存活',tip.inner_text())
        link.click()
        self.assertIn('生物 #1',self.page.locator('#archiveDetailTitle').inner_text())
        self.assertFalse(tip.is_visible())
        self.assertEqual(self.page.evaluate('window.__ecologyTest.snapshot().selected'),1)

    def test_death_link_works_when_directory_filters_only_living(self):
        self.birth('DeathGene')
        self.page.evaluate('window.__ecologyTest.configure(1,{energy:-2.44})')
        self.page.evaluate('window.__ecologyTest.step(.3)')
        self.assertEqual(self.page.locator('#archiveFilter').input_value(),'living')
        self.assertEqual(self.page.locator('#archiveList .archive-record').count(),0)
        link=self.link(1)
        link.hover()
        self.assertIn('飢餓死亡',self.page.locator('#creaturePreview').inner_text())
        link.click()
        self.assertIn('生物 #1',self.page.locator('#archiveDetailTitle').inner_text())
        self.page.locator('[data-archive-tab="gene"]').click()
        self.assertIn('DeathGene',self.page.locator('.archive-gene').inner_text())

    def test_mating_message_links_both_parents_and_offspring(self):
        self.birth('AAAAAA')
        self.birth('BBBBBB')
        for id in (1,2):
            self.page.evaluate('id=>window.__ecologyTest.configure(id,{age:6,energy:1.4,repCD:0})',id)
        self.page.evaluate('window.__ecologyTest.step(.08)')
        row=self.page.locator('#eventLog > div').filter(has_text='交配').first
        self.assertEqual(row.locator('.log-creature').all_inner_texts(),['#1','#2','#3'])
        for id in (1,2,3):
            row.locator(f'[data-creature-id="{id}"]').click()
            self.assertIn(f'生物 #{id}',self.page.locator('#archiveDetailTitle').inner_text())

    def test_keyboard_focus_enter_and_escape(self):
        self.birth('AccessibleGene')
        link=self.link(1)
        link.focus()
        self.assertIn('AccessibleGene',self.page.locator('#creaturePreview').inner_text())
        self.page.keyboard.press('Enter')
        self.assertIn('生物 #1',self.page.locator('#archiveDetailTitle').inner_text())
        self.assertFalse(self.page.locator('#creaturePreview').is_visible())
        link.focus()
        self.page.keyboard.press('Escape')
        self.assertFalse(self.page.locator('#creaturePreview').is_visible())

    def test_mobile_tap_shows_summary_and_explicit_navigation(self):
        context=self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,
                                         has_touch=True,device_scale_factor=1)
        try:
            page=context.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content(self.fixture,wait_until='load')
            page.evaluate('window.__ecologyTest.reset("empty")')
            page.evaluate('window.__ecologyTest.birth("MobileGene",220,230)')
            link=page.locator('#eventLog [data-creature-id="1"]')
            link.tap()
            tip=page.locator('#creaturePreview')
            self.assertTrue(tip.is_visible())
            self.assertEqual(tip.get_attribute('role'),'dialog')
            self.assertIn('MobileGene',tip.inner_text())
            self.assertIsNone(link.get_attribute('aria-describedby'))
            box=tip.bounding_box()
            self.assertGreaterEqual(box['x'],0)
            self.assertLessEqual(box['x']+box['width'],391)
            page.locator('#creaturePreview [data-preview-close]').tap()
            self.assertFalse(tip.is_visible())
            link.tap()
            page.locator('#creaturePreview [data-preview-open="1"]').tap()
            self.assertIn('生物 #1',page.locator('#archiveDetailTitle').inner_text())
            self.assertFalse(tip.is_visible())
            self.assertEqual(errors,[])
        finally:
            context.close()

    def test_unknown_id_remains_text_and_message_is_not_html(self):
        self.birth('A')
        self.page.evaluate('window.__ecologyTest.writeLog("不存在的 #999 <b>請忽略</b>，已知的 #1")')
        row=self.page.locator('#eventLog > div').first
        self.assertEqual(row.locator('.log-creature').count(),1)
        self.assertIn('#999',row.inner_text())
        self.assertEqual(row.locator('b').count(),0)
        self.assertIn('<b>請忽略</b>',row.inner_text())
        self.assertEqual(row.locator('.log-creature').inner_text(),'#1')

    def test_reset_closes_preview_and_log_keeps_nine_rows(self):
        self.birth('BeforeReset')
        self.link(1).hover()
        self.assertTrue(self.page.locator('#creaturePreview').is_visible())
        self.page.locator('#clearBtn').click()
        self.assertFalse(self.page.locator('#creaturePreview').is_visible())
        self.assertEqual(self.page.locator('#eventLog .log-creature').count(),0)
        for index in range(12):
            self.page.evaluate('(n)=>window.__ecologyTest.writeLog("第"+n+"筆操作")',index)
        self.assertEqual(self.page.locator('#eventLog > div').count(),9)


if __name__ == '__main__':
    unittest.main()
