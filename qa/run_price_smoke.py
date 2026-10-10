"""Live price + repeat-cache + model distinction evidence (paid upstream calls)."""
from run_live import client, request, multipart, ROOT
import json, time
from datetime import datetime
from zoneinfo import ZoneInfo

if __name__=='__main__':
    opener=client();base='http://127.0.0.1:8081';records=[]
    for label,text in [('price','เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไร'),('repeat','เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไร'),('pro_max','เปลี่ยนหน้าจอ iPhone 13 Pro Max ราคาเท่าไร')]:
        start=time.perf_counter();body,typ=multipart({'input':text})
        status,data=request(opener,base+'/api/chat',body,typ)
        records.append({'case':label,'input':text,'http_status':status,'elapsed_ms':round((time.perf_counter()-start)*1000),'observed':data})
    p=ROOT/'results/price-cache-model.json';p.write_text(json.dumps({'executed_at':datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),'target':base,'records':records},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(p),'http_statuses':[r['http_status'] for r in records],'answer_cache':[r['observed'].get('cache',{}).get('answer') for r in records]}))
