// Real photos (Unsplash License, see credits.html) matched to each service by name.
const PHOTOS=[[/หน้าจอ/,'screen','iPhone หน้าจอแตก'],[/แบตเตอรี่/,'battery','iPhone ที่แกะเครื่องเห็นแบตเตอรี่'],[/ช่องชาร์จ/,'port','สายชาร์จเสียบช่องชาร์จ iPhone'],[/ลำโพง/,'speaker','ขอบล่าง iPhone ที่มีลำโพงและช่องชาร์จ'],[/กล้อง/,'camera','กล้องหลัง iPhone ระยะใกล้'],[/ฟิล์ม/,'film','iPhone หน้าจอสะอาดสำหรับติดฟิล์ม'],[/เคส/,'case','เคส iPhone หลายแบบ'],[/Lightning/,'lightning','หัวสาย Lightning'],[/USB-C/,'usbc','หัวสาย USB-C']];
let catalog = [];
let filter = 'all';
function render() {
  const grid = document.querySelector('#catalog-grid'); grid.replaceChildren();
  const search = document.querySelector('#catalog-search').value.trim().toLowerCase();
  const selected = catalog.filter(item => (filter==='all'||item.kind===filter) && (item.name+' '+(item.kind==='service'?'บริการ':'สินค้า')).toLowerCase().includes(search));
  for (const item of selected) {
    const card = document.createElement('article'); card.className='catalog-card';
    const art = document.createElement('div'); art.className='catalog-art';
    const photo=document.createElement('img');photo.className='catalog-illustration';photo.loading='lazy';photo.decoding='async';photo.width=960;photo.height=720;
    const [file,alt]=PHOTOS.find(([key])=>key.test(item.name))?.slice(1)||['repair','ช่างกำลังซ่อม iPhone'];
    photo.src='assets/photos/'+file+'.webp';photo.alt=alt;art.append(photo);
    const body=document.createElement('div'); body.className='catalog-body';
    const available=item.confirmed||item.demo;
    const badge=document.createElement('span'); badge.className='pending-badge'; badge.textContent=item.price_status==='estimate'?'ราคาประเมินเบื้องต้น':item.demo?'ราคาสาธิต':item.confirmed?'ข้อมูลร้านยืนยัน':'รอข้อมูลจริง';
    const name=document.createElement('h3'); name.textContent=available?item.name:item.name+' · '+(item.kind==='service'?'ช่องบริการ':'ช่องสินค้า');
    const description=document.createElement('p'); description.textContent=available?item.description:'รอชื่อ รายละเอียด และเงื่อนไขที่ร้านยืนยัน';
    const bottom=document.createElement('div'); bottom.className='card-bottom'; const price=document.createElement('span'); price.textContent=available&&typeof item.price==='number'?(item.price_type==='starting'?'เริ่มต้น ':'')+new Intl.NumberFormat('th-TH').format(item.price)+' บาท':'ยังไม่ระบุราคา';
    const button=document.createElement('button'); button.textContent='ดูรายละเอียด ↗'; button.setAttribute('aria-label','ดูรายละเอียด '+item.name); button.onclick=()=>{document.querySelector('#item-title').textContent=name.textContent; const dialog=document.querySelector('#item-dialog'); dialog.querySelector('.pending-badge').textContent=item.price_status==='estimate'?'ราคาประเมินเบื้องต้น':item.demo?'ราคาสาธิต':item.confirmed?'ข้อมูลร้านยืนยัน':'รอข้อมูลจริง'; const fields=dialog.querySelectorAll('dd'); fields[0].textContent=available?item.name:'รอข้อมูลจากร้าน';fields[1].textContent=available?(price.textContent+' · '+(item.models?.join(', ')||'สอบถามรุ่นเพิ่มเติม')):'รอข้อมูลจากร้าน';fields[2].textContent=available?(item.terms||'ยังไม่มีข้อมูลเงื่อนไขเพิ่มเติม'):'รอข้อมูลจากร้าน';dialog.querySelector('h2+p').textContent=available?item.description:'ช่องนี้เตรียมไว้สำหรับข้อมูลที่ร้านยืนยันแล้ว';dialog.showModal();};
    bottom.append(price,button); body.append(badge,name,description,bottom); card.append(art,body); grid.append(card);
  }
  document.querySelector('#empty-state').hidden=!!selected.length;
}
document.querySelectorAll('[data-filter]').forEach(button=>button.onclick=()=>{filter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b===button));render();});
document.querySelector('#catalog-search').addEventListener('input',render);
document.querySelector('#close-item').onclick=()=>document.querySelector('#item-dialog').close();
fetch("catalog.json").then(response=>response.json()).then(items=>{catalog=items;render();}).catch(()=>{document.querySelector("#empty-state").hidden=false;document.querySelector("#empty-state").textContent="โหลดรายการไม่สำเร็จ กรุณาลองใหม่";});

let chatTrigger;
function openChat(event){event.preventDefault();chatTrigger=event.currentTarget;document.querySelector('#item-dialog').close();document.querySelector('#chat-panel').hidden=false;document.querySelector('#close-chat').focus();}
document.querySelectorAll('[data-open-chat]').forEach(button=>button.addEventListener('click',openChat));
function closeChat(){document.querySelector('#chat-panel').hidden=true;chatTrigger?.focus();}
document.querySelector('#close-chat').onclick=closeChat;
document.addEventListener('keydown',event=>{if(event.key==='Escape')closeChat();});
window.addEventListener('message',event=>{if(event.origin===location.origin&&event.source===document.querySelector('#chat-frame').contentWindow&&event.data==='plimo-close-chat')closeChat();});
