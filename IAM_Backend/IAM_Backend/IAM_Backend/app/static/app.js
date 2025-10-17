// app.js — Panel por roles + perfil + temporizador

const authOk  = localStorage.getItem('auth_ok') === 'true';
const authExp = parseInt(localStorage.getItem('auth_expires') || '0', 10);
const uid     = localStorage.getItem('uid') || sessionStorage.getItem('uid');

if (!authOk || !authExp || Date.now() > authExp) {
  location.replace('login.html'); // sesión no válida
}

const $ = (s)=>document.querySelector(s);
const expiresEl = $('#expires');
const nameEl = $('#name');
const emailEl = $('#email');
const roleEl = $('#role');
const avatarEl = $('#avatar');
const cornerName = document.getElementById('cornerName');
const cornerAvatar = document.getElementById('cornerAvatar');

function tickExp(){
  const s = Math.max(0, Math.floor((authExp - Date.now())/1000));
  const mm = String(Math.floor(s/60)).padStart(2,'0');
  const ss = String(s%60).padStart(2,'0');
  expiresEl.textContent = `${mm}:${ss}`;
  if (s<=0) {
    localStorage.clear(); sessionStorage.clear();
    location.replace('login.html?msg=timeout');
  }
}
setInterval(tickExp, 1000); tickExp();

async function getJSON(url){
  const r = await fetch(url);
  if(!r.ok) throw new Error((await r.json().catch(()=>({detail:'error'}))).detail || 'error');
  return r.json();
}

// Perfil
async function loadMe(){
  const me = await getJSON(`/api/users/me?uid=${encodeURIComponent(uid)}`);
  nameEl.textContent  = `${me.nombre||''} ${me.apellido||''}`.trim() || me.uid;
  emailEl.textContent = me.email || '';
  roleEl.textContent  = me.rol || '-';
  avatarEl.src        = me.foto_url || 'avatar.png';
  if (cornerName) cornerName.textContent = (nameEl.textContent || me.uid);
  if (cornerAvatar) cornerAvatar.src = avatarEl.src;
  applyRole(me.rol);
  loadSections(me.rol);
}

// Tabs
function applyRole(role){
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(t => t.addEventListener('click', () => {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.getElementById(t.dataset.target).classList.add('active');
    t.classList.add('active');
  }));

  const hideTab = (id)=>{
    const tab = Array.from(tabs).find(x => x.dataset.target === id);
    const sec = document.getElementById(id);
    if (tab) tab.style.display = 'none';
    if (sec) sec.style.display = 'none';
  };

  if (role === 'R-ADM') {
    // full access
  } else if (role === 'R-MON') {
    hideTab('sec-db'); hideTab('sec-ac');
  } else if (role === 'R-IM') {
    hideTab('sec-cams'); hideTab('sec-logs'); hideTab('sec-ac');
  } else if (role === 'R-AC') {
    hideTab('sec-cams'); hideTab('sec-logs'); hideTab('sec-db');
  } else {
    hideTab('sec-cams'); hideTab('sec-logs'); hideTab('sec-db'); hideTab('sec-ac');
  }

  const first = Array.from(document.querySelectorAll('.tab')).find(x => x.style.display !== 'none');
  if (first) first.click();
}

// Carga de secciones
async function loadSections(role){
  try{
    if (role === 'R-ADM' || role === 'R-MON') {
      // Cargar lista de cámaras y mostrarlas en grid 2x2 con paginación y fallback "No Signal"
      try{
        const cams = await getJSON('/cameras');
        const PAGE = 4; let page = 0;
        const total = Math.max(PAGE, (cams||[]).length);
        const pages = Math.ceil(total / PAGE);
        const grid = document.getElementById('cams-grid');
        const info = document.getElementById('camsInfo');
        const prev = document.getElementById('camsPrev');
        const next = document.getElementById('camsNext');
        const render = () => {
          const items = [];
          for (let i=0;i<PAGE;i++){
            const idx = page*PAGE + i;
            const c = (cams && cams[idx]) || {name:`Cam ${idx+1}`, url:''};
            const usingImg = c.url && (c.url.startsWith('/camera_mjpeg') || c.url.endsWith('.mjpg'));
            items.push(`
              <div class=\"cam\">
                <div class=\"title\">${c.name||`Cam ${idx+1}`}</div>
                ${usingImg ? `<img src=\"${c.url}\" onload=\"this.nextElementSibling.style.display='none'\" onerror=\"this.nextElementSibling.style.display='flex'\">`
                           : c.url ? `<iframe src=\"${c.url}\" onload=\"this.nextElementSibling.style.display='none'\"></iframe>`
                                   : `<div style=\"width:100%;height:220px\"></div>`}
                <div class=\"nosignal\">NO SIGNAL</div>
              </div>`);
          }
          grid.innerHTML = items.join('');
          info.textContent = `Página ${page+1} de ${pages}`;
          prev.disabled = page<=0; next.disabled = page>=pages-1;
        };
        prev.onclick = ()=>{ if(page>0){page--; render();}};
        next.onclick = ()=>{ if(page<pages-1){page++; render();}};
        render();
      }catch{}

      const logs = await getJSON(`/api/logs?uid=${encodeURIComponent(uid)}`);
      const box = document.getElementById('logs');
      box.innerHTML = logs.length ? logs.map(e => `
        <div style="padding:6px 0;border-bottom:1px solid #e5e7eb">
          <b>${e.tipo}</b> · <span class="muted">${e.created_at}</span> · actor: ${e.actor_uid} · src: ${e.source}
        </div>`).join('') : 'Sin eventos.';
    }
    if (role === 'R-ADM' || role === 'R-IM') {
      const dbdata = await getJSON(`/api/db/all?uid=${encodeURIComponent(uid)}`);

      const uBody = document.getElementById('db-users');
      uBody.innerHTML = (dbdata.usuarios||[]).map(u => `
        <tr>
          <td>${u.uid||''}</td>
          <td>${u.nombre||''}</td>
          <td>${u.apellido||''}</td>
          <td>${u.email||''}</td>
          <td>${u.rol||''}</td>
          <td>${u.estado||''}</td>
          <td>${u.qr_status||''}</td>
          <td>${u.qr_card_id||''}</td>
          <td>${u.ultimo_acceso||''}</td>
        </tr>`).join('');

      const sBody = document.getElementById('db-sessions');
      sBody.innerHTML = (dbdata.auth_sessions||[]).map(s => `
        <tr>
          <td style="font-family:monospace">${s.session_id}</td>
          <td>${s.uid||''}</td>
          <td>${s.state||''}</td>
          <td>${s.created_at||''}</td>
          <td>${s.expires_at||''}</td>
        </tr>`).join('');

      const eBody = document.getElementById('db-events');
      const fmtCtx = (c)=>{
        try{ return c? JSON.stringify(c):''; }catch{ return ''; }
      };
      eBody.innerHTML = (dbdata.eventos||[]).map(e => `
        <tr>
          <td>${e.id}</td>
          <td>${e.event}</td>
          <td>${e.actor_uid||''}</td>
          <td>${e.source||''}</td>
          <td>${e.ts||''}</td>
          <td style="max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${fmtCtx(e.context)}</td>
        </tr>`).join('');

      // Dispositivos en Data Base
      const camBody = document.getElementById('db-cams');
      if (camBody){
        const cams = (dbdata.devices && dbdata.devices.cameras) || [];
        camBody.innerHTML = cams.map(d=>`
          <tr><td>${d.id}</td><td>${d.name||''}</td><td>${d.ip||''}</td><td>${d.url||''}</td><td>${d.status||''}</td><td>${d.location||''}</td><td>${d.last_seen||''}</td></tr>
        `).join('');
      }
      const qrBody = document.getElementById('db-qr');
      if (qrBody){
        const rows = (dbdata.devices && dbdata.devices.qr_scanners) || [];
        qrBody.innerHTML = rows.map(d=>`
          <tr><td>${d.id}</td><td>${d.name||''}</td><td>${d.ip||''}</td><td>${d.url||''}</td><td>${d.status||''}</td><td>${d.location||''}</td><td>${d.last_seen||''}</td></tr>
        `).join('');
      }
      const nfcBody = document.getElementById('db-nfc');
      if (nfcBody){
        const rows = (dbdata.devices && dbdata.devices.nfc) || [];
        nfcBody.innerHTML = rows.map(d=>`
          <tr><td>${d.id}</td><td>${d.name||''}</td><td>${d.ip||''}</td><td>${d.port||''}</td><td>${d.status||''}</td><td>${d.location||''}</td><td>${d.last_seen||''}</td></tr>
        `).join('');
      }
      const form = document.getElementById('userForm');
      if (form){
        form.addEventListener('submit', async (ev)=>{
          ev.preventDefault();
          const payload = {
            uid: document.getElementById('f_uid').value.trim(),
            email: document.getElementById('f_email').value.trim(),
            nombre: document.getElementById('f_nombre').value.trim(),
            apellido: document.getElementById('f_apellido').value.trim(),
            rol: document.getElementById('f_rol').value.trim()||'R-EMP',
            password: document.getElementById('f_password').value,
          };
          try{
            const r = await fetch(`/api/users?uid=${encodeURIComponent(uid)}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
            if(!r.ok){ const j = await r.json().catch(()=>({detail:'error'})); alert('Error: '+j.detail); return; }
            location.reload();
          }catch(err){ alert('Error: '+err.message); }
        });
      }
    }
    if (role === 'R-ADM' || role === 'R-AC') {
      try{
        const ev = await getJSON(`/api/ac/last?uid=${encodeURIComponent(uid)}`);
        document.getElementById('acbox').innerHTML = `
          <div style="display:flex;gap:10px;align-items:center">
            <img src="${ev.foto_url}" style="width:48px;height:48px;border-radius:50%">
            <div>
              <div><b>${ev.nombre}</b> <span class="muted">(${ev.uid})</span></div>
              <div class="muted">${ev.rol || ''}</div>
              <div class="muted">Autenticado: ${ev.when}</div>
            </div>
          </div>`;
      }catch{ document.getElementById('acbox').textContent = 'Sin autenticaciones recientes.'; }
    }
  }catch(e){ console.error(e); }
}

// Logout
document.getElementById('logout').addEventListener('click', ()=>{
  localStorage.clear(); sessionStorage.clear();
  location.replace('login.html?msg=loggedout');
});

loadMe();
