const $=s=>document.querySelector(s),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let P=[],CFG={},cat='All',cart=JSON.parse(localStorage.getItem('cart')||'{}');
const save=()=>{localStorage.setItem('cart',JSON.stringify(cart));render()};
const lines=()=>Object.entries(cart).map(([id,q])=>({p:P.find(x=>x.id==id),q})).filter(l=>l.p);
const total=()=>lines().reduce((s,l)=>s+l.p.price*l.q,0);
const wa=(ls,extra='')=>`https://wa.me/${CFG.whatsapp}?text=`+encodeURIComponent(`Hello Cakewala! I'd like to order:\n`+ls.map(l=>`• ${l.p.name} x${l.q} ${l.p.unit} = ₹${l.p.price*l.q}`).join('\n')+`\nTotal: ₹${ls.reduce((s,l)=>s+l.p.price*l.q,0)}${extra}`);
function render(){
 const q=$('#q').value.toLowerCase(),cats=['All',...new Set(P.map(p=>p.category))];
 $('#cats').innerHTML=cats.map(c=>`<button class="chip ${c==cat?'on':''}" data-c="${esc(c)}">${esc(c)}</button>`).join('');
 $('#grid').innerHTML=P.filter(p=>(cat=='All'||p.category==cat)&&(p.name+p.description).toLowerCase().includes(q)).map(p=>`<article class="card"><img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy"><div class="b"><h3>${esc(p.name)}</h3><p>${esc(p.description)}</p><b>₹${p.price}/${esc(p.unit)}</b> · <small>${p.is_available?'Available':'Sold out'}</small><div class="row"><button data-add="${p.id}" ${p.is_available?'':'disabled'}>Add to cart</button><button class="wa" data-wa="${p.id}" ${p.is_available?'':'disabled'}>WhatsApp</button></div></div></article>`).join('');
 $('#cnt').textContent=Object.values(cart).reduce((a,b)=>a+b,0);
 if($('#dlg').open&&!$('#done'))cartView();
}
function cartView(){
 const ls=lines();
 if(!ls.length){$('#cartBody').innerHTML='<h3>Your cart is empty</h3>';return}
 const t=new Date().toISOString().slice(0,10);
 $('#cartBody').innerHTML='<h3>Your cart</h3>'+ls.map(l=>`<div class="ln"><span>${esc(l.p.name)}</span><span><button data-m="${l.p.id}">−</button> ${l.q} <button data-p="${l.p.id}">+</button> <button data-r="${l.p.id}">✕</button></span><b>₹${l.p.price*l.q}</b></div>`).join('')+
 `<h3>Total: ₹${total()}</h3><a class="btn wa" target="_blank" rel="noopener" href="${wa(ls)}">Order on WhatsApp</a><hr><h4>Checkout</h4><form id="f"><input name="name" placeholder="Your name" required><input name="phone" placeholder="Mobile number" required inputmode="tel"><textarea name="address" placeholder="Delivery address" required></textarea><input type="date" name="delivery_date" min="${t}" required><input type="time" name="delivery_time" required><select name="payment_method"><option value="COD">Cash on Delivery</option><option value="UPI">UPI (pay manually; shop confirms)</option></select><textarea name="notes" placeholder="Notes (e.g. message on cake)"></textarea><button>Place order</button><p id="err" style="color:#b00"></p></form>`;
}
document.addEventListener('click',e=>{const d=e.target.dataset;if(!d)return;
 if(d.c){cat=d.c;render()}
 if(d.add){cart[d.add]=(cart[d.add]||0)+1;save()}
 if(d.p){cart[d.p]++;save()}
 if(d.m){cart[d.m]--;if(cart[d.m]<1)delete cart[d.m];save()}
 if(d.r){delete cart[d.r];save()}
 if(d.wa)open(wa([{p:P.find(x=>x.id==d.wa),q:1}]),'_blank','noopener');
 if(e.target.id=='cartBtn'||e.target.closest('#cartBtn')){e.preventDefault();cartView();$('#dlg').showModal()}});
$('#q').oninput=render;
document.addEventListener('submit',async e=>{e.preventDefault();const f=Object.fromEntries(new FormData(e.target));
 f.items=lines().map(l=>({id:l.p.id,quantity:l.q}));
 const r=await fetch('/api/orders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(f)}),o=await r.json();
 if(!r.ok){$('#err').textContent='Please check: '+(o.fields||[o.error]).join(', ');return}
 cart={};localStorage.removeItem('cart');
 $('#cartBody').innerHTML=`<div id="done"><h3>Order received ✅</h3><p>Order number: <b>${esc(o.order_number)}</b><br>Total: ₹${o.total_amount} · ${esc(o.payment_method)}<br>Status: ${esc(o.order_status)} (payment: ${esc(o.payment_status)}). We'll confirm shortly.</p><a class="btn wa" target="_blank" rel="noopener" href="https://wa.me/${CFG.whatsapp}?text=${encodeURIComponent('Hi, my order number is '+o.order_number)}">Message us on WhatsApp</a></div>`;render()});
(async()=>{CFG=await (await fetch('/api/config')).json();P=await (await fetch('/api/products')).json();
 $('#waContact').href=`https://wa.me/${CFG.whatsapp}`;render()})();
