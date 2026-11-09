"""A specimen portrait reuses the real drawing code; behavior reuses actual targeting."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / 'index.html'


def fixture(html):
    head = "(()=>{'use strict';"
    tail = "window.addEventListener('resize',resize);resize();reset('demo');"
    assert html.count(head) == 1 and html.count(tail) == 1
    instrumentation = """window.__statusTest={
       birth:(g)=>birth(g,220,230)?.id??null,
       reset:(mode='empty')=>reset(mode),
       step:(dt)=>update(dt),
       set:(id,fields)=>Object.assign(world.find(c=>c.id===id),fields),
       drop:(ch,x,y)=>dropChar(ch,x,y),
       snapshot:()=>({creatures:world.map(c=>({id:c.id,text:c.text,age:c.age,energy:c.energy,repCD:c.repCD,x:c.x,y:c.y})),
         records:[...creatureRecords.values()],events:lifeEvents.map(e=>({...e})),foods:foods.map(f=>f.ch),time:simTime}),
       drawState:()=>({target:targetFor(world.find(c=>c.id===1)),paused}),
     };"""
    return (html.replace(head, head+'window.requestAnimationFrame=()=>0;', 1)
                .replace(tail, instrumentation + tail, 1))


class StatusPreviewBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        args={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            args.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox','--disable-gpu'])
        cls.browser=cls.playwright.chromium.launch(**args)
        cls.html=fixture(HTML.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop()

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':1360,'height':900})
        self.page=self.context.new_page()
        self.errors=[]
        self.page.on('pageerror', lambda error:self.errors.append(str(error)))
        self.page.set_content(self.html,wait_until='load')
        self.page.locator('#autoFeed').uncheck()
        self.page.evaluate('window.__statusTest.reset("empty")')

    def tearDown(self):
        try:self.assertEqual(self.errors, [])
        finally:self.context.close()

    def eval(self, code):return self.page.evaluate(code)
    def birth(self,g):return self.page.evaluate('g=>window.__statusTest.birth(g)',g)
    def snapshot(self):return self.eval('window.__statusTest.snapshot()')
    def open(self,id):
        self.page.locator('#archiveFilter').select_option('all')
        self.page.locator(f'#archiveList [data-open-creature="{id}"]').click()

    def behavior(self):return self.page.locator('#archiveBehaviorText').inner_text()
    def canvas(self):return self.page.locator('#archiveSpecimenCanvas')
    def pixels(self):return self.canvas().evaluate('(c)=>c.toDataURL()')

    def test_living_specimen_has_actual_drawing_with_accessible_label(self):
        self.birth('AqMZkyLpRST')
        self.open(1)
        c=self.canvas()
        self.assertTrue(c.is_visible())
        self.assertIn('生物 #1',c.get_attribute('aria-label'))
        self.assertGreater(c.evaluate('(el)=>el.width'),200)
        self.assertGreater(c.evaluate('(el)=>el.height'),200)
        self.assertGreater(len(self.pixels()),1500)
        self.assertIn('使用目前個體的基因性狀',self.page.locator('.archive-specimen figcaption').inner_text())
        self.assertIn('自由游動',self.behavior())
        self.assertEqual(self.page.locator('[data-state-key="生存狀態"]').inner_text(),'存活')

    def test_different_genome_has_different_portrait_and_switch_back(self):
        self.birth('AqMZkyLpRST')
        self.birth('CzWQrsHpTUV')
        self.open(1)
        first=self.pixels()
        self.open(2)
        self.assertNotEqual(first,self.pixels())
        self.open(1)
        self.assertEqual(first,self.pixels())
        self.page.locator('[data-archive-tab="gene"]').click()
        self.assertEqual(self.page.locator('#archiveSpecimenCanvas').count(),0)
        self.page.locator('[data-archive-tab="status"]').click()
        self.assertEqual(first,self.pixels())

    def test_hunting_label_matches_actual_case_sensitive_target(self):
        self.birth('Aa')
        self.eval('window.__statusTest.set(1,{energy:0})')
        self.eval('window.__statusTest.drop("a",220,230);window.__statusTest.drop("X",220,230)')
        self.open(1)
        self.assertEqual(self.behavior(),'正接近食物「a」')
        self.assertEqual(self.eval('window.__statusTest.drawState().target.type'),'food')
        self.page.locator('#clearFoodBtn').click()
        self.assertIn('自由游動',self.behavior())

    def test_mate_label_matches_actual_selected_mate(self):
        self.birth('AAAAAA')
        self.birth('BBBBBB')
        self.eval('window.__statusTest.set(1,{energy:1.4,age:6,repCD:0});window.__statusTest.set(2,{energy:1.4,age:6,repCD:0})')
        self.open(1)
        self.assertEqual(self.behavior(),'正接近生物 #2（交配對象）')
        self.assertEqual(self.eval('window.__statusTest.drawState().target.type'),'mate')

    def test_pause_and_drag_are_not_misreported_as_wandering(self):
        self.birth('ABCDEF')
        self.open(1)
        self.page.locator('#pauseBtn').click()
        self.assertEqual(self.behavior(),'模擬已暫停')
        self.page.locator('#pauseBtn').click()
        self.assertIn('自由游動',self.behavior())
        self.eval('window.__statusTest.set(1,{dragging:true})')
        self.eval('window.__statusTest.step(.3)')
        self.assertIn('正被拖曳',self.behavior())

    def test_dead_specimen_is_static_no_fabricated_current_behavior(self):
        self.birth('DeathGene')
        self.eval('window.__statusTest.set(1,{energy:-2.44})')
        self.eval('window.__statusTest.step(.3)')
        self.open(1)
        self.assertIn('已死亡',self.behavior())
        self.assertEqual(self.page.locator('[data-state-key="生存狀態"]').inner_text(),'飢餓死亡')
        self.assertTrue(self.canvas().is_visible())
        self.assertIn('並非死亡瞬間截圖',self.page.locator('.archive-specimen figcaption').inner_text())
        self.assertIn('死亡時大小',self.page.locator('#archiveTabBody').inner_text())
        before=self.pixels()
        self.eval('window.__statusTest.step(2)')
        self.assertEqual(before,self.pixels())
        self.assertEqual(self.snapshot()['records'][0]['status'],'dead')

    def test_viewing_does_not_change_creatures_or_life_events(self):
        self.birth('AAAAAA')
        self.birth('BBBBBB')
        before=self.snapshot()
        self.open(1)
        self.page.locator('[data-archive-tab="gene"]').click()
        self.page.locator('[data-archive-tab="status"]').click()
        self.open(2)
        after=self.snapshot()
        self.assertEqual(before,after)

    def test_reset_and_mobile_widths(self):
        self.birth('AqMZkyLpRST')
        self.open(1)
        for width in [320,390,768,1440]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width,'height':844})
                if width <= 767 and not self.canvas().is_visible():
                    self.page.locator('#archiveList [data-open-creature="1"]').click()
                self.assertTrue(self.canvas().is_visible())
                self.assertLessEqual(self.eval('document.documentElement.scrollWidth'),width+1)
        self.page.locator('#clearBtn').click()
        self.assertEqual(self.page.locator('#archiveSpecimenCanvas').count(),0)
        self.assertEqual(self.page.locator('#archiveBehaviorText').count(),0)

if __name__=='__main__':unittest.main()
