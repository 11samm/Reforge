"""Explicit operation specifications. Gaussian Blur remains on its original configuration."""
BRIGHTNESS = {
 'id':'brightness','version':1,'name':'Brightness (Color Corrections)',
 'menu':['Image','Color Corrections ...'],'dialog':'Color Corrections',
 'parameter':{'name':'Brightness','key':'brightness','min':-100,'max':100,'default':0,'step':1},
 'frozen_controls':{'Contrast':0,'Saturation':0,'Hue':0,'Luminance':0,'Red channel':0,'Green channel':0,'Blue channel':0},
 'scope':'Fresh transparent document; one imported raster layer, offset 0, rotation 0, opacity 100; no other layers; PNG All layers at resolution 72, no resize.',
 'source':'src/brightness.ts','export':'applyBrightness','interface':'applyBrightness(raster: Raster, brightness: number): Raster',
 'ui_menu':'Image','ui_item':'Color Corrections…','ui_parameter':'Brightness',
 'policy':'exact-rgba-v1','provenance':'evidence/learning/brightness-preparation/imported-scope-2/parameters.json',
}

def operation_spec(ident):
 if ident!='brightness': raise ValueError('Unknown operation specification')
 return BRIGHTNESS
