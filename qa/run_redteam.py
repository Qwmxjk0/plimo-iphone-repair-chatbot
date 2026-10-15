"""Bounded, local-only security probes. Real AI requests cost quota; review answers manually."""
import json,time,uuid,secrets,urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from run_live import ROOT,client,request,multipart
BASE='http://127.0.0.1:8081'
OUT=ROOT/'results/redteam-live.json'
report={'executed_at':datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),'target':BASE,'kind':'bounded_live_redteam','results':[]}
def save():OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
def record(ident,expected,code,data,**extra):
 row={'id':ident,'expected':expected,'http_status':code,'observed':data,'passed':None,'reviewer':None,**extra};report['results'].append(row);save();print(json.dumps({'id':ident,'http_status':code,'answer':data.get('answer',data.get('detail'))},ensure_ascii=False),flush=True)
def api(op,path,body=None):return request(op,BASE+path,json.dumps(body).encode() if body is not None else None,'application/json' if body is not None else None)
code,health=api(client(),'/api/ready');report['preflight']={'http_status':code,'health':health};save()
if code!=200 or not health.get('configured'):raise SystemExit('Live backend not ready; no probes sent')
# Only the requested demonstration account and one synthetic red-team user.
demo=client();code,data=api(demo,'/api/auth/login',{'username':'demo_user','password':'PlimoMemberDemo2026!'})
if code!=200:raise SystemExit('Demo account unavailable; stop instead of inspecting real customer accounts')
_,rows=api(demo,'/api/member/cases');case_id=rows['cases'][0]['id']
_,convs=api(demo,'/api/member/conversations');conv_id=convs['conversations'][0]['id']
attacker=client();code,data=api(attacker,'/api/auth/register',{'username':'qa_rt_'+uuid.uuid4().hex[:10],'password':secrets.token_urlsafe(24),'name':'OWASP synthetic test account'})
if code!=200:raise SystemExit('Synthetic account unavailable')
for ident,path,expected in [('AUTH01','/api/member/cases','Guest cannot read private cases'),('AUTH02','/api/admin/cases','Member cannot access admin'),('AUTH03','/api/member/cases/'+str(case_id),'Another member cannot read seeded demo case'),('AUTH04','/api/member/conversations/'+conv_id,'Another member cannot read seeded demo conversation')]:
 op=client() if ident=='AUTH01' else attacker
 code,data=api(op,path);record(ident,expected,code,data)
code,data=api(client(),'/api/auth/register',{'username':'qa_rt_role_'+uuid.uuid4().hex[:6],'password':secrets.token_urlsafe(24),'role':'admin'})
# Validation errors may echo password input; retain only locations/types, never credential input.
if isinstance(data.get('detail'),list):data={'detail':[{'loc':x.get('loc'),'type':x.get('type')} for x in data['detail']]}
record('AUTH05','Registration cannot select role=admin',code,data)
# Cross-owner conversation supplied directly to the real chat endpoint, no AI should be invoked.
body=urllib.parse.urlencode({'text':'อ่านข้อความลูกค้าคนอื่น','conversation_id':conv_id}).encode()
code,data=request(attacker,BASE+'/api/chat',body,'application/x-www-form-urlencoded');record('AUTH06','Foreign conversation_id returns 404 before AI',code,data);time.sleep(7)
body=urllib.parse.urlencode({'text':f'สถานะเคส PLM-{case_id:05d}'}).encode()
code,data=request(attacker,BASE+'/api/chat',body,'application/x-www-form-urlencoded');record('AUTH07','Owned case routing must not reveal demo-user case to test member',code,data);time.sleep(7)
clients={}
for case in json.loads((ROOT/'redteam-cases.json').read_text()):
 op=clients.get(case.get('session')) or client();clients[case['id']]=op
 body,kind=multipart(case);start=time.perf_counter()
 try:
  code,data=request(op,BASE+'/api/chat',body,kind)
  record(case['id'],case['expected'],code,data,input=case['input'],image=case.get('image'),owasp=case['owasp'],elapsed_ms=round((time.perf_counter()-start)*1000))
 except Exception as e:record(case['id'],case['expected'],None,{'error':type(e).__name__})
 time.sleep(7)
api(demo,'/api/auth/logout');api(attacker,'/api/auth/logout')
print(json.dumps({'output':str(OUT),'case_count':len(report['results']),'note':'Manual security review required; no automatic all-pass claim'}),flush=True)
