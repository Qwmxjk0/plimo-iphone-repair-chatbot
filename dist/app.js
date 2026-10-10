const $ = (selector) => document.querySelector(selector);
const input = $('#message'), fileInput = $('#file-input'), send = $('#send');
let files = [], busy = false, generation = 0;
let live = false;
let conversationId=null,loggedMember=false,memberLoading=true;
const memberReady=fetch('/api/auth/me').then(r=>r.ok?r.json():null).then(async data=>{
  loggedMember=!!data?.user;
  if(!loggedMember)return;
  const params=new URLSearchParams(location.search);
  conversationId=params.get('conversation');
  if(!conversationId&&!params.has('new')){
    const response=await fetch('/api/member/conversations');
    if(response.ok)conversationId=(await response.json()).conversations[0]?.id||null;
  }
  if(conversationId){
    const response=await fetch('/api/member/conversations/'+encodeURIComponent(conversationId));
    if(!response.ok){conversationId=null;throw new Error('เปิดประวัติแชทไม่ได้');}
    const history=(await response.json()).messages;
    if(history.length){$('#welcome').hidden=true;$('#messages').hidden=false;history.forEach(m=>message(m.role,m.content));}
  }
}).catch(()=>{conversationId=null;}).finally(()=>{memberLoading=false;update();});
let demoCatalog=[];
const catalogReady=fetch('catalog.json').then(r=>r.ok?r.json():[]).then(items=>{demoCatalog=items.filter(i=>i.demo===true);}).catch(()=>{});
const ready = fetch('/api/health').then(r => r.ok ? r.json() : null).then(data => {
  live = data?.configured === true;
  if (live) $('.composer-note').textContent = 'ผู้ช่วยใช้ข้อมูลร้านและราคาสาธิต · ภาพใช้ประเมินเบื้องต้น';
}).catch(() => { live = false; });
const objectUrls = new Set();
function imageUrl(file) { const url = URL.createObjectURL(file); objectUrls.add(url); return url; }
function error(message = '') { $('#error').textContent = message; $('#error').hidden = !message; }
function update() {
  send.disabled = busy || memberLoading || (!input.value.trim() && !files.length);
  input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 125) + 'px';
}
function renderAttachments() {
  const box = $('#attachments');
  box.querySelectorAll('img').forEach(img => { URL.revokeObjectURL(img.src); objectUrls.delete(img.src); });
  box.replaceChildren(); box.hidden = !files.length;
  files.forEach((file, i) => {
    const item = document.createElement('div'); item.className = 'attachment';
    const img = document.createElement('img'); img.src = imageUrl(file); img.alt = file.name;
    const remove = document.createElement('button'); remove.className = 'remove-image'; remove.textContent = '×'; remove.setAttribute('aria-label', 'นำภาพ ' + file.name + ' ออก');
    remove.onclick = () => { files.splice(i, 1); renderAttachments(); update(); };
    item.append(img, remove); box.append(item);
  });
}
async function acceptFiles(incoming) {
  const errors = [];
  for (const file of incoming) {
    if (files.length >= 3) { errors.push('แนบได้สูงสุด 3 ภาพต่อข้อความ'); break; }
    if (!['image/jpeg','image/png','image/webp'].includes(file.type)) { errors.push('รองรับ JPG, PNG และ WebP กรุณาแปลง HEIC เป็น JPG ก่อน'); continue; }
    if (file.size > 10 * 1024 * 1024) { errors.push('แต่ละภาพต้องมีขนาดไม่เกิน 10 MB'); continue; }
    try { const bitmap = await createImageBitmap(file); bitmap.close(); files.push(file); }
    catch { errors.push('เปิดภาพนี้ไม่ได้ กรุณาเลือกภาพใหม่'); }
  }
  error([...new Set(errors)].join(' · ')); renderAttachments(); update();
}
fileInput.addEventListener('change', async () => { await acceptFiles([...fileInput.files]); fileInput.value = ''; });
$('#attach').onclick = $('#photo-guide').onclick = () => fileInput.click();
input.addEventListener('input', update);
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); submit(); } });
input.addEventListener('paste', e => { const pasted = [...e.clipboardData.files]; if (pasted.length) { e.preventDefault(); acceptFiles(pasted); } });
const composer = $('.composer');
composer.addEventListener('dragover', e => e.preventDefault());
composer.addEventListener('drop', e => { e.preventDefault(); acceptFiles([...e.dataTransfer.files]); });
function message(role, text, images = []) {
  const row = document.createElement('article'); row.className = 'message ' + role + '-message';
  if (role === 'assistant') {
    const label = document.createElement('div'); label.className = 'assistant-label';
    const avatar = document.createElement('span'); avatar.className = 'assistant-avatar'; avatar.textContent = 'p';
    label.append(avatar, document.createTextNode('ผู้ช่วย Plimo')); row.append(label);
  }
  if (images.length) {
    const gallery = document.createElement('div'); gallery.className = 'message-images';
    images.forEach(file => { const img = document.createElement('img'); img.src = imageUrl(file); img.alt = file.name; gallery.append(img); }); row.append(gallery);
  }
  if (text) { const bubble = document.createElement('div'); bubble.className = 'bubble'; bubble.textContent = text; row.append(bubble); }
  $('#messages').append(row); scrollToEnd(); return row;
}
function scrollToEnd() { const area = $('.workspace'); area.scrollTop = area.scrollHeight; }
function demoReply(text, imageCount) {
  if (imageCount) return 'ได้รับภาพ ' + imageCount + ' ภาพแล้วครับ\n\nตอนนี้เป็นโหมดสาธิตหน้าเว็บ จึงยังไม่ได้วิเคราะห์ภาพด้วย AI กรุณาระบุรุ่น iPhone และเล่าอาการเพิ่มเติมได้เลยครับ\n\nPlimo รับ iPhone 11–17 รวม Pro / Pro Max และตรวจเช็คฟรีที่ร้าน';
  if (/เปิด|ปิด|กี่โมง|เวลา|พุธ|เช็คฟรี/.test(text)) return 'ร้านเปิด 10:00–20:00 น. ทุกวัน ยกเว้นวันพุธครับ\n\nตรวจเช็คฟรีที่ร้าน และรับซ่อม iPhone 11–17 รวม Pro / Pro Max';
  if (/ประกัน|ส่วนลด/.test(text)) return 'ยังไม่มีเงื่อนไขรับประกันหรือส่วนลดที่ร้านยืนยันครับ ราคาในแค็ตตาล็อกเป็นข้อมูลสาธิตเท่านั้น';
  if (/ราคา|เท่าไร|เท่าไหร่|บาท|หน้าจอ|แบตเตอรี่|สายชาร์จ|ฟิล์ม|เคส|สินค้า|บริการ/.test(text)) {
    if (/จอง|ซื้อเลย|ชำระ/.test(text)) return 'รายการและราคาเป็นข้อมูลสาธิตครับ ยังรับจองหรือชำระเงินไม่ได้ ต้องยืนยันกับร้านก่อน';
    if (/pro|โปร/i.test(text)) return 'ราคาในรายการหน้าจอและแบตเตอรี่ตัวอย่างระบุเฉพาะรุ่นปกติครับ ยังไม่มีราคาสาธิตเฉพาะ Pro / Pro Max ต้องสอบถามร้านเพื่อยืนยันราคา';
    const model=text.match(/(?:iphone|ไอโฟน)\s*(1[1-7])/i)?.[1];
    const term=['หน้าจอ','แบตเตอรี่','สายชาร์จ','ฟิล์ม','เคส','กล้อง','ลำโพง','ช่องชาร์จ'].find(t=>text.includes(t));
    const matches=demoCatalog.filter(i=>(!term||i.name.includes(term))&&(!model||i.models.some(m=>m==='iPhone '+model||m.includes('11–17'))));
    if (!matches.length) return 'ยังไม่มีรายการและราคาสาธิตที่ตรงกับคำถามครับ กรุณาระบุรุ่นและบริการ หรือสอบถามร้านเพื่อขอราคาจริง';
    return 'ราคาต่อไปนี้เป็นข้อมูลสาธิต ไม่ใช่ราคาเสนอจริงจากร้านครับ\n\n'+matches.map(i=>i.name+' · '+(i.price_type==='starting'?'เริ่มต้น ':'')+new Intl.NumberFormat('th-TH').format(i.price)+' บาท').join('\n')+'\n\nราคาสาธิต ต้องยืนยันรุ่น อาการ เงื่อนไข และราคากับร้านก่อน ไม่มีการจองหรือชำระเงินในเว็บนี้';
  }
  return 'แจ้งรุ่น iPhone และอาการที่พบได้เลยครับ ถ้ามีภาพตัวเครื่อง หน้าจอ หรือข้อความแจ้งเตือน สามารถกด + เพื่อแนบภาพได้\n\nPlimo รับ iPhone 11–17 รวม Pro / Pro Max และตรวจเช็คฟรีที่ร้าน\n\nนี่เป็นคำตอบสาธิต ยังไม่ได้ตรวจสอบอาการด้วย AI ครับ';
}
async function submit() {
  if (busy || memberLoading || (!input.value.trim() && !files.length)) return;
  const text = input.value.trim(), images = [...files], turn = generation;
  busy = true; $('#welcome').hidden = true; $('#messages').hidden = false;
  message('user', text, images); input.value = ''; files = []; renderAttachments(); error(); update();
  const loading = document.createElement('div'); loading.className = 'typing'; loading.setAttribute('role','status'); loading.textContent = 'กำลังเตรียมคำตอบ'; $('#messages').append(loading); scrollToEnd();
  try {
    await ready;
    await memberReady;
    let result;
    if (live) {
      loading.textContent = images.length ? 'กำลังดูภาพและค้นข้อมูลร้าน' : 'กำลังค้นข้อมูลร้าน';
      const form = new FormData(); form.append('text', text); images.forEach(file => form.append('images', file));
      if(loggedMember&&conversationId)form.append('conversation_id',conversationId);
      const response = await fetch('/api/chat', {method:'POST',body:form,signal:AbortSignal.timeout(290000)});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'ส่งคำถามไม่สำเร็จ กรุณาลองใหม่');
      result = data;
      if(loggedMember)conversationId=data.conversation_id||conversationId;
    } else {
      loading.textContent = 'กำลังเตรียมคำตอบสาธิต';
      await new Promise(resolve => setTimeout(resolve, 850));
      await catalogReady;
      result = {answer:demoReply(text, images.length),sources:[]};
    }
    if (turn !== generation) return;
    loading.remove(); const reply = message('assistant', result.answer);
    const source = document.createElement('p'); source.className = 'message-source';
    source.textContent = live ? (result.sources.length ? 'อ้างอิง: '+result.sources.map(s=>s.label.endsWith('shop.md')?'ข้อมูลร้าน Plimo':s.label.includes('demo-slot-')?'รายการและราคาสาธิต':'เอกสารอ้างอิง').join(' · ') : 'ยังไม่พบข้อมูลที่ยืนยัน') : 'โหมดสาธิต · ยังไม่ได้เชื่อมผู้ช่วย AI';
    reply.append(source);
  } catch (err) {
    if (turn !== generation) return;
    loading.remove(); input.value=text; files=images; renderAttachments();
    error(err.name === 'TimeoutError' ? 'ใช้เวลาตอบนานเกินไป กรุณาลองใหม่' : err.message);
  } finally { if (turn === generation) {busy=false;update();scrollToEnd();} }
}
send.onclick = submit;
document.querySelectorAll('[data-question]').forEach(button => { button.onclick = () => { if (busy) return; input.value = button.dataset.question; update(); submit(); }; });
$('#new-chat').onclick = () => {
  conversationId=null;
  generation++; busy = false; files = []; input.value = ''; $('#messages').replaceChildren(); $('#messages').hidden = true; $('#welcome').hidden = false;
  objectUrls.forEach(url => URL.revokeObjectURL(url)); objectUrls.clear(); renderAttachments(); error(); update(); input.focus();
  if (live) {busy=true;update();fetch('/api/session/new',{method:'POST'}).catch(()=>error('เริ่มบทสนทนาใหม่ไม่สำเร็จ กรุณาโหลดหน้าอีกครั้ง')).finally(()=>{busy=false;update();});}
};
$('#mobile-new').onclick = () => $('#new-chat').click();
$('#store-info').onclick = () => $('#info-dialog').showModal();
$('.dialog-close').onclick = () => $('#info-dialog').close();
$('#info-dialog').addEventListener('click', e => { if (e.target === e.currentTarget) { const r = e.currentTarget.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.currentTarget.close(); } });
window.addEventListener('beforeunload', () => objectUrls.forEach(url => URL.revokeObjectURL(url)));
document.addEventListener('keydown', event => {if(event.key==='Escape'&&!$('#info-dialog').open)parent.postMessage('plimo-close-chat',location.origin);});
update();
const caseButton=document.createElement('button');caseButton.type='button';caseButton.className='chat-case-button';caseButton.textContent='ส่งเคสซ่อม';caseButton.onclick=()=>{if(busy)return;parent.postMessage({type:'plimo-case',conversation_id:conversationId},location.origin);};$('.composer-note').before(caseButton);
