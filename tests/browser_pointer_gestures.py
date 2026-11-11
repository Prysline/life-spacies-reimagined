"""Stage 3C: pointer/touch cancellation and gesture ownership regression."""
import os
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from browser_ecology import instrument

HTML=Path(__file__).resolve().parents[1] / 'index.html'


def fixture(html):
    source=instrument(html)
    anchor='window.__ecologyTest = {'
    if source.count(anchor)!=1:
        raise ValueError('Ecology harness anchor drift')
    extra="""window.__ecologyTest = {
      point: (mode='creature') => {
        const r=canvas.getBoundingClientRect(),c=world[0];
        const x=mode==='creature'?c.x:W*.85,y=mode==='creature'?c.y:H*.7;
        return [r.left+x*r.width/W,r.top+y*r.height/H];
      },
      pointer:()=>drag?{id:drag.pointerId,travel:drag.travel,creature:drag.c?.id??null}:null,
      dragging:()=>world.map(c=>Boolean(c.dragging)),
    """
    return source.replace(anchor,extra,1)


class PointerGestureBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        kwargs={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            kwargs.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],
                          args=['--no-sandbox','--disable-gpu'])
        cls.browser=cls.pw.chromium.launch(**kwargs)
        cls.source=fixture(HTML.read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.ctx=self.browser.new_context(viewport={'width':390,'height':844},has_touch=True)
        self.page=self.ctx.new_page()
        self.errors=[]
        self.page.on('pageerror',lambda err:self.errors.append(str(err)))
        self.page.set_content(self.source,wait_until='load')
        self.page.evaluate('window.__ecologyTest.reset("empty")')
        self.page.evaluate('document.querySelector("#autoFeed").checked=false')
        self.page.evaluate('window.__ecologyTest.random(.5)')
        self.page.evaluate('window.__ecologyTest.birth("Abcd",220,230)')

    def tearDown(self):
        try:self.assertEqual(self.errors,[])
        finally:self.ctx.close()

    def snap(self):return self.page.evaluate('window.__ecologyTest.snapshot()')
    def point(self,mode='creature'):
        return self.page.evaluate('(m)=>window.__ecologyTest.point(m)',mode)
    def state(self):return self.page.evaluate('window.__ecologyTest.pointer()')
    def drag_begin(self,mode='creature'):
        x,y=self.point(mode)
        self.page.mouse.move(x,y)
        self.page.mouse.down()
        return x,y

    def test_touch_tap_creature_selects_without_cloning(self):
        x,y=self.point()
        self.page.touchscreen.tap(x,y)
        s=self.snap()
        self.assertEqual(s['born'],1)
        self.assertEqual(s['selected'],1)
        self.assertEqual(self.state(),None)
        self.assertEqual(self.page.evaluate('window.__ecologyTest.dragging()'),[False])

    def test_touch_tap_empty_only_drops_one_letter(self):
        self.page.evaluate('document.getElementById("feedText").value="A"')
        x,y=self.point('empty')
        self.page.touchscreen.tap(x,y)
        s=self.snap()
        self.assertEqual(s['born'],1)
        self.assertEqual(len(s['foods']),1)
        self.assertEqual(s['foods'][0]['ch'],'A')
        self.assertIsNone(self.state())

    def test_cancelled_drag_restores_position_without_clone(self):
        initial=self.snap()['creatures'][0]
        x,y=self.drag_begin()
        self.page.mouse.move(x+65,y+22,steps=5)
        state=self.state()
        self.assertGreater(state['travel'],20)
        self.page.evaluate('''() => {
          const id=window.__ecologyTest.pointer().id;
          document.querySelector('#world').dispatchEvent(
            new PointerEvent('pointercancel',{bubbles:true,pointerId:id,pointerType:'mouse'}));
        }''')
        after=self.snap()
        self.assertEqual(after['born'],1)
        self.assertAlmostEqual(after['creatures'][0]['x'],initial['x'])
        self.assertAlmostEqual(after['creatures'][0]['y'],initial['y'])
        self.assertEqual(self.page.evaluate('window.__ecologyTest.dragging()'),[False])
        self.page.mouse.up()
        self.assertEqual(self.snap()['born'],1)

    def test_cancelled_empty_tap_does_not_feed(self):
        self.page.evaluate('document.getElementById("feedText").value="F"')
        self.drag_begin('empty')
        self.page.evaluate('''() => {
          const id=window.__ecologyTest.pointer().id;
          document.querySelector('#world').dispatchEvent(
            new PointerEvent('pointercancel',{bubbles:true,pointerId:id,pointerType:'mouse'}));
        }''')
        self.page.mouse.up()
        self.assertEqual(len(self.snap()['foods']),0)

    def test_second_touch_cancels_first_gesture_without_clone(self):
        initial=self.snap()['creatures'][0]
        x,y=self.drag_begin()
        self.page.mouse.move(x+65,y+12,steps=4)
        self.page.evaluate('''() => document.querySelector('#world').dispatchEvent(
          new PointerEvent('pointerdown',{bubbles:true,pointerId:999,pointerType:'touch',
            isPrimary:false,button:0,clientX:25,clientY:25}))''')
        self.assertIsNone(self.state())
        self.page.mouse.up()
        s=self.snap()
        self.assertEqual(s['born'],1)
        self.assertEqual(s['foods'],[])
        self.assertAlmostEqual(s['creatures'][0]['x'],initial['x'])

    def test_unrelated_pointer_move_and_up_do_not_finish_drag(self):
        x,y=self.drag_begin()
        own=self.state()['id']
        self.page.evaluate('''() => {
          const c=document.querySelector('#world');
          c.dispatchEvent(new PointerEvent('pointermove',{bubbles:true,pointerId:765,
            pointerType:'touch',clientX:350,clientY:500}));
          c.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:765,
            pointerType:'touch'}));
        }''')
        self.assertEqual(self.state()['id'],own)
        self.assertEqual(self.state()['travel'],0)
        self.page.mouse.up()
        self.assertEqual(self.snap()['born'],1)

    def test_right_click_empty_does_not_feed(self):
        self.page.evaluate('document.getElementById("feedText").value="Q"')
        x,y=self.point('empty')
        self.page.mouse.click(x,y,button='right')
        self.assertEqual(self.snap()['foods'],[])

    def test_completed_mouse_drag_still_clones_once(self):
        x,y=self.drag_begin()
        self.page.mouse.move(x+55,y+20,steps=5)
        self.page.mouse.up()
        s=self.snap()
        self.assertEqual(s['born'],2)
        self.assertEqual(len(s['creatures']),2)
        self.assertEqual([c['text'] for c in s['creatures']],['Abcd','Abcd'])
        self.assertIsNone(self.state())

    def test_blur_cancels_pending_drag(self):
        initial=self.snap()['creatures'][0]
        x,y=self.drag_begin()
        self.page.mouse.move(x+40,y+10,steps=4)
        self.page.evaluate('window.dispatchEvent(new Event("blur"))')
        self.page.mouse.up()
        self.assertEqual(self.snap()['born'],1)
        self.assertAlmostEqual(self.snap()['creatures'][0]['x'],initial['x'])
        self.assertFalse(any(self.page.evaluate('window.__ecologyTest.dragging()')))


if __name__=='__main__':
    unittest.main()
