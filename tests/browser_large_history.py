"""3C: bounded archive DOM and canonical high-volume event history regression."""
import os
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / 'index.html'
START = "(()=>{'use strict';"
END = "window.addEventListener('resize',resize);resize();reset('demo');"
HARNESS = r"""
window.__loadTest={
 seed:(n=1400,meals=7000)=>{
  reset('empty');
  const start=performance.now();
  const push=(type,id,data)=>{
   const e={id:nextEventId++,time:simTime,type,creatureIds:[id],data};
   lifeEvents.push(e);creatureRecords.get(id).eventIds.push(e.id);
  };
  for(let i=1;i<=n;i++){
   const gene=(i===1?'A_OLD_EARLY_':i===n?'Z_LAST_REC_':'A_GENERIC_')+i;
   const traits=decode(gene).g;
   creatureRecords.set(i,{id:i,gene,traits:{...traits},generation:i%4+1,
    origin:'manual',parentIds:[],sourceId:null,childIds:[],bornAt:i,diedAt:i+1,
    deathCause:'age',status:'dead',lastState:{age:1,energy:0,size:traits.size,x:220,y:200,repCD:0},eventIds:[]});
   push('birth',i,{childId:i,origin:'manual',parentIds:[],sourceId:null,gene,generation:i%4+1});
   push('death',i,{cause:'age',age:1,energy:0});
  }
  for(let j=0;j<meals;j++){
   const i=1+j%n;
   push('eat',i,{ch:'A',energyBefore:0,energyAfter:1});
  }
  majorEventCount=2*n;
  nextId=n+1;totalBorn=n;
  archiveDirty=true;
  $('archiveFilter').value='dead';
  refreshGlobalHistory();sync();
  return {timeMs:performance.now()-start,records:creatureRecords.size,events:lifeEvents.length};
 },
 addMeal:(id)=>{recordLifeEvent('eat',[id],{ch:'A',energyBefore:0,energyAfter:1});sync();},
 info:()=>({records:creatureRecords.size,events:lifeEvents.length,selected:archiveSelectedId,
  limit:archiveVisibleLimit,archiveDirty,historyCount:majorEventCount}),
 reset:()=>reset('empty')
};
"""


def fixture(html):
    if html.count(START)!=1 or html.count(END)!=1:
        raise ValueError('Fixture insertion anchor drift')
    return html.replace(START,START+'window.requestAnimationFrame=()=>0;',1).replace(END,HARNESS+END,1)


class LargeHistoryBrowserRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        opts={'headless':True}
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            opts.update(executable_path=os.environ['CHROMIUM_EXECUTABLE'],args=['--no-sandbox','--disable-gpu'])
        cls.browser=cls.pw.chromium.launch(**opts)
        cls.html=fixture(HTML.read_text(encoding='utf8'))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop()

    def setUp(self):
        self.ctx=self.browser.new_context(viewport={'width':1440,'height':900})
        self.page=self.ctx.new_page()
        self.errors=[]
        self.page.on('pageerror',lambda err:self.errors.append(str(err)))
        self.page.set_content(self.html,wait_until='load')
        self.seed=self.page.evaluate('window.__loadTest.seed(1400,7000)')

    def tearDown(self):
        try:self.assertEqual(self.errors,[])
        finally:self.ctx.close()

    def record_count(self):return self.page.locator('#archiveList [data-open-creature]').count()
    def info(self):return self.page.evaluate('window.__loadTest.info()')

    def test_large_record_load_has_bounded_archive_dom(self):
        self.assertEqual((self.seed['records'],self.seed['events']),(1400,9800))
        self.assertEqual(self.record_count(),100)
        self.assertIn('1400 / 1400',self.page.locator('#archiveCount').inner_text())
        self.assertTrue(self.page.locator('#archiveMore').is_visible())
        self.assertLess(self.seed['timeMs'],15000)
        self.assertEqual(self.info()['historyCount'],2800)

    def test_load_more_keeps_total_count_and_has_keyboard_focus(self):
        self.page.locator('#archiveMore').click()
        self.assertEqual(self.record_count(),200)
        self.assertEqual(self.page.evaluate('document.activeElement.dataset.openCreature'),'1300')
        self.page.locator('#archiveMore').click()
        self.assertEqual(self.record_count(),300)
        self.assertEqual(self.info()['limit'],300)
        self.assertIn('1400 / 1400',self.page.locator('#archiveCount').inner_text())

    def test_search_all_records_not_only_displayed_batch(self):
        self.page.locator('#archiveSearch').fill('#1')
        self.assertEqual(self.record_count(),1)
        self.assertIn('1 / 1400',self.page.locator('#archiveCount').inner_text())
        self.assertIn('A_OLD_EARLY_1',self.page.locator('#archiveList').inner_text())
        self.page.locator('#archiveList [data-open-creature="1"]').click()
        self.assertIn('生物 #1',self.page.locator('#archiveDetailTitle').inner_text())
        self.page.locator('[data-archive-tab="gene"]').click()
        self.assertIn('A_OLD_EARLY_1',self.page.locator('#archiveTabBody').inner_text())

    def test_sort_and_filter_reset_batch_and_support_old_records(self):
        self.page.locator('#archiveMore').click()
        self.page.locator('#archiveSort').select_option('id-asc')
        self.assertEqual(self.record_count(),100)
        self.assertEqual(self.page.locator('#archiveList [data-open-creature]').first.get_attribute('data-open-creature'),'1')
        self.page.locator('#archiveFilter').select_option('living')
        self.assertEqual(self.record_count(),0)
        self.assertIn('0 / 1400',self.page.locator('#archiveCount').inner_text())
        self.page.locator('#archiveFilter').select_option('all')
        self.assertEqual(self.record_count(),100)
        self.assertEqual(self.info()['limit'],100)

    def test_many_meals_do_not_rebuild_unrelated_archive(self):
        result=self.page.evaluate('''() => {
          const first=document.querySelector('#archiveList [data-open-creature]');
          window.__loadTest.addMeal(1);
          return first===document.querySelector('#archiveList [data-open-creature]');
        }''')
        self.assertTrue(result)
        self.assertEqual(self.record_count(),100)
        self.assertEqual(self.info()['events'],9801)
        self.page.locator('#archiveSort').select_option('energy')
        first=self.page.locator('#archiveList [data-open-creature]').first.element_handle()
        self.page.evaluate('window.__loadTest.addMeal(1)')
        self.assertNotEqual(first,self.page.locator('#archiveList [data-open-creature]').first.element_handle())

    def test_selected_life_record_updates_without_losing_full_history(self):
        self.page.locator('#archiveSearch').fill('#1')
        self.page.locator('#archiveList [data-open-creature="1"]').click()
        self.page.locator('[data-archive-tab="life"]').click()
        self.assertIn('7 筆',self.page.locator('#archiveTabBody').inner_text())
        before=self.page.locator('#archiveTabBody').inner_text()
        self.page.evaluate('window.__loadTest.addMeal(1)')
        after=self.page.locator('#archiveTabBody').inner_text()
        self.assertNotEqual(before,after)
        self.assertEqual(self.info()['events'],9801)
        self.assertEqual(self.record_count(),1)

    def test_global_history_is_25_per_page_and_filters_meals(self):
        self.assertEqual(self.page.locator('#historyTotal').inner_text(),'2800 筆重大事件')
        self.page.locator('#historyToggle').click()
        self.assertEqual(self.page.locator('#historyList li').count(),25)
        self.assertIn('第 1 / 112 頁',self.page.locator('#historyPage').inner_text())
        self.page.locator('#historyType').select_option('birth')
        self.assertEqual(self.page.locator('#historyList li').count(),25)
        self.assertIn('第 1 / 56 頁',self.page.locator('#historyPage').inner_text())
        self.page.locator('#historyNext').click()
        self.assertIn('第 2 / 56 頁',self.page.locator('#historyPage').inner_text())
        self.assertTrue(self.page.locator('#historyList').evaluate('(e)=>e.scrollHeight>e.clientHeight'))
        self.page.locator('#historyList').evaluate('(e)=>e.scrollTop=e.scrollHeight')
        self.assertGreater(self.page.locator('#historyList').evaluate('(e)=>e.scrollTop'),0)

    def test_stress_scrolling_archive_history_and_reset(self):
        for width in [320,390,768,1024,1440]:
            with self.subTest(width=width):
                self.page.set_viewport_size({'width':width,'height':820})
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width+1)
                self.assertEqual(self.record_count(),100)
                self.assertTrue(self.page.locator('#archiveList').evaluate('(e)=>e.scrollHeight>e.clientHeight'))
                self.page.locator('#archiveList').evaluate('(e)=>e.scrollTop=e.scrollHeight')
                self.assertGreater(self.page.locator('#archiveList').evaluate('(e)=>e.scrollTop'),0)
        self.page.evaluate('window.__loadTest.reset()')
        self.assertEqual(self.record_count(),0)
        self.assertEqual(self.page.locator('#archiveMore').count(),0)
        self.assertEqual(self.page.locator('#historyTotal').inner_text(),'0 筆重大事件')
        self.assertEqual(self.info()['limit'],100)


if __name__=='__main__': unittest.main()
