"""Clear active letter food while preserving organisms, events and experiment identity."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / 'index.html'


def fixture(html):
    start = "(()=>{'use strict';"
    hook = "window.addEventListener('resize',resize);resize();reset('demo');"
    if html.count(start) != 1 or html.count(hook) != 1:
        raise ValueError('Simulation fixture anchor changed')
    return (html.replace(start, start + 'window.requestAnimationFrame=()=>0;', 1)
                .replace(hook, """window.__foodTest={
      snapshot:()=>({time:simTime,autoClock,
        creatures:world.map(c=>({id:c.id,gene:c.text,gen:c.gen,energy:c.energy,age:c.age})),
        foods:foods.map(f=>f.ch),born:totalBorn,selected,
        records:Array.from(creatureRecords.values()),events:lifeEvents.map(e=>({...e})),
        auto:document.getElementById('autoFeed').checked}),
      reset:(mode='empty')=>reset(mode),
      birth:gene=>birth(gene,220,230)?.id??null,
      step:dt=>update(dt),
      setEnergy:(id,energy)=>{const c=world.find(c=>c.id===id);if(c)c.energy=energy;}
    };""" + hook, 1))


class ClearFoodBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        args = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            args.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                        args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**args)
        cls.fixture = fixture(HTML.read_text(encoding='utf8'))

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
        self.page.evaluate('window.__foodTest.reset("empty")')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Unexpected JavaScript errors')
        finally:
            self.context.close()

    def js(self, expression):
        return self.page.evaluate(expression)

    def snap(self):
        return self.js('window.__foodTest.snapshot()')

    def test_clears_only_food_and_keeps_exact_experiment_records(self):
        self.js('window.__foodTest.birth("Aa")')
        self.page.locator('#feedText').fill('Feed text still here')
        self.page.locator('#feedBtn').click()
        self.assertGreater(int(self.page.locator('#foodCount').inner_text()), 0)
        before = self.snap()
        self.page.locator('#clearFoodBtn').click()
        after = self.snap()
        self.assertEqual(after['foods'], [])
        self.assertEqual(self.page.locator('#foodCount').inner_text(), '0')
        for field in ['time','autoClock','creatures','born','selected','records','events','auto']:
            self.assertEqual(after[field], before[field], field)
        self.assertEqual(self.page.locator('#feedText').input_value(), 'Feed text still here')
        self.assertEqual(self.page.locator('#living').inner_text(), '1')
        self.assertEqual(self.page.locator('#births').inner_text(), '1')
        self.assertIn('已清空', self.page.locator('#eventLog > div').first.inner_text())
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '1 筆重大事件')

    def test_keeps_auto_feed_enabled_and_later_refills(self):
        self.js('window.__foodTest.birth("AAAA")')
        self.page.locator('#feedBtn').click()
        self.assertTrue(self.page.locator('#autoFeed').is_checked())
        self.page.locator('#clearFoodBtn').click()
        self.assertTrue(self.page.locator('#autoFeed').is_checked())
        self.assertIn('稍後可能再次出現',
                      self.page.locator('#eventLog > div').first.inner_text())
        self.js('window.__foodTest.step(2.8)')
        self.assertGreater(len(self.snap()['foods']), 0)
        self.assertEqual(self.page.locator('#living').inner_text(), '1')

    def test_disabled_auto_feed_stays_disabled(self):
        self.js('window.__foodTest.birth("AAAA")')
        self.page.locator('#autoFeed').uncheck()
        self.page.locator('#feedBtn').click()
        self.page.locator('#clearFoodBtn').click()
        self.assertFalse(self.page.locator('#autoFeed').is_checked())
        self.assertNotIn('自動投餵仍開啟',
                         self.page.locator('#eventLog > div').first.inner_text())
        self.js('window.__foodTest.step(3.2)')
        self.assertEqual(self.snap()['foods'], [])
        self.assertEqual(self.page.locator('#foodCount').inner_text(), '0')

    def test_no_food_is_safe_and_no_false_history_event(self):
        self.js('window.__foodTest.birth("A")')
        before = self.snap()
        self.page.locator('#clearFoodBtn').click()
        self.page.locator('#clearFoodBtn').click()
        self.assertEqual(self.snap(), before)
        self.assertIn('沒有字母飼料',
                      self.page.locator('#eventLog > div').first.inner_text())
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '1 筆重大事件')

    def test_preserves_dead_creature_ancestry_and_history(self):
        self.js('window.__foodTest.birth("Deceased")')
        self.js('window.__foodTest.setEnergy(1,-2.44)')
        self.js('window.__foodTest.step(.3)')
        self.assertEqual(len(self.snap()['creatures']), 0)
        self.page.locator('#feedText').fill('ABCD')
        self.page.locator('#feedBtn').click()
        before = self.snap()
        self.page.locator('#clearFoodBtn').click()
        after = self.snap()
        for key in ['records','events','born','time']:
            self.assertEqual(before[key], after[key], key)
        self.page.locator('#archiveFilter').select_option('dead')
        self.assertIn('#1 ·', self.page.locator('#archiveList').inner_text())
        self.assertEqual(self.page.locator('#historyTotal').inner_text(), '2 筆重大事件')

    def test_full_reset_is_still_distinct_and_clears_all(self):
        self.js('window.__foodTest.birth("A")')
        self.page.locator('#feedBtn').click()
        self.page.locator('#clearFoodBtn').click()
        self.assertEqual(len(self.snap()['records']), 1)
        self.page.locator('#clearBtn').click()
        state = self.snap()
        for key in ['creatures','foods','records','events']:
            self.assertEqual(state[key], [], key)
        self.assertEqual(state['born'], 0)
        self.assertEqual(state['time'], 0)

    def test_clear_food_button_is_separate_and_mobile_safe(self):
        button = self.page.locator('#clearFoodBtn')
        full_reset = self.page.locator('#clearBtn')
        self.assertEqual(button.inner_text(), '清空所有飼料（保留生物）')
        self.assertIn('完全清空', full_reset.inner_text())
        for width, height in [(320,720),(390,844),(768,1024),(1440,900)]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width,'height':height})
                self.assertTrue(button.is_visible())
                self.assertLessEqual(self.js('document.documentElement.scrollWidth'), width+1)


if __name__ == '__main__':
    unittest.main()
