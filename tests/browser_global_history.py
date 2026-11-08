"""Complete global ecology history: canonical events, type filter, paging and linked IDs."""
import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_records import instrument_records

HTML = Path(__file__).resolve().parents[1] / 'index.html'


def history_fixture(html):
    instrumented = instrument_records(html)
    anchor = 'window.__ecologyTest = {'
    if instrumented.count(anchor) != 1:
        raise ValueError('Ecology test fixture changed; review instrumentation')
    additions = (
        'historyDie: id => {const c=world.find(c=>c.id===id);'
        'if(!c)throw Error("not living");c.energy=-2.44;update(.3);},'
        'historyMate: (a,b) => {for(const id of [a,b]){'
        'const c=world.find(c=>c.id===id);'
        'Object.assign(c,{age:6,energy:1.4,repCD:0});}'
        'update(.08);},'
        'historyFeed: ch => {const c=world.find(c=>c.id===1);'
        'c.energy=0;dropChar(ch,c.x,c.y);update(.04);},'
    )
    return instrumented.replace(anchor, anchor + additions, 1)


class GlobalHistoryBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        options = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            options.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                           args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**options)
        cls.fixture = history_fixture(HTML.read_text(encoding='utf-8'))

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
        self.page.evaluate('window.__ecologyTest.reset("empty")')
        self.page.evaluate('document.querySelector("#autoFeed").checked=false')
        self.page.evaluate('window.__ecologyTest.random(0.5)')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Unexpected JavaScript errors')
        finally:
            self.context.close()

    def birth(self, gene='A'):
        return self.page.evaluate('(gene)=>window.__ecologyTest.birth(gene,220,230)', gene)

    def die(self, id):
        self.page.evaluate('(id)=>window.__ecologyTest.historyDie(id)', id)

    def toggle(self):
        self.page.locator('#historyToggle').click()

    def items(self):
        return self.page.locator('#historyList > li')

    def test_opening_empty_history_is_accessible(self):
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '0 筆重大事件')
        self.assertTrue(self.page.locator('#globalHistory').is_hidden())
        self.toggle()
        self.assertEqual(self.page.locator('#historyToggle').get_attribute('aria-expanded'), 'true')
        self.assertEqual(self.items().count(), 0)
        self.assertTrue(self.page.locator('#historyEmpty').is_visible())
        self.assertTrue(self.page.locator('#historyPrev').is_disabled())
        self.assertTrue(self.page.locator('#historyNext').is_disabled())
        self.toggle()
        self.assertTrue(self.page.locator('#globalHistory').is_hidden())

    def test_paginate_thirty_major_events_and_filter_birth_death(self):
        for _ in range(15):
            id = self.birth('A')
            self.die(id)
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '30 筆重大事件')
        self.assertLessEqual(self.page.locator('#eventLog > div').count(), 9)
        self.toggle()
        self.assertEqual(self.items().count(), 25)
        self.assertIn('第 1 / 2 頁', self.page.locator('#historyPage').inner_text())
        self.assertIn('因飢餓死亡', self.items().first.inner_text())
        self.page.locator('#historyNext').click()
        self.assertEqual(self.items().count(), 5)
        self.assertIn('第 2 / 2 頁', self.page.locator('#historyPage').inner_text())
        self.assertIn('生物 #1 出生', self.items().last.inner_text())
        self.page.locator('#historyPrev').click()
        self.assertEqual(self.items().count(), 25)
        self.page.locator('#historyType').select_option('birth')
        self.assertEqual(self.items().count(), 15)
        self.assertIn('第 1 / 1 頁', self.page.locator('#historyPage').inner_text())
        self.assertNotIn('死亡', self.page.locator('#historyList').inner_text())
        self.page.locator('#historyType').select_option('death')
        self.assertEqual(self.items().count(), 15)
        self.assertNotIn('出生', self.page.locator('#historyList').inner_text())

    def test_shared_mating_links_and_canonical_event_count(self):
        self.birth('AAAAAA')
        self.birth('BBBBBB')
        self.page.evaluate('window.__ecologyTest.historyMate(1,2)')
        self.assertEqual(len(self.page.evaluate('window.__ecologyTest.records()')), 3)
        self.toggle()
        self.assertEqual(self.items().count(), 4)
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '4 筆重大事件')
        self.page.locator('#historyType').select_option('mate')
        self.assertEqual(self.items().count(), 1)
        self.assertEqual(self.items().first.locator('.log-creature').all_inner_texts(),
                         ['#1', '#2', '#3'])
        self.items().first.locator('[data-creature-id="3"]').click()
        self.assertIn('生物 #3', self.page.locator('#archiveDetailTitle').inner_text())

    def test_personal_meals_do_not_pollute_global_history(self):
        self.birth('A')
        for _ in range(6):
            self.page.evaluate('window.__ecologyTest.historyFeed("A")')
        events = self.page.evaluate('window.__ecologyTest.history()')
        self.assertGreater(sum(e['type'] == 'eat' for e in events), 0)
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '1 筆重大事件')
        self.toggle()
        self.assertEqual(self.items().count(), 1)
        self.assertNotIn('進食', self.page.locator('#historyList').inner_text())
        self.page.locator('#historyType').select_option('mate')
        self.assertEqual(self.items().count(), 0)
        self.assertTrue(self.page.locator('#historyEmpty').is_visible())

    def test_older_page_id_still_opens_the_archived_specimen(self):
        for i in range(28):
            self.birth('OldGene' if i == 0 else 'A')
        self.toggle()
        self.page.locator('#historyNext').click()
        link = self.items().last.locator('[data-creature-id="1"]')
        link.focus()
        self.assertIn('OldGene', self.page.locator('#creaturePreview').inner_text())
        self.page.keyboard.press('Enter')
        self.assertIn('生物 #1', self.page.locator('#archiveDetailTitle').inner_text())

    def test_reset_discards_all_events_and_clears_paging(self):
        self.birth('A')
        self.toggle()
        self.page.locator('#historyType').select_option('birth')
        self.page.locator('#clearBtn').click()
        self.assertTrue(self.page.locator('#globalHistory').is_hidden())
        self.assertEqual(self.page.locator('#historyType').input_value(), 'all')
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '0 筆重大事件')
        self.toggle()
        self.assertEqual(self.items().count(), 0)
        self.assertEqual(self.page.evaluate('window.__ecologyTest.history().length'), 0)
        self.page.locator('#demoBtn').click()
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '3 筆重大事件')

    def test_operations_are_not_copied_into_canonical_history_and_no_overflow(self):
        self.birth('A')
        for _ in range(3):
            self.page.locator('#feedText').fill('A')
            self.page.locator('#feedBtn').click()
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '1 筆重大事件')
        self.toggle()
        for width in (320, 390, 768, 1440):
            with self.subTest(width=width):
                self.page.set_viewport_size({'width': width, 'height': 850})
                self.assertLessEqual(
                    self.page.evaluate('document.documentElement.scrollWidth'), width + 1)
                self.assertTrue(self.page.locator('#historyList').is_visible())


if __name__ == '__main__':
    unittest.main()
