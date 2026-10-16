const statusNames={submitted:'ส่งเคสแล้ว',received:'ร้านรับเรื่อง',checking:'กำลังตรวจเช็ค',awaiting_approval:'รออนุมัติราคา',repairing:'กำลังซ่อม',ready:'พร้อมรับเครื่อง',closed:'ปิดเคส',cancelled:'ยกเลิก'};
let memberUser=null,memberBackend=true,selectedConversation=null;
const md=document.querySelector('#member-dialog'),mb=document.querySelector('#member-body'),me=document.querySelector('#member-error');
function node(tag,text='',className=''){const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e;}
async function memberApi(path,method='GET',body){const r=await fetch('/api'+path,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});let d;try{d=await r.json();}catch{throw new Error('ระบบสมาชิกใช้งานผ่านเว็บ local เท่านั้น');}if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'ข้อมูลไม่ถูกต้อง กรุณาตรวจช่องกรอก');return d;}
function fail(err){me.textContent=err.message||'โหลดข้อมูลไม่สำเร็จ';}
function field(form,label,type='text',required=true){const l=node('label',label),i=document.createElement(type==='textarea'?'textarea':'input');if(type!=='textarea')i.type=type;i.required=required;l.append(i);form.append(l);return i;}
function action(text,fn){const b=node('button',text,'member-action');b.type='button';b.onclick=fn;return b;}
function resetMemberChat(cid=null){const frame=document.querySelector('#chat-frame');if(frame)frame.src='chat.html?widget=1'+(cid?'&conversation='+encodeURIComponent(cid):'&new=1');}
function updateMemberButton(){document.querySelector('#member-open').textContent=memberUser?'บัญชี · '+memberUser.name:'เข้าสู่ระบบ';}
function memberTabs(active){
 const toolbar=node('div','','member-toolbar'),t=node('nav','','member-tabs');t.setAttribute('aria-label','เมนูบัญชีสมาชิก');
 for(const [key,label] of [['cases','งานซ่อมของฉัน'],['history','ประวัติแชท'],['new','ส่งเคสใหม่']]){const b=action(label,()=>showMember(key));b.classList.toggle('active',active===key);b.setAttribute('aria-current',active===key?'page':'false');t.append(b);}
 const utilities=node('div','','member-utilities');if(memberUser.role==='admin'){const a=node('a','หน้า Admin','member-action');a.href='admin.html';utilities.append(a);}
 utilities.append(action('ออกจากระบบ',async()=>{try{await memberApi('/auth/logout','POST');memberUser=null;selectedConversation=null;resetMemberChat();updateMemberButton();authForm();}catch(e){fail(e);}}));toolbar.append(t,utilities);return toolbar;
}
function authForm(register=false){md.dataset.view='auth';me.textContent='';mb.replaceChildren();if(!memberBackend){mb.append(node('p','ระบบสมาชิกและเคสใช้งานบนเว็บ local ที่เชื่อม backend ครับ','member-hint'));const a=node('a','เปิดเว็บ local','member-action');a.href='http://127.0.0.1:8081/';mb.append(a);return;}
 const tabs=node('div','','member-tabs');tabs.append(action('เข้าสู่ระบบ',()=>authForm(false)),action('สมัครสมาชิก',()=>authForm(true)));tabs.children[register?1:0].classList.add('active');mb.append(tabs);
 const form=node('form','','member-form'),name=register?field(form,'ชื่อที่แสดง'):null,user=field(form,'ชื่อบัญชี (a-z และ 0-9)'),password=field(form,'รหัสผ่านอย่างน้อย 10 ตัว','password');user.autocomplete='username';user.maxLength=32;password.minLength=10;password.maxLength=128;password.autocomplete=register?'new-password':'current-password';if(name)name.maxLength=64;
 form.append(node('p','บัญชีสมาชิก เก็บข้อความแชท รูปตัวเครื่อง และสลิปแบบส่วนตัวเพื่อดูย้อนหลังและใช้ประกอบเคส','member-hint'));const submit=node('button',register?'สมัครสมาชิก':'เข้าสู่ระบบ');submit.type='submit';form.append(submit);form.onsubmit=async e=>{e.preventDefault();submit.disabled=true;me.textContent='';try{const d=await memberApi(register?'/auth/register':'/auth/login','POST',{username:user.value,password:password.value,name:name?.value||''});memberUser=d.user;selectedConversation=null;resetMemberChat();updateMemberButton();showMember('cases');}catch(err){fail(err);}finally{submit.disabled=false;}};mb.append(form);
}
async function showMember(tab='cases'){
 md.dataset.view=tab;me.textContent='';mb.replaceChildren(memberTabs(tab),node('p','กำลังโหลด…','member-hint'));
 try{
 const head=memberTabs(tab);mb.replaceChildren(head);
 if(tab==='cases'){
   const d=await memberApi('/member/cases');
   if(memberUser?.role==='admin'){
     // Admins see every customer's case on the admin page; this tab lists only cases the account itself owns.
     const note=node('div','','admin-note');note.append(node('strong','คุณเข้าสู่ระบบในฐานะผู้ดูแลร้าน'),node('p','เคสของลูกค้าทุกคนอยู่ที่หน้า Admin แท็บนี้แสดงเฉพาะเคสที่บัญชีนี้ส่งเอง'));
     const go=node('a','ไปหน้า Admin','member-action primary');go.href='admin.html';note.append(go);mb.append(note);
     if(!d.cases.length)return;
   }
   if(!d.cases.length){mb.append(node('p','ยังไม่มีเคส กดส่งเคสใหม่เพื่อเริ่มต้น','member-hint'));return;}
   const intro=node('div','','member-section-title');intro.append(node('h3','งานซ่อมของฉัน'),node('span',d.cases.length+' เคส'));mb.append(intro);
   const list=node('div','','member-list');for(const c of d.cases){
     const row=node('article','','member-row'),heading=node('div','','case-heading');heading.append(node('strong',c.reference+' · '+c.model),node('span',c.status==='awaiting_approval'&&c.quote?.status==='approved'?'รอร้านเริ่มซ่อม':statusNames[c.status],'status-badge'));row.append(heading,node('p',c.issue,'case-issue'));
     if(c.quoted_price!==null)row.append(node('p','ราคาเสนอ: '+Number(c.quoted_price).toLocaleString('th-TH')+' บาท','case-quote'));
     if(c.quote){
       const quote=c.quote,labels={pending:'รอการตัดสินใจ',approved:'อนุมัติแล้ว',rejected:'ปฏิเสธแล้ว',superseded:'มีใบเสนอใหม่'};
       row.append(node('p','ใบเสนอ #'+quote.id+' · '+labels[quote.status],'quote-state'));
       if(c.status==='awaiting_approval'&&quote.status==='pending'){
         const form=node('form','','quote-decision'),label=node('label','ตอบรับราคาเสนอ '+Number(quote.amount).toLocaleString('th-TH')+' บาท'),select=node('select');
         for(const [value,text] of [['','เลือกการตัดสินใจ'],['approve','อนุมัติราคานี้'],['reject','ปฏิเสธ / ขอประเมินใหม่']]){const option=node('option',text);option.value=value;select.append(option);}select.required=true;label.append(select);form.append(label);
         const note=field(form,'หมายเหตุ (ไม่จำเป็น)','text',false);note.maxLength=1000;form.append(node('p','การอนุมัติครอบคลุมใบเสนอราคานี้เท่านั้น หากมีค่าใช้จ่ายเพิ่ม ร้านต้องส่งราคาใหม่ให้คุณอนุมัติก่อนเริ่มซ่อม ยังไม่มีการชำระเงินผ่านเว็บไซต์','member-hint'));
         const submit=node('button','ยืนยันคำตอบ','member-action primary');submit.type='submit';form.append(submit);form.onsubmit=async e=>{e.preventDefault();submit.disabled=true;me.textContent='';try{await memberApi('/member/cases/'+c.id+'/quote-decision','POST',{quote_id:quote.id,decision:select.value,note:note.value});await showMember('cases');}catch(err){fail(err);submit.disabled=false;}};row.append(form);
       }else if(quote.status==='approved'&&c.status==='awaiting_approval')row.append(node('p','รอร้านเริ่มซ่อมตามราคาที่คุณอนุมัติ','member-hint'));
     }
     if(c.payment?.status==='paid')row.append(node('p','ชำระแล้ว '+Number(c.payment.amount).toLocaleString('th-TH')+' บาท (Stripe โหมดทดสอบ)','payment-paid'));
     else if(c.can_pay&&d.payments_enabled){
       const pay=action('ชำระเงิน '+Number(c.quote.amount).toLocaleString('th-TH')+' บาท (โหมดทดสอบ)',async()=>{pay.disabled=true;me.textContent='';try{const r=await memberApi('/member/cases/'+c.id+'/checkout','POST');const u=new URL(r.url);if(u.protocol!=='https:'||u.hostname!=='checkout.stripe.com')throw new Error('ลิงก์ชำระเงินไม่ถูกต้อง');location.assign(u.href);}catch(err){fail(err);pay.disabled=false;}});
       pay.classList.add('pay-action');row.append(pay,node('p','โหมดทดสอบ ไม่มีการตัดเงินจริง ใช้บัตรทดสอบ 4242 4242 4242 4242 วันหมดอายุในอนาคต และ CVC ใดก็ได้','member-hint'));
     }
     const details=node('details','','case-history'),summary=node('summary','ประวัติสถานะ'),timeline=node('ol','','case-timeline');details.append(summary,timeline);let loaded=false;
     details.addEventListener('toggle',async()=>{if(!details.open||loaded)return;loaded=true;timeline.replaceChildren(node('li','กำลังโหลด…','member-hint'));try{const detail=await memberApi('/member/cases/'+c.id);timeline.replaceChildren();for(const ev of detail.events){const item=node('li'),line=node('div','','timeline-heading'),date=node('time',new Date(ev.created*1000).toLocaleString('th-TH'));date.dateTime=new Date(ev.created*1000).toISOString();line.append(node('strong',statusNames[ev.status]),date);item.append(line,node('p',ev.note));timeline.append(item);}}catch(e){loaded=false;timeline.replaceChildren(node('li','โหลดประวัติไม่สำเร็จ กรุณาปิดแล้วเปิดอีกครั้ง','member-hint'));fail(e);}});
     row.append(details);list.append(row);
   }mb.append(list);
 }else if(tab==='history'){
   const d=await memberApi('/member/conversations');if(!d.conversations.length)mb.append(node('p','แชทหลังเข้าสู่ระบบจะปรากฏที่นี่','member-hint'));
   const list=node('div','','conv-list');
   for(const c of d.conversations){const row=node('article','','member-row conv-row'),info=node('div','','conv-info'),buttons=node('div','','row-actions');
     info.append(node('strong',c.title),node('small',new Date(c.updated*1000).toLocaleString('th-TH',{dateStyle:'medium',timeStyle:'short'})));
     const open=action('เปิดบทสนทนา',()=>{selectedConversation=c.id;resetMemberChat(c.id);md.close();document.querySelector('#chat-panel').hidden=false;window.syncFloating?.();});open.classList.add('primary');
     buttons.append(open,action('ใช้ส่งเคส',()=>{selectedConversation=c.id;showMember('new');}));row.append(info,buttons);list.append(row);}
   mb.append(list);
 }else{
   mb.append(node('p','ส่งคำขอให้ร้านตรวจสอบก่อน การส่งคำขอยังไม่ยืนยันว่าร้านได้รับเครื่องหรือรับนัดหมายแล้ว','member-hint'));
   if(selectedConversation)mb.append(node('p','แนบบทสนทนาที่เลือกแล้ว ผู้ดูแลจะอ่านได้เมื่อเปิดเคสนี้','member-hint'));
   const form=node('form','','member-form'),label=node('label','รุ่น iPhone'),model=document.createElement('select');for(let n=11;n<=17;n++)for(const suffix of ['', ' Pro',' Pro Max']){const o=node('option','iPhone '+n+suffix);o.value=o.textContent;model.append(o);}label.append(model);form.append(label);
   const issue=field(form,'อาการ / รายละเอียด','textarea');issue.minLength=5;issue.maxLength=2000;const b=node('button','ส่งเคส');b.type='submit';form.append(b);form.onsubmit=async e=>{e.preventDefault();b.disabled=true;try{await memberApi('/member/cases','POST',{model:model.value,issue:issue.value,conversation_id:selectedConversation});selectedConversation=null;await showMember('cases');}catch(err){fail(err);}finally{b.disabled=false;}};mb.append(form);
 }
 }catch(e){fail(e);}
}
document.querySelector('#member-open').onclick=async()=>{md.showModal();me.textContent='';try{memberUser=(await memberApi('/auth/me')).user;memberBackend=true;updateMemberButton();memberUser?showMember():authForm();}catch(e){memberBackend=false;authForm();}};
document.querySelector('#member-close').onclick=()=>md.close();
memberApi('/auth/me').then(d=>{memberUser=d.user;updateMemberButton();}).catch(()=>{memberBackend=false;});
window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===document.querySelector('#chat-frame')?.contentWindow&&event.data?.type==='plimo-case'){selectedConversation=event.data.conversation_id||null;md.showModal();memberUser?showMember('new'):authForm();}});

// Return from Stripe Checkout: confirm on the server (never trust the redirect alone), then clean the URL.
(async()=>{const q=new URLSearchParams(location.search),state=q.get('payment');if(!state)return;const sid=q.get('session_id');history.replaceState(null,'',location.pathname);md.showModal();me.textContent='';
 try{memberUser=(await memberApi('/auth/me')).user;updateMemberButton();if(!memberUser){authForm();me.textContent='กรุณาเข้าสู่ระบบเพื่อดูผลการชำระเงิน';return;}
  let message='ยกเลิกการชำระเงินแล้ว ชำระใหม่ได้ภายหลัง',ok=false;
  if(state==='success'&&sid){const r=await memberApi('/member/payments/confirm?session_id='+encodeURIComponent(sid));ok=r.status==='paid';message=ok?'ชำระเงินสำเร็จ '+r.reference+' (โหมดทดสอบ)':'ยังไม่ได้รับการยืนยันการชำระเงิน กรุณาตรวจสอบอีกครั้งภายหลัง';}
  await showMember('cases');mb.prepend(node('p',message,ok?'payment-banner ok':'payment-banner'));
 }catch(e){fail(e);}})();
