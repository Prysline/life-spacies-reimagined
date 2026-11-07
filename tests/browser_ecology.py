"""Deterministic v2 ecology behavior regression tests.

The browser executes the actual index.html simulation code. For these tests only,
we disable the animation scheduler and expose a narrow fixture interface within
an in-memory copy of that script. Real update(), breed(), crossover(), birth(),
and pointer handlers remain unchanged. Production HTML is never rewritten.
"""

import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / "index.html"
START = "(()=>{'use strict';"
END = "window.addEventListener('resize',resize);resize();reset('demo');"

# Only test-time instrumentation: expose real closure state and functions;
# no simulation formulas or event handlers are replaced.
HARNESS = r"""
window.__ecologyTest = {
  reset: (mode='empty') => reset(mode),
  birth: (text, x=220, y=230, generation=1) => birth(text, x, y, generation)?.id ?? null,
  drop: (ch, x, y) => dropChar(ch, x, y),
  step: dt => update(dt),
  random: value => { Math.random = () => value; },
  configure: (id, values) => { const c=world.find(c=>c.id===id); if(!c) throw Error('Unknown creature'); Object.assign(c,values); },
  foodAge: age => { if (!foods.length) throw Error('No food'); foods[0].age=age; return foods[0].life; },
  snapshot: () => ({
    creatures: world.map(c => ({id:c.id, text:c.text, gen:c.gen, age:c.age,
      energy:c.energy, repCD:c.repCD, size:c.size, gsize:c.g.size,
      speed:c.g.speed, life:c.life, x:c.x, y:c.y})),
    foods: foods.map(f => ({ch:f.ch, age:f.age, life:f.life, x:f.x, y:f.y})),
    selected, born:totalBorn, simTime,
    events:Array.from(document.querySelectorAll('#eventLog > div')).map(el => el.innerText)
  })
};
"""


def instrument(html):
    if html.count(START) != 1 or html.count(END) != 1:
        raise ValueError('v2 simulation anchors changed; update test fixture consciously')
    return html.replace(START, START + 'window.requestAnimationFrame = () => 0;', 1).replace(
        END, HARNESS + END, 1
    )


class V2EcologyRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        launch = {'headless': True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            launch.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                          args=['--no-sandbox', '--disable-gpu'])
        cls.browser = cls.playwright.chromium.launch(**launch)
        cls.fixture_html = instrument(HTML.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1360, 'height': 900})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.set_content(self.fixture_html, wait_until='load')
        self.page.evaluate("document.querySelector('#autoFeed').checked = false")
        self.eval('window.__ecologyTest.reset("empty")')
        self.eval('window.__ecologyTest.random(0.5)')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [], 'Unexpected JavaScript page error')
        finally:
            self.context.close()

    def eval(self, expression):
        return self.page.evaluate(expression)

    def snapshot(self):
        return self.eval('window.__ecologyTest.snapshot()')

    def birth(self, gene, x=220, y=230, generation=1):
        return self.page.evaluate('([g, x, y, gen]) => window.__ecologyTest.birth(g, x, y, gen)',
                                  [gene, x, y, generation])

    def set_creature(self, id, **values):
        self.page.evaluate('([id, values]) => window.__ecologyTest.configure(id, values)',
                           [id, values])

    def step(self, dt):
        self.page.evaluate('(dt) => window.__ecologyTest.step(dt)', dt)

    def test_case_sensitive_food_selection_and_energy_gain(self):
        a = self.birth('A')
        c = self.snapshot()['creatures'][0]
        self.set_creature(a, energy=0)
        self.page.evaluate('([x, y]) => {window.__ecologyTest.drop("a", x, y); window.__ecologyTest.drop("A", x, y);}',
                           [c['x'], c['y']])
        self.step(0.05)
        state = self.snapshot()
        self.assertEqual([f['ch'] for f in state['foods']], ['a'], 'Only matching uppercase A should be eaten')
        self.assertGreater(state['creatures'][0]['energy'], .85)
        self.assertGreater(state['creatures'][0]['size'], c['size'])
        self.set_creature(a, energy=0)
        self.step(0.05)
        self.assertEqual([f['ch'] for f in self.snapshot()['foods']], ['a'], 'Lowercase a must remain inedible to A')
        b = self.birth('a', 230, 232)
        self.set_creature(b, energy=0)
        self.step(0.05)
        self.assertEqual(self.snapshot()['foods'], [], 'A lowercase genotype should consume lowercase a')

    def test_movement_cost_decreases_energy_and_expired_food_disappears(self):
        self.birth('A')
        first = self.snapshot()['creatures'][0]
        self.step(0.5)
        later = self.snapshot()['creatures'][0]
        expected = first['energy'] - (.07 + first['speed'] * .0008) * .5
        self.assertAlmostEqual(later['energy'], expected, places=5)
        self.assertGreater(later['age'], first['age'])
        self.eval('window.__ecologyTest.drop("Z", 220, 230)')
        self.eval('window.__ecologyTest.foodAge(window.__ecologyTest.snapshot().foods[0].life - 0.01)')
        self.step(0.02)
        self.assertEqual(self.snapshot()['foods'], [], 'Old food should expire without being eaten')

    def test_hunger_death_clears_selected_creature(self):
        self.page.locator('#geneText').fill('A')
        self.page.locator('#createBtn').click()
        state = self.snapshot()
        self.assertEqual(state['selected'], 1)
        self.set_creature(1, energy=-2.44)
        self.step(.3)
        state = self.snapshot()
        self.assertEqual(state['creatures'], [])
        self.assertIsNone(state['selected'])
        self.assertTrue(any('飢餓死亡' in e for e in state['events']))
        self.assertEqual(self.page.locator('#living').inner_text(), '0')
        self.assertTrue(self.page.locator('#tabSelected').is_disabled())

    def test_lifespan_death_is_distinguished_from_hunger(self):
        id = self.birth('A')
        self.set_creature(id, age=135, energy=1)
        self.step(.3)
        state = self.snapshot()
        self.assertEqual(state['creatures'], [])
        self.assertTrue(any('壽命結束' in e for e in state['events']))
        self.assertFalse(any('飢餓死亡' in e for e in state['events']))

    def test_mating_uses_real_crossover_and_cooldown(self):
        a = self.birth('AAAAAA', 220, 230)
        b = self.birth('BBBBBB', 229, 234)
        for id in (a, b):
            self.set_creature(id, age=6, repCD=0, energy=1.4)
        self.step(.08)
        state = self.snapshot()
        self.assertEqual(len(state['creatures']), 3)
        self.assertEqual(state['born'], 3)
        self.assertEqual(state['creatures'][2]['text'], 'AAABBB')
        self.assertEqual(state['creatures'][2]['gen'], 2)
        self.assertGreater(state['creatures'][0]['repCD'], 10)
        self.assertGreater(state['creatures'][1]['repCD'], 10)
        self.assertTrue(any('交配' in e for e in state['events']))
        self.step(.08)
        self.assertEqual(len(self.snapshot()['creatures']), 3, 'Cooldown prevents immediate repeated mating')

    def test_mutation_branch_changes_inherited_gene(self):
        self.eval('window.__ecologyTest.random(0)')
        a = self.birth('ZZZZ', 220, 230)
        b = self.birth('YYYY', 228, 230)
        for id in (a, b):
            self.set_creature(id, age=6, repCD=0, energy=1.4)
        self.step(.08)
        state = self.snapshot()
        self.assertEqual(len(state['creatures']), 3)
        self.assertEqual(state['creatures'][2]['text'], 'AYYY',
                         'With random=0 the first character of ZYYY mutates to A')
        self.assertEqual(state['creatures'][2]['gen'], 2)

    def test_ineligible_mates_cannot_reproduce(self):
        a = self.birth('AAAA', 220, 230)
        b = self.birth('BBBB', 229, 234)
        self.set_creature(a, age=4, energy=1.4, repCD=0)
        self.set_creature(b, age=6, energy=1.4, repCD=0)
        self.step(.08)
        self.assertEqual(self.snapshot()['born'], 2, 'Young mates should be rejected')
        self.set_creature(a, age=6, energy=1.4, repCD=4)
        self.step(.08)
        self.assertEqual(self.snapshot()['born'], 2, 'Cooldown should prevent mating')
        self.set_creature(a, repCD=0, energy=-.01)
        self.step(.08)
        self.assertEqual(self.snapshot()['born'], 2, 'Low-energy mates should be rejected')

    def test_actual_canvas_pointer_drag_clones_without_modifying_parent_gene(self):
        original_gene = 'CqMZkyLpRST'
        id = self.birth(original_gene, 220, 230, 2)
        original = self.snapshot()['creatures'][0]
        box = self.page.locator('#world').bounding_box()
        self.assertIsNotNone(box)
        # canvas CSS coordinates equal simulation coordinates at the default desktop viewport
        canvas = self.page.locator('#world')
        extent = canvas.evaluate('(el) => ({width:el.width, height:el.height})')
        ratio = self.page.evaluate("() => window.devicePixelRatio")
        css_x = original['x'] * box['width'] / (extent['width'] / ratio)
        css_y = original['y'] * box['height'] / (extent['height'] / ratio)
        x, y = box['x'] + css_x, box['y'] + css_y
        self.page.mouse.click(x, y)
        self.assertEqual(self.snapshot()['born'], 1, 'Simple selection must not clone')
        self.page.mouse.move(x, y)
        self.page.mouse.down()
        self.page.mouse.move(x + 65, y + 18, steps=6)
        self.page.mouse.up()
        state = self.snapshot()
        self.assertEqual(state['born'], 2)
        self.assertEqual(len(state['creatures']), 2)
        self.assertEqual([c['text'] for c in state['creatures']], [original_gene, original_gene])
        self.assertEqual([c['gen'] for c in state['creatures']], [2, 2])
        self.assertTrue(any('複製出' in e for e in state['events']))


if __name__ == '__main__':
    unittest.main()
