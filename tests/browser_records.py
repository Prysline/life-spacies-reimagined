"""v3 phase-one historical creature records / structured life-event contract.

The fixture instruments the in-memory HTML only. Production UI and algorithms
are executed without changes to their real behavior.
"""

import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
from browser_ecology import instrument

HTML = Path(__file__).resolve().parents[1] / 'index.html'


def instrument_records(html):
    scripted = instrument(html)
    anchor = '  snapshot: () => ({'
    if scripted.count(anchor) != 1:
        raise ValueError('Ecology harness was changed; review record fixture')
    return scripted.replace(anchor,
        '  records: () => Array.from(creatureRecords.values()),\n'
        '  history: () => lifeEvents,\n' + anchor, 1)


class V3RecordRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        launch = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            launch.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                          args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**launch)
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
        self.page.evaluate("document.querySelector('#autoFeed').checked = false")
        self.eval('window.__ecologyTest.reset("empty")')
        self.eval('window.__ecologyTest.random(0.5)')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [])
        finally:
            self.context.close()

    def eval(self, expression):
        return self.page.evaluate(expression)

    def records(self):
        return self.eval('window.__ecologyTest.records()')

    def events(self):
        return self.eval('window.__ecologyTest.history()')

    def birth(self, gene, generation=1):
        return self.page.evaluate('([gene, gen]) => window.__ecologyTest.birth(gene,220,230,gen)',
                                  [gene, generation])

    def configure(self, id, **fields):
        self.page.evaluate('([id, f]) => window.__ecologyTest.configure(id,f)',
                           [id, fields])

    def step(self, dt):
        self.page.evaluate('(dt) => window.__ecologyTest.step(dt)', dt)

    def test_manual_birth_creates_gene_and_trait_snapshot(self):
        self.assertEqual(self.birth('A 中b\n1'), 1)
        record, = self.records()
        self.assertEqual(record['gene'], 'Ab1')
        self.assertEqual(record['status'], 'living')
        self.assertEqual(record['origin'], 'manual')
        self.assertEqual(record['generation'], 1)
        self.assertEqual(record['parentIds'], [])
        self.assertIsNone(record['sourceId'])
        self.assertEqual(record['eventIds'], [1])
        event, = self.events()
        self.assertEqual(event['type'], 'birth')
        self.assertEqual(event['creatureIds'], [1])
        self.assertEqual(event['data']['gene'], 'Ab1')
        self.eval('window.__ecologyTest.configure(1, {g: {morph:4}})')
        self.assertEqual(self.records()[0]['traits']['morph'], ord('A') % 5,
                         'Phenotype snapshot must not be a reference to mutable runtime trait')

    def test_death_keeps_gene_last_state_and_event_history(self):
        self.birth('ABCDEF')
        self.configure(1, energy=-2.44)
        self.step(.3)
        self.assertEqual(self.eval('window.__ecologyTest.snapshot().creatures'), [])
        record, = self.records()
        self.assertEqual(record['gene'], 'ABCDEF')
        self.assertEqual(record['status'], 'dead')
        self.assertEqual(record['deathCause'], 'starvation')
        self.assertGreater(record['diedAt'], record['bornAt'])
        self.assertLess(record['lastState']['energy'], -2.45)
        self.assertEqual(record['eventIds'], [1, 2])
        self.assertEqual([e['type'] for e in self.events()], ['birth', 'death'])
        self.step(.3)
        self.assertEqual(len(self.events()), 2, 'Death must not be recorded twice')
        self.assertEqual(len(self.records()), 1, 'Dead records must remain queryable')

    def test_every_meal_is_personal_not_global_ui(self):
        self.birth('Aa')
        self.configure(1, energy=0)
        self.eval('window.__ecologyTest.drop("A",220,230); window.__ecologyTest.drop("a",220,230)')
        self.step(.05)
        self.configure(1, energy=0)
        self.step(.05)
        events = [e for e in self.events() if e['type'] == 'eat']
        self.assertEqual(len(events), 2)
        self.assertEqual({e['data']['character'] for e in events}, {'A','a'})
        for e in events:
            self.assertEqual(e['creatureIds'], [1])
            self.assertGreater(e['data']['energyAfter'], e['data']['energyBefore'])
        self.assertEqual(self.records()[0]['eventIds'], [1, 2, 3])
        self.assertNotIn('吃掉', self.page.locator('#eventLog').inner_text())

    def test_sexual_offspring_has_both_parents_and_shared_mating_event(self):
        a = self.birth('AAAAAA')
        b = self.birth('BBBBBB')
        for id in [a,b]:
            self.configure(id, age=6, energy=1.4, repCD=0)
        self.step(.08)
        records = self.records()
        self.assertEqual(len(records), 3)
        parents, child = records[:2], records[2]
        self.assertEqual(child['gene'], 'AAABBB')
        self.assertEqual(child['generation'], 2)
        self.assertEqual(child['origin'], 'breeding')
        self.assertEqual(child['parentIds'], [1, 2])
        self.assertIsNone(child['sourceId'])
        self.assertEqual(parents[0]['childIds'], [3])
        self.assertEqual(parents[1]['childIds'], [3])
        mates = [e for e in self.events() if e['type']=='mate']
        self.assertEqual(len(mates), 1)
        self.assertEqual(mates[0]['creatureIds'], [1,2,3])
        for rec in records:
            self.assertIn(mates[0]['id'], rec['eventIds'])

    def test_drag_clone_tracks_source_not_sexual_parent(self):
        self.birth('CqMZkyLpRST', generation=2)
        canvas = self.page.locator('#world')
        box = canvas.bounding_box()
        state = self.eval('window.__ecologyTest.snapshot().creatures[0]')
        extent = canvas.evaluate('(el) => ({w:el.width,h:el.height})')
        ratio = self.eval('window.devicePixelRatio')
        x = box['x'] + state['x'] * box['width'] / (extent['w']/ratio)
        y = box['y'] + state['y'] * box['height'] / (extent['h']/ratio)
        self.page.mouse.move(x,y)
        self.page.mouse.down()
        self.page.mouse.move(x+60,y+20,steps=5)
        self.page.mouse.up()
        records = self.records()
        self.assertEqual(len(records), 2)
        source, clone = records
        self.assertEqual(clone['origin'], 'clone')
        self.assertEqual(clone['sourceId'], source['id'])
        self.assertEqual(clone['parentIds'], [])
        self.assertEqual(source['childIds'], [])
        self.assertEqual(clone['gene'], source['gene'])
        self.assertEqual(clone['generation'], 2)
        clone_birth = [e for e in self.events() if e['type']=='birth'][-1]
        self.assertEqual(clone_birth['creatureIds'], [2,1])
        self.assertIn(clone_birth['id'], source['eventIds'])

    def test_full_reset_clears_records_events_and_restarts_ids(self):
        self.birth('A')
        self.configure(1, energy=-2.44)
        self.step(.3)
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(len(self.events()), 2)
        self.eval('window.__ecologyTest.reset("empty")')
        self.assertEqual(self.records(), [])
        self.assertEqual(self.events(), [])
        self.assertEqual(self.eval('window.__ecologyTest.snapshot().born'), 0)
        self.assertEqual(self.birth('B'), 1)
        self.assertEqual(self.events()[0]['id'], 1)
        self.eval('window.__ecologyTest.reset("demo")')
        self.assertEqual(len(self.records()), 3)
        self.assertEqual(len(self.events()), 3)
        self.assertEqual([r['id'] for r in self.records()], [1, 2, 3])
        self.assertEqual([r['origin'] for r in self.records()], ['demo']*3)

    def test_rejected_birth_does_not_create_phantom_records_or_events(self):
        self.assertIsNone(self.birth(''))
        for _ in range(29):
            self.birth('A')
        self.assertEqual(len(self.records()), 28)
        self.assertEqual(len(self.events()), 28)
        self.assertEqual([e['id'] for e in self.events()], list(range(1,29)))
        self.assertEqual(self.eval('window.__ecologyTest.snapshot().born'), 28)


if __name__ == '__main__':
    unittest.main()
