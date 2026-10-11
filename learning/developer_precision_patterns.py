"""User-authorized developer-added precision probes; not model-planner patterns."""
from PIL import Image
DEFINITIONS = {
 'dev_precision_atlas': '257x257 atlas: top-left vertical opaque black/white step x=64; top-right asymmetric colored rectangle and point; bottom-left alpha-15 color seam x=64; bottom-right same color seam x=192 at alpha255. Exact recipe is archived.',
 'dev_precision_transpose': 'Exact transpose of dev_precision_atlas; all channels and dimensions preserved.',
 'dev_impulse_64': '65x65 opaque black; center (32,32) RGB64 alpha255.',
 'dev_impulse_128': '65x65 opaque black; center (32,32) RGB128 alpha255.'}
def render(kind,w,h):
 if kind.startswith('dev_impulse_'):
  if (w,h)!=(65,65): raise ValueError('Amplitude comparison requires 65x65')
  a=int(kind.rsplit('_',1)[1]); im=Image.new('RGBA',(w,h),(0,0,0,255)); im.putpixel((32,32),(a,a,a,255)); return im
 if (w,h)!=(257,257): raise ValueError('Atlas requires 257x257')
 im=Image.new('RGBA',(w,h),(0,0,0,255)); px=im.load()
 for y in range(h):
  for x in range(w):
   if y<128 and x<128: px[x,y]=(255,255,255,255) if x>=64 else (0,0,0,255)
   elif y>=128:
    local=x if x<128 else x-128
    rgb=(51,102,153) if local<64 else (204,153,102)
    px[x,y]=(*rgb,15 if x<128 else 255)
 for y in range(40,83):
  for x in range(160,182): px[x,y]=(255,128,64,255)
 px[209,88]=(64,255,128,255)
 return im.transpose(Image.Transpose.TRANSPOSE) if kind=='dev_precision_transpose' else im
