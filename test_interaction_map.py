"""Offline tests for persistent UI maps and paginated inspection."""
import json
import tempfile
import unittest
from pathlib import Path
from features.interaction_map import InteractionMap
from features.inspection import pages,content
from test_features import MOCK, specification, strategy
from features.browser import DiscoveryBroker, ground
from features.discovery import LIMITS

TARGET={'name':'miniPaint','visible_version':'mock-v1','build':'offline fixture'}

class MapTests(unittest.TestCase):
    def test_persistence_query_and_target_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'map.json'; m=InteractionMap(path,TARGET)
            m.observe([], 'observation-1',[{'label':'Contrast','type':'range','min':'-10','max':'10','step':'1','value':'0'}],'attempt/observation-1')
            self.assertEqual(m.query('contrast')['nodes'][0]['status'],'observed')
            m.record_route(specification())
            fresh=InteractionMap(path,TARGET)
            self.assertEqual(fresh.query('contrast')['nodes'][0]['status'],'stale')
            self.assertEqual(fresh.route('contrast')['status'],'cached-needs-revalidation')
            fresh.invalidate_route('contrast'); self.assertEqual(fresh.route('contrast')['status'],'stale')
            changed=InteractionMap(path,{**TARGET,'visible_version':'changed'})
            self.assertEqual(changed.query()['total'],0); self.assertIsNone(changed.route('contrast'))
    def test_queries_cover_all_nodes_and_preserve_parent_edges(self):
        with tempfile.TemporaryDirectory() as d:
            m=InteractionMap(Path(d)/'map.json',TARGET)
            actions=[strategy('menuitem','Image'),strategy('menuitem','Adjust')]
            m.observe(actions,'observation-1',[{'label':f'Control {i}','type':'range'} for i in range(420)],'job/discovery/observation-1')
            ids=[]; first=m.query()
            for index in range(first['pages']): ids += [row['id'] for row in m.query(page=index)['nodes']]
            self.assertEqual(len(set(ids)),first['total'])
            for node in m.data['nodes'].values():
                if node['parent']: self.assertIn(node['parent'],m.data['nodes'])
            with self.assertRaises(ValueError): m.query(page=64)

    def test_pagination_preserves_all_content_with_bounded_responses(self):
        raw={'accessibility':'many visible controls\n'*2000,'controls':[{'label':f'Control {i}','text':'x'*120} for i in range(250)]}
        chunks=pages(raw,16000)
        self.assertGreater(len(chunks),1)
        self.assertEqual(''.join(c['accessibility'] for c in chunks),raw['accessibility'])
        self.assertEqual([r for c in chunks for r in c['controls']],raw['controls'])
        for c in chunks: self.assertLessEqual(len(json.dumps(content('observation-1',c)).encode()),16000)
    def test_large_individual_item_fails_without_truncation(self):
        with self.assertRaises(ValueError): pages({'accessibility':'','controls':[{'text':'x'*20000}]},16000)
    def test_incomplete_dialog_pages_cannot_ground(self):
        s=specification(); observed={'observation-1':{'snapshot_id':'one','page':0,'pages':2,'controls':[{'type':'range','dialog':'Adjust','row':'Contrast: 0','min':'-10','max':'10','step':'1','value':'0'}]}}
        with self.assertRaisesRegex(ValueError,'every page'): ground(s,observed)

class InspectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw=sync_playwright().start(); cls.browser=cls.pw.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls): cls.browser.close(); cls.pw.stop()
    def setUp(self): self.page=self.browser.new_page(); self.page.set_content(MOCK)
    def tearDown(self): self.page.close()
    def test_large_menu_click_succeeds_and_controls_remain_reachable(self):
        html='<button role="menuitem">Effects</button>'+''.join(f'<button role="menuitem">Item {i}</button>' for i in range(300))
        self.page.set_content(html)
        with tempfile.TemporaryDirectory() as d:
            broker=DiscoveryBroker(self.page,Path(d),LIMITS)
            response=broker.call('visible_click',{'locator':strategy('menuitem','Effects'),'dialog':''})
            self.assertEqual(json.loads(response[0]['text'])['action_status'],'succeeded')
            self.assertEqual(len(broker.observations),0)
            first=json.loads(broker.call('visible_inspect',{'scope':'page','dialog':'','page':0})[0]['text'])['untrusted_visible_data']
            all_controls=list(first['controls']); self.assertGreater(first['pages'],1)
            for index in range(1,first['pages']):
                value=json.loads(broker.call('visible_inspect',{'scope':'page','dialog':'','page':index})[0]['text'])['untrusted_visible_data']
                all_controls+=value['controls']
            self.assertEqual(len(all_controls),301)
    def test_action_invalidates_snapshot_and_dialog_focus_excludes_page_noise(self):
        with tempfile.TemporaryDirectory() as d:
            broker=DiscoveryBroker(self.page,Path(d),LIMITS)
            broker.call('visible_inspect',{'scope':'page','dialog':'','page':0})
            broker.call('visible_set',{'locator':strategy('slider','Contrast:','row'),'dialog':'Adjust','value':3})
            with self.assertRaisesRegex(ValueError,'Snapshot changed'):
                broker.call('visible_inspect',{'scope':'page','dialog':'','page':1})
            value=json.loads(broker.call('visible_inspect',{'scope':'auto','dialog':'','page':0})[0]['text'])['untrusted_visible_data']
            self.assertEqual(value['scope'],'dialog')
            self.assertFalse(any(c.get('text')=='Image' for c in value['controls']))
    def test_map_tools_do_not_count_as_current_observation(self):
        with tempfile.TemporaryDirectory() as d:
            broker=DiscoveryBroker(self.page,Path(d)/'observations',LIMITS)
            broker.site_map=InteractionMap(Path(d)/'map.json',TARGET)
            broker.call('visible_inspect',{})
            count=len(broker.observations)
            value=json.loads(broker.call('map_query',{'query':'Contrast','parent':'','page':0})[0]['text'])
            self.assertTrue(value['nodes']); self.assertEqual(len(broker.observations),count)
