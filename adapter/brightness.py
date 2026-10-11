"""Brightness procedure uses visible controls and exported PNGs only."""
import re,time
from playwright.sync_api import expect
from .minipaint import MiniPaintAdapter
from .png import compare_pngs
from learning.operations import BRIGHTNESS
from learning.core import save

class BrightnessAdapter(MiniPaintAdapter):
 def apply_brightness(self,value):
  if self.phase!='imported' or type(value) is not int or not -100<=value<=100:
   raise ValueError('Brightness requires original import and integer -100..100')
  with self.action('apply_brightness',requested=value,frozen_controls=BRIGHTNESS['frozen_controls']) as record:
   self.menu(*BRIGHTNESS['menu']); dialog=self.dialog(BRIGHTNESS['dialog'])
   for name,v in {**BRIGHTNESS['frozen_controls'],'Brightness':value}.items():
    row=dialog.get_by_role('row',name=re.compile('^'+re.escape(name)+':'))
    slider=row.get_by_role('slider')
    bounds=(-180,180) if name=='Hue' else (-255,255) if 'channel' in name else (-100,100)
    for attr,want in [('min',str(bounds[0])),('max',str(bounds[1])),('step','1')]: expect(slider).to_have_attribute(attr,want)
    expect(slider).to_have_value('0')
    for _ in range(abs(v)): slider.press('ArrowRight' if v>0 else 'ArrowLeft')
    expect(slider).to_have_value(str(v)); expect(row.get_by_role('cell').last).to_have_text(str(v))
   self.capture_screenshot(self.artifact_dir/'accepted-brightness.png')
   dialog.get_by_role('button',name='Ok',exact=True).click(); expect(dialog).not_to_be_visible()
   self.assert_dimensions(); expect(self.page.locator('[id="layer_name"]')).to_have_count(1)
   self.capture_screenshot(self.artifact_dir/'operation-complete.png')
   record['accepted_brightness']=value; self.accepted_brightness=value; self.phase='operated'

def reference_brightness(request,directory):
 from learning.core import digest
 from .png import within,png_info
 started=time.monotonic(); report={'status':'infrastructure_failure','id':request['id'],'requested_brightness':request['brightness']}
 path=within(request['input_path'],directory.parent.parent/'inputs')
 if digest(path)!=request['input_sha256']: raise ValueError('Input changed')
 info=png_info(path)
 setup={'canvas_width':info['width'],'canvas_height':info['height'],'transparent':True,'resolution_ui':72,'imported_layer_offset':[0,0],'layer_opacity_percent':100,'layer_rotation_degrees':0,'fresh_original_input':True,'other_visible_layers':False}
 try:
  with BrightnessAdapter(directory,headed=True,window_position=request.get('window_position',[1600,0]),diagnostic_input_root=path.parent) as a:
   a.reset_reference(setup); report['target']=a.identity
   if a.identity['version_discrepancy']: raise ValueError('Target version changed')
   report['import']=a.import_image(path,route='file_chooser'); a.export_png(directory/'original-confirmation.png')
   report['original_confirmation']=compare_pngs(path,directory/'original-confirmation.png')
   if not report['original_confirmation']['rgba_equal']:
    report['status']='import_normalization'; return report
   if request.get('import_only'): report['status']='import_exact'; return report
   a.apply_brightness(request['brightness']); report['accepted_brightness']=a.accepted_brightness
   report['output_path']=str(directory/'output.png'); report['output']=a.export_png(directory/'output.png'); report['status']='observed'; report['actions']=a.actions
 except Exception as e: report['error']={'type':type(e).__name__,'message':str(e)[:2000]}
 finally:
  report['elapsed_seconds']=round(time.monotonic()-started,3); save(directory/'reference-record.json',report)
 return report
