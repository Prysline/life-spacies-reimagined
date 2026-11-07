"""Browser regression tests for the living/dead directory and shared specimen details."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_records import instrument_records

HTML = Path(__file__).resolve().parents[1] / 'index.html'


class ArchiveBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        opts = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            opts.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                        args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**opts)
        cls.fixture = instrument_records(HTML.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1360, 'height': 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.set_content(self.fixture, wait_until='load')
        self.page.evaluate("document.querySelector('#autoFeed').checked=false")
        self.page.evaluate('window.__ecologyTest.random(0.5)')
        self.page.evaluate('window.__ecologyTest.reset("empty")')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Unexpected JavaScript page errors')
        finally:
            self.context.close()

    def birth(self, gene, generation=1):
        return self.page.evaluate('([gene,gen])=>window.__ecologyTest.birth(gene,220,230,gen)',
                                  [gene,generation])

    def records(self):
        return self.page.evaluate('window.__ecologyTest.records()')

    def configure(self, id, **fields):
        self.page.evaluate('([id,fields])=>window.__ecologyTest.configure(id,fields)',
                           [id,fields])

    def step(self, dt):
        self.page.evaluate('(dt)=>window.__ecologyTest.step(dt)', dt)

    def list_ids(self):
        return self.page.locator('#archiveList [data-open-creature]').evaluate_all(
            '(els)=>els.map(el=>Number(el.dataset.openCreature))')

    def open(self, id):
        self.page.locator(f'#archiveList [data-open-creature="{id}"]').click()

    def tab(self, name):
        self.page.locator(f'[data-archive-tab="{name}"]').click()

    def test_living_dead_all_filters_and_death_archive(self):
        self.birth('AZZ')
        self.assertEqual(self.list_ids(), [1])
        self.configure(1, energy=-2.44)
        self.step(.3)
        self.assertEqual(self.list_ids(), [])
        self.page.locator('#archiveFilter').select_option('dead')
        self.assertEqual(self.list_ids(), [1])
        self.open(1)
        self.assertIn('飢餓死亡', self.page.locator('#archiveDetail').inner_text())
        self.assertEqual(self.page.locator('#archiveDetail [data-archive-tab]').count(), 4)
        self.tab('gene')
        self.assertEqual(self.page.locator('.archive-gene').inner_text(), 'AZZ')
        self.page.locator('#archiveFilter').select_option('all')
        self.assertEqual(self.list_ids(), [1])

    def test_search_case_insensitive_gene_and_id_and_sort(self):
        self.birth('AqM123')
        self.birth('BzM456')
        self.birth('CqM789')
        self.assertEqual(self.list_ids(), [3,2,1])
        self.page.locator('#archiveSort').select_option('id-asc')
        self.assertEqual(self.list_ids(), [1,2,3])
        self.page.locator('#archiveSearch').fill('QM')
        self.assertEqual(self.list_ids(), [1,3])
        self.page.locator('#archiveSearch').fill('#2')
        self.assertEqual(self.list_ids(), [2])
        self.page.locator('#archiveSearch').fill('missing')
        self.assertEqual(self.list_ids(), [])
        self.assertIn('沒有符合條件', self.page.locator('#archiveList').inner_text())
        self.page.locator('#archiveSearch').fill('')
        self.page.locator('#archiveSort').select_option('generation')
        self.assertEqual(self.list_ids(), [3,2,1])

    def test_full_gene_formula_and_event_history(self):
        self.birth('AqMZkyLpRSTB')
        self.open(1)
        self.tab('gene')
        self.assertEqual(self.page.locator('.archive-traits > div').count(), 11)
        self.assertEqual(self.page.locator('.archive-trace tbody tr').count(), 12)
        self.assertIn('B / 66', self.page.locator('.archive-trace').inner_text())
        self.tab('life')
        self.assertIn('出生（輸入生成）', self.page.locator('#archiveTabBody').inner_text())
        self.assertEqual(self.page.locator('.archive-events li').count(), 1)

    def test_two_parents_child_links_and_shared_mating_event(self):
        self.birth('AAAAAA')
        self.birth('BBBBBB')
        for id in (1,2):
            self.configure(id, age=6, energy=1.4, repCD=0)
        self.step(.3)
        self.assertEqual(len(self.records()), 3)
        self.open(3)
        self.tab('kin')
        self.assertEqual(self.page.locator('#archiveTabBody [data-open-creature]').count(), 2)
        self.page.locator('#archiveTabBody [data-open-creature="1"]').click()
        self.assertIn('生物 #1', self.page.locator('#archiveDetailTitle').inner_text())
        self.tab('kin')
        self.page.locator('#archiveTabBody [data-open-creature="3"]').click()
        self.tab('life')
        self.assertIn('交配：', self.page.locator('#archiveTabBody').inner_text())
        self.assertEqual(self.page.locator('.archive-events li').count(), 2)

    def test_canvas_selection_and_archive_selection_share_live_id(self):
        self.birth('AqMZkyLpRST')
        state = self.page.evaluate('window.__ecologyTest.snapshot().creatures[0]')
        canvas = self.page.locator('#world')
        box = canvas.bounding_box()
        extent = canvas.evaluate('(el)=>({width:el.width,height:el.height})')
        ratio = self.page.evaluate('window.devicePixelRatio')
        x = box['x'] + state['x'] * box['width'] / (extent['width']/ratio)
        y = box['y'] + state['y'] * box['height'] / (extent['height']/ratio)
        self.page.mouse.click(x,y)
        self.assertIn('生物 #1', self.page.locator('#archiveDetailTitle').inner_text())
        self.assertEqual(self.page.locator('.archive-record[aria-current="true"]').count(), 1)
        self.assertEqual(self.page.evaluate('window.__ecologyTest.snapshot().selected'), 1)

    def test_100_event_pagination_and_reset(self):
        self.birth('A')
        for _ in range(110):
            self.configure(1, energy=0)
            self.page.evaluate('window.__ecologyTest.drop("A",220,230)')
            self.step(.001)
        self.open(1)
        self.tab('life')
        self.assertEqual(self.page.locator('.archive-events li').count(), 100)
        self.page.locator('#archiveMoreHistory').click()
        self.assertEqual(self.page.locator('.archive-events li').count(), 111)
        self.page.locator('#clearBtn').click()
        self.assertEqual(self.list_ids(), [])
        self.assertIn('選擇名冊中的個體', self.page.locator('#archiveDetail').inner_text())
        self.assertEqual(self.records(), [])

    def test_mobile_tablet_desktop_overflow_and_navigation(self):
        self.birth('AqMZkyLpRST')
        for width,height in [(320,720),(390,844),(768,1024),(1024,768),(1440,900)]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width,'height':height})
                self.open(1)
                for name in ['status','gene','life','kin']:
                    self.tab(name)
                    self.assertTrue(self.page.locator('#archiveTabBody').is_visible())
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width+1)


if __name__ == '__main__':
    unittest.main()
