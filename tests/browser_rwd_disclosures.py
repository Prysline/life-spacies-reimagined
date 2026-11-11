import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
HTML = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
class ResponsiveDisclosuresBrowserRegression(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-gpu'])
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.p.stop()
 def setUp(self):
  self.context=self.browser.new_context(viewport={'width':390,'height':844});self.page=self.context.new_page();self.err=[]
  self.page.on('pageerror',lambda e:self.err.append(str(e)));self.page.set_content(HTML,wait_until='load');self.page.evaluate('document.querySelector("#autoFeed").checked=false')
 def tearDown(self):
  self.assertEqual(self.err,[]);self.context.close()
 def openTool(self,id):self.page.locator(f'[data-tool-toggle="{id}"]').click()
 def create(self,gene='GeneMobile'):
  self.openTool('genePanel');self.page.locator('#geneText').fill(gene);self.page.locator('#createBtn').click()
 def test_1_mobile_default_collapsed_and_short(self):
  for id in ['genePanel','feedPanel','controlPanel']:
   self.assertFalse(self.page.locator(f'#{id} .tool-body').is_visible());self.assertEqual(self.page.locator(f'#{id} .tool-toggle').get_attribute('aria-expanded'),'false')
  self.assertFalse(self.page.locator('#archiveDetail').is_visible())
  self.assertFalse(self.page.locator('body').evaluate('(e)=>e.classList.contains("specimen-open")'))
 def test_2_quick_links_open_correct_panels(self):
  self.page.locator('a[href="#feedPanel"].quick-link').click();self.assertTrue(self.page.locator('#feedText').is_visible())
  self.page.locator('a[href="#genePanel"].quick-link').click();self.assertTrue(self.page.locator('#createBtn').is_visible())
  self.page.locator('#genePanel .tool-toggle').click();self.assertFalse(self.page.locator('#createBtn').is_visible())
  self.openTool('controlPanel');self.assertTrue(self.page.locator('#pauseBtn').is_visible())
 def test_3_mobile_archive_detail_open_and_close(self):
  self.create();self.page.locator('#archiveList [data-open-creature]').first.click()
  self.assertTrue(self.page.locator('#archiveDetail').is_visible());self.assertEqual(self.page.locator('#archiveDetail').get_attribute('role'),'dialog');self.assertEqual(self.page.locator('#archiveDetail').get_attribute('aria-modal'),'true')
  self.assertEqual(self.page.locator('body.specimen-open').count(), 1);self.assertTrue(self.page.locator('#archiveDetailTitle').is_visible())
  for name in ['gene','life','kin','status']:
   self.page.locator(f'[data-archive-tab="{name}"]').click();self.assertEqual(self.page.locator(f'[data-archive-tab="{name}"]').get_attribute('aria-selected'),'true')
  self.page.locator('[data-detail-close="list"]').click()
  self.assertFalse(self.page.locator('#archiveDetail').is_visible());self.assertEqual(self.page.locator('body.specimen-open').count(), 0);self.assertTrue(self.page.locator('#archiveList [aria-current="true"]').is_visible())
 def test_4_close_to_stage_and_keyboard_escape(self):
  self.create();self.page.locator('#archiveList [data-open-creature]').first.click()
  self.page.keyboard.press('Escape');self.assertFalse(self.page.locator('#archiveDetail').is_visible())
  self.page.locator('#archiveList [data-open-creature]').first.click()
  self.page.locator('[data-detail-close="stage"]').click();self.assertFalse(self.page.locator('#archiveDetail').is_visible());self.assertEqual(self.page.evaluate('document.activeElement.id'),'world')
 def test_5_320_no_overflow(self):
  self.page.set_viewport_size({'width':320,'height':700});self.create();self.page.locator('#archiveList [data-open-creature]').first.click()
  self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),321)
  self.assertLessEqual(self.page.locator('#archiveDetail').bounding_box()['width'],320)
 def test_6_desktop_tools_and_archive_still_visible(self):
  self.page.set_viewport_size({'width':1440,'height':900})
  self.assertFalse(self.page.locator('.tool-toggle').first.is_visible())
  for name in ['geneText','feedText','pauseBtn']:
   self.assertTrue(self.page.locator(f'#{name}').is_visible())
  self.assertFalse(self.page.locator('#archiveDetail').is_visible())
  self.page.locator('#geneText').fill('DesktopGene');self.page.locator('#createBtn').click();self.page.locator('#archiveList [data-open-creature]').first.click();self.assertTrue(self.page.locator('#archiveDetail').is_visible());self.assertTrue(self.page.locator('#archiveDetailTitle').is_visible())
  self.assertEqual(self.page.locator('#archiveDetail').get_attribute('role'),None)
 def test_7_return_on_resize_and_no_data_loss(self):
  self.create('KeepData');self.page.locator('#archiveList [data-open-creature]').first.click()
  self.page.set_viewport_size({'width':1440,'height':900});self.assertEqual(self.page.locator('body.specimen-open').count(), 0)
  self.assertIn('KeepData',self.page.locator('#archiveList').inner_text())
  self.page.set_viewport_size({'width':390,'height':844});self.assertFalse(self.page.locator('#archiveDetail').is_visible())
  self.page.locator('#archiveList [data-open-creature]').first.click();self.assertTrue(self.page.locator('#archiveDetail').is_visible())
 def test_8_reset_closes_and_retains_no_phantom_dialog(self):
  self.create();self.page.locator('#archiveList [data-open-creature]').first.click()
  self.page.evaluate('document.querySelector("#clearBtn").click()')
  self.assertEqual(self.page.locator('body.specimen-open').count(), 0);self.assertEqual(self.page.locator('#births').inner_text(),'0')
 def test_10_gene_inspector_collapses_and_resizes_preview(self):
  self.assertFalse(self.page.locator('#inspectorResearch').is_visible())
  self.assertEqual(self.page.locator('#inspectorDisclosure').get_attribute('aria-expanded'),'false')
  self.page.locator('a.quick-link[href="#inspector"]').click()
  self.assertTrue(self.page.locator('#inspectorResearch').is_visible())
  self.assertGreater(self.page.locator('#previewCanvas').evaluate('(el)=>el.width'),300)
  self.page.locator('#inspectorDisclosure').click()
  self.assertFalse(self.page.locator('#inspectorResearch').is_visible())
  self.page.locator('#inspectorDisclosure').click()
  self.assertTrue(self.page.locator('#inspectorResearch').is_visible())

 def test_9_entry_from_event_opens_same_detail(self):
  self.create();self.page.locator('#eventLog [data-creature-id="4"]').first.click()
  self.assertTrue(self.page.locator('#archiveDetail').is_visible())
  self.assertIn('生物 #4',self.page.locator('#archiveDetailTitle').inner_text())
if __name__=='__main__':unittest.main(verbosity=2)
