"""Live shop-persona smoke checks. Invokes paid upstream requests; saves actual answers."""
from run_live import client, request, multipart, ROOT
from datetime import datetime
from zoneinfo import ZoneInfo
import json
cases=[('hours','ร้านเปิดกี่โมงครับ'),('price','เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไร'),('repeat','เปลี่ยนหน้าจอ iPhone 13 ราคาเท่าไร'),('parts','ถ้าต้องซื้ออะไหล่เพิ่ม ต้องจ่ายเพิ่มโดยไม่แจ้งผมหรือเปล่า'),('pro_max','เปลี่ยนหน้าจอ iPhone 13 Pro Max ราคาเดียวกับรุ่นธรรมดาไหม'),('warranty','ซ่อมแล้วรับประกันกี่วันครับ')]
records=[]
for name,text in cases:
    opener=client() if name!='repeat' else previous
    previous=opener
    body,kind=multipart({'input':text})
    code,data=request(opener,'http://127.0.0.1:8081/api/chat',body,kind)
    answer=data.get('answer','')
    checks={'transport':code==200,'rag':data.get('rag_used') is True,'no_demo':all(x not in answer.lower() for x in ['demo','สาธิต'])}
    if name in ('price','repeat'):checks['price']=('3,200' in answer or '3200' in answer) and ('เบื้องต้น' in answer or 'ประเมิน' in answer)
    if name=='repeat':checks['cache']=data.get('cache',{}).get('answer') is True
    if name=='parts':checks['approval']='อนุมัติ' in answer and ('ก่อน' in answer)
    records.append({'case':name,'input':text,'http_status':code,'checks':checks,'observed':data})
p=ROOT/'results/shop-tone-live.json'
p.write_text(json.dumps({'executed_at':datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),'kb_version':'plimo-estimate-v3','prompt_version':'thai-shop-estimate-v4','records':records},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(p),'all_checks':all(all(r['checks'].values()) for r in records),'records':records},ensure_ascii=False))
