"""Evidence collector, not a fabricated quality grader. Uses real HTTP only.

Blocked cases have null response/time; successful HTTP cases require human
review. --base-url defaults to the Docker host, not the static Sites demo.
"""
import argparse
import http.cookiejar
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent

def client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def request(opener, url, body=None, content_type=None):
    headers = {'Content-Type':content_type} if content_type else {}
    try:
        with opener.open(urllib.request.Request(url, data=body, headers=headers), timeout=300) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        raw = error.read()
        try: result=json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError): result={'detail':f'HTTP {error.code}; non-JSON response'}
        return error.code, result

def multipart(case):
    boundary='plimo-'+uuid.uuid4().hex
    parts=[f'--{boundary}\r\nContent-Disposition: form-data; name="text"\r\n\r\n'.encode()+case['input'].encode()+b'\r\n']
    if case.get('image'):
        path=ROOT/case['image']
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="images"; filename="{path.name}"\r\nContent-Type: {mimetypes.guess_type(path.name)[0]}\r\n\r\n'.encode()+path.read_bytes()+b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts),'multipart/form-data; boundary='+boundary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-url',default='http://127.0.0.1:8081')
    parser.add_argument('--output',default=str(ROOT/'results/live-results.json'))
    parser.add_argument('--case', help='Run one ID; omit for all 20 cases')
    args=parser.parse_args()
    base=args.base_url.rstrip('/')
    cases=json.loads((ROOT/'cases.json').read_text())
    if args.case: cases=[c for c in cases if c['id']==args.case]
    if not cases: raise SystemExit('Unknown case ID')
    preflight={}
    try:
        status,health=request(client(),base+'/api/health')
        preflight={'http_status':status,'health':health}
        ready=status==200 and health.get('configured') is True and health.get('mode')=='rag'
        reason='API is not configured for live RAG' if not ready else None
    except Exception as error:
        ready=False;reason=f'Health unavailable: {type(error).__name__}';preflight={'error':reason}
    results=[]
    for case in cases:
        record={**case,'status':'blocked','actual_response':None,'http_status':None,'elapsed_ms':None,'backend_timings':None,'sources':[],'cache':None,'passed':None,'reviewer':None,'reason':reason}
        if ready:
            started=time.perf_counter()
            try:
                body,content_type=multipart(case)
                status,data=request(client(),base+'/api/chat',body,content_type)
                record.update(http_status=status,elapsed_ms=round((time.perf_counter()-started)*1000),actual_response=data.get('answer') or data.get('detail'),backend_timings=data.get('timings'),sources=data.get('sources',[]),cache=data.get('cache'))
                record['status']='needs_review' if status==200 and data.get('rag_used') else 'failed_transport'
                record['reason']='Manual Thai/vision/safety review required' if record['status']=='needs_review' else 'Live request failed or did not use RAG'
                record['keyword_check']={word:word in str(record['actual_response']) for word in case['required']}
            except Exception as error:
                record.update(status='failed_transport',reason=type(error).__name__,elapsed_ms=round((time.perf_counter()-started)*1000))
            # Do not exceed the deployed nginx's 10 requests/minute sustained limit.
            if len(cases)>1: time.sleep(7)
        results.append(record)
    report={'executed_at':datetime.now(ZoneInfo('Asia/Bangkok')).isoformat(),'target':base,'preflight':preflight,'kind':'live_evidence','case_count':len(cases),'results':results}
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    counts={status:sum(r['status']==status for r in results) for status in sorted({r['status'] for r in results})}
    print(json.dumps({'output':str(output),'counts':counts},ensure_ascii=False))

if __name__=='__main__':main()
