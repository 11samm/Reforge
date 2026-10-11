"""Bounded synthetic inputs and summaries of actual visible PNG exports."""
from PIL import Image
from .core import validate_plan
from adapter.png import png_info

DEFINITIONS = {
    'impulse_center':'Opaque black background; one opaque white pixel at (floor(width/2),floor(height/2)).',
    'impulse_boundary':'Opaque black background; one opaque white pixel at (0,floor(height/2)); LEFT MIDPOINT, not corner.',
    'edge':'Opaque black for x<floor(width/2); opaque white otherwise.',
    'gradient':'Opaque RGB(round(x*255/(width-1)),round(y*255/(height-1)),64).',
    'checkerboard':'Opaque black/white 3x3 blocks; white when (floor(x/3)+floor(y/3)) modulo2 is1.',
    'rgb':'Opaque vertical red/green/blue thirds using min(2,floor(x*3/width)).',
    'alpha':'Vertical bands: x<floor(width/3) RGBA(0,0,0,0); x<floor(2*width/3) RGBA(255,64,16,128); otherwise RGBA(0,32,255,255). NOT hidden-blue/red step.'}

# Developer-selected follow-up patterns. Not offered to the model planner schema.
DEVELOPER_DEFINITIONS = {
    'dev_uniform_low_alpha':'Every pixel RGBA(200,100,50,10).',
    'dev_adjacent_alpha':'x<floor(width/2) RGBA(255,0,0,255); otherwise RGBA(0,0,255,40).',
    'dev_hidden_rgb':'x<floor(width/2) RGBA(0,255,0,0) (fully transparent, nonzero hidden green); otherwise RGBA(255,0,0,255).'}

from .developer_precision_patterns import DEFINITIONS as PRECISION_DEFINITIONS, render as render_precision
DEVELOPER_DEFINITIONS.update(PRECISION_DEFINITIONS)
ALL_DEFINITIONS = DEFINITIONS | DEVELOPER_DEFINITIONS

def render(kind, w, h):
    if kind not in ALL_DEFINITIONS: raise ValueError('Unknown generator')
    if kind in PRECISION_DEFINITIONS: return render_precision(kind,w,h)
    image=Image.new('RGBA',(w,h),(0,0,0,255))
    pixels=image.load()
    for y in range(h):
        for x in range(w):
            if kind=='edge': pixels[x,y]=(255,255,255,255) if x >= w//2 else (0,0,0,255)
            elif kind=='gradient': pixels[x,y]=(round(x*255/(w-1)),round(y*255/(h-1)),64,255)
            elif kind=='checkerboard': pixels[x,y]=(255,255,255,255) if (x//3+y//3)%2 else (0,0,0,255)
            elif kind=='rgb': pixels[x,y]=[(255,0,0,255),(0,255,0,255),(0,0,255,255)][min(2,x*3//w)]
            elif kind=='alpha':
                pixels[x,y]=(0,0,0,0) if x < w//3 else (255,64,16,128) if x < 2*w//3 else (0,32,255,255)
            elif kind=='dev_uniform_low_alpha': pixels[x,y]=(200,100,50,10)
            elif kind=='dev_adjacent_alpha': pixels[x,y]=(255,0,0,255) if x < w//2 else (0,0,255,40)
            elif kind=='dev_hidden_rgb': pixels[x,y]=(0,255,0,0) if x < w//2 else (255,0,0,255)
    if kind.startswith('impulse'):
        pixels[w//2 if kind=='impulse_center' else 0,h//2]=(255,255,255,255)
    return image

def generate(plan, path, config):
    validate_plan(plan, config)
    return write_input(plan['input'], path)

def write_input(spec, path):
    if path.exists(): raise ValueError('Refusing to overwrite diagnostic input')
    render(spec['kind'],spec['width'],spec['height']).save(path)
    return png_info(path)

def describe(path):
    with Image.open(path) as raw:
        image=raw.convert('RGBA'); w,h=image.size
        points=sorted(set([(0,0),(w-1,0),(0,h-1),(w-1,h-1),(w//2,h//2),(1,1)]))
        # Exact samples from user-visible exports. No browser canvas reads.
        return {'png':png_info(path),'center_row':[list(image.getpixel((x,h//2))) for x in range(w)],
                'center_column':[list(image.getpixel((w//2,y))) for y in range(h)],
                'top_row':[list(image.getpixel((x,0))) for x in range(w)],
                'samples':[{'xy':[x,y],'rgba':list(image.getpixel((x,y)))} for x,y in points],
                'alpha_sum':sum(image.getchannel('A').get_flattened_data()),
                'red_sum':sum(image.getchannel('R').get_flattened_data())}

def compact_samples(samples):
    """Lossless run-length rows avoid repeating uniform exported samples in model packets."""
    def runs(row):
        result=[]
        for i,pixel in enumerate(row):
            if result and result[-1][2:]==pixel: result[-1][1]+=1
            else: result.append([i,1,*pixel])
        return result
    return {k:v for k,v in samples.items() if k not in ['center_row','center_column','top_row']} | {
        'profile_encoding':'Each run is [start_index,length,R,G,B,A]; exactly reconstructs its named axis profile.',
        **{k+'_runs':runs(samples[k]) for k in ['center_row','center_column','top_row']}}

def compact_evidence(e):
    return {k:v for k,v in e.items() if k not in ['input_samples','export_samples','input','expected','procedure_record']} | {
        'input_samples':compact_samples(e['input_samples']),'export_samples':compact_samples(e['export_samples'])}
