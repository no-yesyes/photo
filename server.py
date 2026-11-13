from __future__ import annotations
import base64,io,json,math,mimetypes,os,threading,uuid
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).parent; STATIC=ROOT/'static'; OUT=ROOT/'outputs'; OUT.mkdir(exist_ok=True); TASKS={}; LOCK=threading.Lock()
def load_env():
 p=ROOT/'.env'
 if p.exists():
  for line in p.read_text(encoding='utf-8').splitlines():
   line=line.strip()
   if line and not line.startswith('#') and '=' in line:
    k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"\''))
def panel_boxes(w,h):
 pw=min(w,round(h*1.5)); stride=max(1,round(pw*.76)); n=max(1,math.ceil(max(0,w-pw)/stride)+1); starts=[round(i*(w-pw)/(n-1)) if n>1 else 0 for i in range(n)]; return [(x,0,min(w,x+pw),h) for x in starts]
def demo_panel(prompt,w,h,offset):
 im=Image.new('RGB',(w,h)); d=ImageDraw.Draw(im)
 for y in range(h):
  t=y/max(1,h-1); c=tuple(round(a*(1-t)+b*t) for a,b in zip((171,211,225),(246,223,184))); d.line((0,y,w,y),fill=c)
 for x in range(-h,w+h,max(1,h//3)):
  cx=x+offset%h; d.ellipse((cx-85,h*.32,cx+85,h*.82),fill=(75,126,104)); d.polygon([(cx-145,h*.53),(cx,h*.06),(cx+145,h*.53)],fill=(63,110,94))
 d.rectangle((0,round(h*.81),w,h),fill=(83,142,128)); d.text((24,22),'OFFLINE PREVIEW / NOT AI GENERATED',fill=(32,49,48)); d.text((24,45),prompt[:100],fill=(32,49,48)); return im
def call_image_api(prompt,size):
 key=os.environ.get('IMAGE_API_KEY','')
 if not key: raise RuntimeError('未配置 IMAGE_API_KEY。请复制 .env.example 为 .env 并填写密钥，或启用演示预览。')
 base=os.environ.get('IMAGE_API_BASE','https://api.openai.com/v1').rstrip('/'); body={'model':os.environ.get('IMAGE_MODEL','gpt-image-1'),'prompt':prompt,'size':os.environ.get('IMAGE_SIZE',size),'n':1}; req=Request(base+'/images/generations',data=json.dumps(body).encode(),headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
 try:
  with urlopen(req,timeout=180) as r: payload=json.loads(r.read())
 except HTTPError as e: raise RuntimeError(f'图像 API 返回 HTTP {e.code}: {e.read().decode("utf-8","replace")[:1000]}') from e
 except URLError as e: raise RuntimeError(f'无法连接图像 API: {e.reason}') from e
 item=payload.get('data',[{}])[0]
 if item.get('b64_json'): return Image.open(io.BytesIO(base64.b64decode(item['b64_json']))).convert('RGB')
 if item.get('url'):
  with urlopen(item['url'],timeout=180) as r: return Image.open(io.BytesIO(r.read())).convert('RGB')
 raise RuntimeError('API 响应未包含图片，请检查服务兼容性。')
def fit_cover(im,size):
 w,h=size; s=max(w/im.width,h/im.height); r=im.resize((round(im.width*s),round(im.height*s)),Image.Resampling.LANCZOS); x=(r.width-w)//2; y=(r.height-h)//2; return r.crop((x,y,x+w,y+h))
def stitch(panels,boxes,w,h):
 acc=np.zeros((h,w,3),np.float32); den=np.zeros((h,w),np.float32)
 for im,(x0,_,x1,_) in zip(panels,boxes):
  im=fit_cover(im.convert('RGB'),(x1-x0,h)); pw=x1-x0; ramp=min(max(2,round(h*.12)),pw//2); wt=np.ones((h,pw),np.float32); fade=np.linspace(1/ramp,1,ramp,dtype=np.float32)
  if x0: wt[:,:ramp]*=fade[None,:]
  if x1<w: wt[:,-ramp:]*=fade[::-1][None,:]
  acc[:,x0:x1]+=np.asarray(im,np.float32)*wt[:,:,None]; den[:,x0:x1]+=wt
 return Image.fromarray((acc/np.maximum(den[:,:,None],1e-6)).clip(0,255).astype('uint8'),'RGB')
def build_prompt(prompt,i,n):
 pos='左侧' if i==0 else '右侧' if i==n-1 else '中间'; return f'{prompt}\n生成横向超宽全景图的{pos}延展段（第 {i+1}/{n} 段）。与同一全景严格保持主体、风格、色彩、光线、地平线和视角一致；边缘自然延续，重要主体放在中部；不要文字、边框、分格或拼贴。'
def generate(tid,req):
 try:
  w,h=int(req['width']),int(req['height'])
  if w<256 or h<128 or w>16384 or h>4096 or not 3.01<=w/h<=20: raise ValueError('尺寸范围：宽 256–16384、高 128–4096，比例需大于 3:1 且不超过 20:1。')
  prompt=str(req.get('prompt','')).strip()[:2000]
  if not prompt: raise ValueError('请输入画面提示词。')
  boxes=panel_boxes(w,h); panels=[]
  for i,b in enumerate(boxes):
   with LOCK: TASKS[tid].update(progress=round(i/len(boxes)*78),status=f'生成第 {i+1}/{len(boxes)} 段')
   pw=b[2]-b[0]; panel=demo_panel(prompt,pw,h,b[0]) if req.get('demo') else call_image_api(build_prompt(prompt,i,len(boxes)),os.environ.get('IMAGE_SIZE','1536x1024')); panels.append(panel)
  with LOCK: TASKS[tid].update(progress=84,status='羽化融合重叠区域')
  result=stitch(panels,boxes,w,h); name=f'{tid}.png'; result.save(OUT/name,format='PNG',optimize=True)
  with LOCK: TASKS[tid].update(progress=100,status='生成完成',done=True,image=f'/outputs/{name}',width=w,height=h,ratio=round(w/h,2),panels=len(boxes),demo=bool(req.get('demo')))
 except Exception as e:
  with LOCK: TASKS[tid].update(done=True,error=str(e),status='生成失败')
class Handler(BaseHTTPRequestHandler):
 def log_message(self,fmt,*args): print(f'[{self.log_date_time_string()}] {fmt%args}')
 def json_response(self,value,code=200):
  data=json.dumps(value,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
 def send_file(self,path):
  try: data=path.read_bytes()
  except OSError: self.send_error(404); return
  self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(str(path))[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
 def do_GET(self):
  path=self.path.split('?',1)[0]
  if path.startswith('/api/tasks/'):
   with LOCK: task=TASKS.get(path.rsplit('/',1)[-1]); task=dict(task) if task else None
   return self.json_response(task or {'error':'任务不存在'},200 if task else 404)
  if path.startswith('/outputs/'): return self.send_file(OUT/Path(path).name)
  return self.send_file(STATIC/('index.html' if path=='/' else path.lstrip('/')))
 def do_POST(self):
  if self.path!='/api/generate': return self.json_response({'error':'接口不存在'},404)
  size=int(self.headers.get('Content-Length','0'))
  if size>1024*1024: return self.json_response({'error':'请求体过大'},413)
  try: req=json.loads(self.rfile.read(size))
  except (json.JSONDecodeError,ValueError): return self.json_response({'error':'请求格式无效'},400)
  tid=uuid.uuid4().hex[:16]
  with LOCK: TASKS[tid]={'progress':0,'status':'任务已排队','done':False}
  threading.Thread(target=generate,args=(tid,req),daemon=True).start(); return self.json_response({'task_id':tid},202)
def main():
 load_env(); host=os.environ.get('HOST','127.0.0.1'); port=int(os.environ.get('PORT','8000')); print(f'WideCanvas running at http://{host}:{port}'); ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=='__main__': main()
