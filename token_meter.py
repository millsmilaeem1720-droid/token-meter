#!/usr/bin/env python3
# TokenMeter v2 - by jie
import sqlite3,os,hashlib,argparse,datetime,json
DB=os.path.join(os.path.dirname(__file__),'token_meter.db')
def dbc():
  conn=sqlite3.connect(DB)
  conn.executescript('CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT,ph TEXT,pt INT,ct INT,m TEXT,cost REAL,ts TEXT);CREATE INDEX IF NOT EXISTS xph ON c(ph);CREATE INDEX IF NOT EXISTS xm ON c(m)')
  return conn
def hsh(t): return hashlib.sha256(t.encode()).hexdigest()
PRC={'gpt-5.5':{'i':15.0,'o':60.0},'gpt-5.5-pro':{'i':30.0,'o':120.0},'gpt-5.4':{'i':10.0,'o':40.0},'deepseek-chat':{'i':0.14,'o':0.28},'deepseek-reasoner':{'i':0.55,'o':2.19}}
def cost(m,pt,ct):p=PRC.get(m,{'i':10.0,'o':40.0});return(pt/1e6*p['i'])+(ct/1e6*p['o'])
def rec(t,pt,ct,m):
  c=cost(m,pt,ct);conn=dbc()
  conn.execute('INSERT INTO c VALUES(?,?,?,?,?,?,?)',(None,hsh(t),pt,ct,m,c,datetime.datetime.now().isoformat()))
  conn.commit();conn.close();return c
def est(t,m='deepseek-chat'):
  conn=dbc()
  ph=hsh(t)
  rows=conn.execute('SELECT pt,ct,cost FROM c WHERE ph=? AND m=? ORDER BY ts DESC LIMIT 5',(ph,m)).fetchall()
  if rows:
    ac=sum(r[2] for r in rows)/len(rows);conn.close()
    return{'s':'exact','n':len(rows),'c':round(ac,4),'pt':int(sum(r[0]for r in rows)/len(rows)),'ct':int(sum(r[1]for r in rows)/len(rows))}
  ept=max(1,len(t)//4)
  er=conn.execute('SELECT AVG(ct*1.0/pt)FROM c WHERE m=? AND pt>0',(m,)).fetchone()[0]
  conn.close()
  ect=int(ept*er)if er and er>0 else ept
  return{'s':'est','c':round(cost(m,ept,ect),4),'pt':ept,'ct':ect}
def sts():
  conn=dbc()
  t=conn.execute('SELECT COUNT(*),SUM(cost),SUM(pt),SUM(ct)FROM c').fetchone()
  td=datetime.date.today().isoformat()
  today=conn.execute('SELECT COUNT(*),SUM(cost)FROM c WHERE ts LIKE ?',(td+'%',)).fetchone()
  bm=conn.execute('SELECT m,COUNT(*),SUM(cost),SUM(pt),SUM(ct)FROM c GROUP BY m ORDER BY SUM(cost)DESC').fetchall()
  conn.close()
  return{'n':t[0]or 0,'c':round(t[1]or 0,4),'pt':t[2]or 0,'ct':t[3]or 0,'td':today[0]or 0,'tc':round(today[1]or 0,4),'bm':[(r[0],r[1],round(r[2],4))for r in bm]}
def recent(n=10):
  conn=dbc()
  rows=conn.execute('SELECT ts,m,pt,ct,cost FROM c ORDER BY ts DESC LIMIT ?',(n,)).fetchall()
  conn.close();return rows
def xport(f='token_meter_export.jsonl'):
  conn=dbc()
  rows=conn.execute('SELECT ph,pt,ct,m,cost,ts FROM c ORDER BY ts').fetchall()
  conn.close()
  with open(f,'w')as fh:
    for r in rows:fh.write(json.dumps({'ph':r[0],'pt':r[1],'ct':r[2],'m':r[3],'c':r[4],'ts':r[5]})+chr(10))
  return len(rows)
def imort(f):
  conn=dbc();c=0
  with open(f)as fh:
    for line in fh:
      d=json.loads(line.strip())
      conn.execute('INSERT INTO c VALUES(?,?,?,?,?,?,?)',(None,d['ph'],d['pt'],d['ct'],d['m'],d['c'],d['ts']))
      c+=1
  conn.commit();conn.close();return c
if __name__=='__main__':
  p=argparse.ArgumentParser(description='TokenMeter v2')
  sub=p.add_subparsers(dest='cmd')
  for c in[('rec','Record'),('sts','Stats'),('est','Estimate'),('recent','Recent'),('export','Export'),('import','Import')]:
    s=sub.add_parser(c[0],help=c[1])
    if c[0]=='rec':s.add_argument('--t',required=True);s.add_argument('--pt',type=int,required=True);s.add_argument('--ct',type=int,required=True);s.add_argument('--m',default='deepseek-chat')
    if c[0]=='est':s.add_argument('--t',required=True);s.add_argument('--m',default='deepseek-chat')
    if c[0]=='recent':s.add_argument('--n',type=int,default=10)
    if c[0]=='import':s.add_argument('--file',required=True)
  a=p.parse_args()
  if not a.cmd:
    s=sts()
    print(f'TokenMeter by jie');print(40*'=')
    print(f'Total: {s["n"]} calls  ${s["c"]}')
    print(f'Today: {s["td"]} calls  ${s["tc"]}')
    print(f'Tokens: {s["pt"]:,} in + {s["ct"]:,} out')
    if s['bm']:
      for r in s['bm']:print(f'  {r[0]:20s}{r[1]:3d}calls ${r[2]:.4f}')
  elif a.cmd=='rec':print(f'Recorded: {rec(a.t,a.pt,a.ct,a.m):.4f}')
  elif a.cmd=='est':
    r=est(a.t,a.m)
    t='Exact match'if r['s']=='exact'else'Estimated'
    print(f'[{t}] in~{r["pt"]}+out~{r["ct"]}=~${r["c"]}')
  elif a.cmd=='sts':
    s=sts()
    print(f'Total: {s["n"]} calls  ${s["c"]}')
    if s['bm']:
      for r in s['bm']:print(f'  {r[0]:20s}{r[1]:3d}calls ${r[2]:.4f}')
  elif a.cmd=='recent':
    print(f'{"Time":20s}{"Model":20s}{"In":>6s}{"Out":>6s}{"Cost":>8s}')
    print('-'*62)
    for r in recent(a.n):print(f'{r[0][:19]:20s}{r[1]:20s}{r[2]:6d}{r[3]:6d}${r[4]:>7.4f}')
  elif a.cmd=='export':print(f'Exported {xport()} records')
  elif a.cmd=='import':print(f'Imported {imort(a.file)} records')
import urllib.request
def _post(url,body,key):
  d=json.dumps(body).encode()
  r=urllib.request.Request(url,data=d,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
  return json.loads(urllib.request.urlopen(r).read())
def call_chat(prompt,model='deepseek-chat',api_key=None,system=None,**kw):
  key=api_key or os.environ.get('OPENAI_API_KEY','')
  if not key:raise ValueError('Set OPENAI_API_KEY')
  msgs=[]
  if system:msgs.append({'role':'system','content':system})
  msgs.append({'role':'user','content':prompt})
  body={'model':model,'messages':msgs};body.update(kw)
  url='https://api.deepseek.com/v1/chat/completions'if model.startswith('deepseek')else'https://api.openai.com/v1/chat/completions'
  d=_post(url,body,key)
  if'error'in d:raise Exception('API:'+str(d['error']))
  u=d.get('usage',{});pt=u.get('prompt_tokens',0);ct=u.get('completion_tokens',0)
  c=rec(prompt,pt,ct,model)
  return d['choices'][0]['message']['content'],{'cost':c,'pt':pt,'ct':ct,'model':model}