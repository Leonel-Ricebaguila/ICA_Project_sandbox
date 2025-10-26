// app.js — Panel por roles + perfil + temporizador

// Sesión a nivel de navegador (localStorage)
let   authOk  = localStorage.getItem('auth_ok') === 'true';
let   authExp = parseInt(localStorage.getItem('auth_expires') || '0', 10);
let   uid     = localStorage.getItem('uid') || sessionStorage.getItem('uid');

// Si venimos de qr.html, podemos traer el UID en la query (?u=UID) o en el hash (#u=UID)
try{
  let uParam = new URLSearchParams(location.search).get('u');
  if (!uParam){
    const h = (location.hash||'').replace(/^#/, '');
    if (h){ uParam = new URLSearchParams(h).get('u'); }
  }
  if (uParam){
    localStorage.setItem('uid', uParam);
    uid = uParam;
    const exp = Date.now() + 4*60*60*1000; // 4h
    localStorage.setItem('auth_ok', 'true');
    localStorage.setItem('auth_expires', String(exp));
    authOk = true; authExp = exp;
    // limpiar query/hash visualmente
    try{ history.replaceState(null, '', location.pathname); }catch{}
  }
}catch{}

function parseJwt(t){
  try{
    const p = (t||'').split('.')[1]; if(!p) return null;
    let b = p.replace(/-/g,'+').replace(/_/g,'/');
    // padding
    while (b.length % 4) b += '=';
    return JSON.parse(atob(b));
  }catch(e){ return null }
}
// Política de inicio: si no tenemos uid en la pestaña, no podemos continuar
if (!uid) {
  location.replace('login.html?msg=nosession');
}
// Si no tenemos expiración, fija una ventana de 60 min para el temporizador de UI
if (!authExp || isNaN(authExp)) {
  authExp = Date.now() + 60*60*1000;
  try{ localStorage.setItem('auth_expires', String(authExp)); }catch{}
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

async function getJSON(url, opts){
  const r = await fetch(url);
  if(!r.ok){
    if (opts && opts.fatal) {
      if (r.status===401 || r.status===403){ localStorage.clear(); sessionStorage.clear(); location.replace('login.html?msg=denied'); return; }
      if (r.status===404){ localStorage.clear(); sessionStorage.clear(); location.replace('login.html?msg=nosession'); return; }
    }
    const j = await r.json().catch(()=>({detail:'error'}));
    throw new Error(j.detail || 'error');
  }
  return r.json();
}

// Perfil
async function loadMe(){
  if (window.__loadMeRan) return;
  try{
    const me = await getJSON(`/api/users/me?uid=${encodeURIComponent(uid||'')}`, {fatal:true});
    if (!me || !me.uid){ throw new Error('no me'); }
    nameEl.textContent  = `${me.nombre||''} ${me.apellido||''}`.trim() || me.uid;
    emailEl.textContent = me.email || '';
    roleEl.textContent  = me.rol || '-';
    avatarEl.src        = me.foto_url || 'avatar.png';
    if (cornerName) cornerName.textContent = (nameEl.textContent || me.uid);
    if (cornerAvatar) cornerAvatar.src = avatarEl.src;
    applyRole(me.rol);
    loadSections(me.rol);
    window.__loadMeRan = true;
    // Publicar clave pública de dispositivo de forma persistente (sobrevive a cierres)
    try{
      await (async function ensureDeviceKey(){
        // Preferir localStorage para persistencia entre sesiones del navegador
        let pub = null, prv = null;
        try{
          pub = localStorage.getItem('dev_pub_jwk');
          prv = localStorage.getItem('dev_priv_jwk');
        }catch{}
        if (!pub || !prv){
          const kp = await crypto.subtle.generateKey({name:'ECDH', namedCurve:'P-256'}, true, ['deriveKey','deriveBits']);
          const pubJ = await crypto.subtle.exportKey('jwk', kp.publicKey);
          const prvJ = await crypto.subtle.exportKey('jwk', kp.privateKey);
          pub = JSON.stringify(pubJ); prv = JSON.stringify(prvJ);
          try{ localStorage.setItem('dev_pub_jwk', pub); localStorage.setItem('dev_priv_jwk', prv); }catch{}
        }
        // Copiar a sessionStorage para uso inmediato
        try{
          if (!sessionStorage.getItem('dev_pub_jwk')) sessionStorage.setItem('dev_pub_jwk', pub);
          if (!sessionStorage.getItem('dev_priv_jwk')) sessionStorage.setItem('dev_priv_jwk', prv);
        }catch{}
        const pubJwk = JSON.parse(pub||'null');
        if (pubJwk){
          await fetch('/api/users/devkey', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({uid, jwk: pubJwk})});
        }
      })();
    }catch(e){ console.warn('devkey publish failed', e); }
  }catch(e){
    try{ console.warn('loadMe failed', e); }catch{}
    // permitir reintento si falló antes de terminar
    try{ delete window.__loadMeRan; }catch{}
    localStorage.clear(); sessionStorage.clear();
    location.replace('login.html?msg=nosession');
  }
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
  } else if (role === 'R-AUD') {
    // auditor: acceso a todas las vistas pero solo lectura (se aplica en loadSections)
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
let _logsTimer = null, _acTimer = null, _dbTimer = null, _msgTimer = null;
let _lastLogId = 0;

async function loadSections(role){
  try{
    if (role === 'R-ADM' || role === 'R-MON' || role === 'R-AUD') {
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

      const box = document.getElementById('logs');
      const logs = (await getJSON(`/api/logs?uid=${encodeURIComponent(uid)}`)).filter(e=> (e.tipo||'')!=='message_created');
      _lastLogId = logs.reduce((m, e)=> Math.max(m, e.id||0), 0);
      box.innerHTML = logs.length ? logs.map(e => `
        <div style="padding:6px 0;border-bottom:1px solid #e5e7eb">
          <b>${e.tipo}</b> · <span class="muted">${e.created_at}</span> · actor: ${e.actor_uid} · src: ${e.source}
        </div>`).join('') : 'Sin eventos.';
      // Preferir SSE; fallback a polling incremental
      let esSupported = 'EventSource' in window;
      if (esSupported){
        try{
          const es = new EventSource(`/api/logs/stream?uid=${encodeURIComponent(uid)}`);
          let lastEvtTs = Date.now();
          // Iniciar polling SIEMPRE como refuerzo (evita perder eventos de otros procesos)
          if (_logsTimer) clearInterval(_logsTimer);
          _logsTimer = setInterval(async ()=>{
            try{
              const inc = (await getJSON(`/api/logs?uid=${encodeURIComponent(uid)}&since_id=${_lastLogId}`)).filter(e=> (e.tipo||'')!=='message_created');
              if (Array.isArray(inc) && inc.length){
                const html = inc.map(e => `
                  <div style=\"padding:6px 0;border-bottom:1px solid #e5e7eb\">\n                    <b>${e.tipo}</b> · <span class=\"muted\">${e.created_at}</span> · actor: ${e.actor_uid} · src: ${e.source}\n                  </div>`).join('');
                const wrap = document.createElement('div');
                wrap.innerHTML = html;
                wrap.childNodes.forEach(n => box.prepend(n));
                _lastLogId = Math.max(_lastLogId, inc[inc.length-1].id||_lastLogId);
                lastEvtTs = Date.now();
              }
            }catch{}
          }, 1000);
          es.addEventListener('log', async (evt)=>{
            try{
              const e = JSON.parse(evt.data||'{}');
              if ((e.tipo||'')==='message_created') return;
              if (!e || !e.id) return;
              // Detectar wipe y forzar resync completo
              if (e.tipo === 'db_wipe'){
                _lastLogId = 0;
                try{ window.__refreshDB && window.__refreshDB(); }catch{}
                try{
                  const all = await getJSON(`/api/logs?uid=${encodeURIComponent(uid)}`);
                  const html = (all||[]).map(x=>`
                    <div style=\"padding:6px 0;border-bottom:1px solid #e5e7eb\">\n                      <b>${x.tipo}</b> · <span class=\"muted\">${x.created_at||''}</span> · actor: ${x.actor_uid||''} · src: ${x.source||''}\n                    </div>`).join('');
                  box.innerHTML = html || 'Sin eventos.';
                  _lastLogId = (all||[]).reduce((m, a)=>Math.max(m, a.id||0), 0);
                }catch{}
              }
              // Si el evento es de la familia QR, hacer un pull completo para capturar toda la secuencia
              const et = (e.tipo||'').toLowerCase();
              if (et.startsWith('qr_') || et === 'login_success_pending_qr'){
                try{
                  const all = await getJSON(`/api/logs?uid=${encodeURIComponent(uid)}`);
                  const html = (all||[]).map(x=>`
                    <div style=\"padding:6px 0;border-bottom:1px solid #e5e7eb\">\n                      <b>${x.tipo}</b> · <span class=\"muted\">${x.created_at||''}</span> · actor: ${x.actor_uid||''} · src: ${x.source||''}\n                    </div>`).join('');
                  box.innerHTML = html || 'Sin eventos.';
                  _lastLogId = (all||[]).reduce((m, a)=>Math.max(m, a.id||0), 0);
                }catch{}
              }
              if (e.id <= _lastLogId) return;
              const div = document.createElement('div');
              div.style.cssText = 'padding:6px 0;border-bottom:1px solid #e5e7eb';
              div.innerHTML = `<b>${e.tipo}</b> · <span class="muted">${e.created_at||''}</span> · actor: ${e.actor_uid||''} · src: ${e.source||''}`;
              box.prepend(div);
              _lastLogId = e.id;
              lastEvtTs = Date.now();
              // Si el evento toca usuarios/QR/DB, refrescar inmediatamente la pestaña DB si existe
              const t = (e.tipo||'').toLowerCase();
              if (window.__refreshDB && (t==='user_created' || t==='user_updated' || t==='user_revoked' || t==='qr_assigned' || t==='qr_revoked' || t==='db_wipe')){
                try{ window.__refreshDB(); }catch{}
              }
            }catch{}
          });
          es.addEventListener('error', ()=>{ try{ es.close(); }catch{} /* polling ya activo */ });
        }catch{ esSupported = false; }
      }
      if (!esSupported){
        if (_logsTimer) clearInterval(_logsTimer);
        _logsTimer = setInterval(async ()=>{
          try{
            const inc = (await getJSON(`/api/logs?uid=${encodeURIComponent(uid)}&since_id=${_lastLogId}`)).filter(e=> (e.tipo||'')!=='message_created');
            if (Array.isArray(inc) && inc.length){
              const html = inc.map(e => `
                <div style="padding:6px 0;border-bottom:1px solid #e5e7eb">
                  <b>${e.tipo}</b> · <span class="muted">${e.created_at}</span> · actor: ${e.actor_uid} · src: ${e.source}
                </div>`).join('');
              const wrap = document.createElement('div');
              wrap.innerHTML = html;
              // Append new in order (inc is asc)
              wrap.childNodes.forEach(n => box.prepend(n));
              _lastLogId = Math.max(_lastLogId, inc[inc.length-1].id||_lastLogId);
            }
          }catch{}
        }, 3000);
      }
    }
    // Mensajería (E2E) con sidebar (grupos fijos + DM por email)
    (async function setupMessaging(){
      if (window.__msgInit) return; window.__msgInit = true;
      const sEl = document.getElementById('msgStatus');
      const listEl = document.getElementById('msgList');
      const tEl = document.getElementById('msgText');
      const sendBtn = document.getElementById('msgSend');
      const groupsBox = document.getElementById('msgGroups');
      const titleEl = document.getElementById('msgTitle');
      const emailEl = document.getElementById('msgEmail');
      const openDmBtn = document.getElementById('msgOpenDM');
      const keyBtn = document.getElementById('msgKeyBtn');
      const syncBtn = document.getElementById('msgSyncBtn');
      if (!groupsBox || !listEl || !sendBtn) return;

      const allGroups = ['IAM','IM','AC','Mon','Avisos'];
      const allowedGroups = (()=>{
        if (role === 'R-ADM') return allGroups;
        if (role === 'R-IM') return ['IM','Avisos'];
        if (role === 'R-AC') return ['AC','Avisos'];
        if (role === 'R-MON') return ['Mon','Avisos'];
        if (role === 'R-AUD') return ['Avisos'];
        return ['Avisos'];
      })();

      // Crypto helpers
      const te = new TextEncoder();
      const td = new TextDecoder();
      const b64 = (buf)=>{ let bin=''; const bytes=new Uint8Array(buf); for (let i=0;i<bytes.length;i++){ bin += String.fromCharCode(bytes[i]); } return btoa(bin); };
      const ub64 = (s)=>{ const bin = atob(s); const len = bin.length; const bytes = new Uint8Array(len); for (let i=0;i<len;i++){ bytes[i] = bin.charCodeAt(i);} return bytes.buffer; };
      async function deriveKeyPBK(pass, salt){ const keyMaterial = await crypto.subtle.importKey('raw', te.encode(pass), 'PBKDF2', false, ['deriveKey']); return crypto.subtle.deriveKey({name:'PBKDF2', salt, iterations:100000, hash:'SHA-256'}, keyMaterial, {name:'AES-GCM', length:256}, false, ['encrypt','decrypt']); }
      async function importPubJwk(jwk){ return crypto.subtle.importKey('jwk', jwk, {name:'ECDH', namedCurve:'P-256'}, true, []); }
      async function importPrvJwk(jwk){ return crypto.subtle.importKey('jwk', jwk, {name:'ECDH', namedCurve:'P-256'}, true, ['deriveBits','deriveKey']); }
      async function dmSharedSecret(otherJwk){
        const prv = JSON.parse(sessionStorage.getItem('dev_priv_jwk')||'null');
        if (!prv) throw new Error('no device key');
        const myPrv = await importPrvJwk(prv);
        const otherPub = await importPubJwk(otherJwk);
        const bits = await crypto.subtle.deriveBits({name:'ECDH', public: otherPub}, myPrv, 256);
        return new Uint8Array(bits);
      }
      async function hkdfToAesKey(bytes, saltStr){
        // Derive AES key by importing raw bytes and running PBKDF2 with a salt string (cheap HKDF-like)
        return deriveKeyPBK(b64(bytes), await crypto.subtle.digest('SHA-256', te.encode(saltStr)));
      }
      async function encrypt(plain, key){ const iv = crypto.getRandomValues(new Uint8Array(12)); const ct = await crypto.subtle.encrypt({name:'AES-GCM', iv}, key, te.encode(plain)); return b64(iv)+':'+b64(ct); }
      async function decrypt(ct, key){ try{ const [ivb, data] = String(ct||'').split(':'); if(!ivb||!data) return null; const iv=new Uint8Array(ub64(ivb)); const buf=await crypto.subtle.decrypt({name:'AES-GCM', iv}, key, ub64(data)); return td.decode(buf);}catch(e){return null;} }

      let state = { channel: null, label: null, key: null };
      const dmKeyCache = new Map(); // targetUid -> AES key
      const channelKeyId = (ch)=> `msg_key_${ch}`;
      async function ensureKeyFor(channel){
        try{
          const cached = sessionStorage.getItem(channelKeyId(channel));
          if (cached){ const salt = await crypto.subtle.digest('SHA-256', te.encode('upy-center-msg::'+channel)); state.key = await deriveKey(cached, salt); return true; }
        }catch{}
        const pass = prompt(`Define la clave E2E para ${channel}`) || '';
        if (!pass) return false;
        try{ sessionStorage.setItem(channelKeyId(channel), pass); }catch{}
        const salt = await crypto.subtle.digest('SHA-256', te.encode('upy-center-msg::'+channel));
        state.key = await deriveKey(pass, salt);
        return true;
      }

      // Clave de canal (grupos y DM) persistente por usuario
      async function ensureChannelKey(){
        if (!state.channel){ state.chanKey = null; return; }
        try{ const raw = localStorage.getItem('chan_key::'+state.channel); if (raw){ const bytes = Uint8Array.from(atob(raw), c=>c.charCodeAt(0)); state.chanKey = await crypto.subtle.importKey('raw', bytes, {name:'AES-GCM'}, false, ['encrypt','decrypt']); return; } }catch{}
        try{ const res = await getJSON(`/api/messages/chan_key?channel=${encodeURIComponent(state.channel)}&uid=${encodeURIComponent(uid)}`); if (res && res.cipher){ const selfPub = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||localStorage.getItem('dev_pub_jwk')||'null'); if (selfPub){ const secSelf = await dmSharedSecret(selfPub); const kek = await hkdfToAesKey(secSelf, 'CHAN:'+state.channel); const rawB64 = await decrypt(res.cipher, kek); if (rawB64){ const bytes = Uint8Array.from(atob(rawB64), c=>c.charCodeAt(0)); state.chanKey = await crypto.subtle.importKey('raw', bytes, {name:'AES-GCM'}, false, ['encrypt','decrypt']); try{ localStorage.setItem('chan_key::'+state.channel, rawB64);}catch{} return; } } } }catch{}
        try{ const keyBytes = crypto.getRandomValues(new Uint8Array(32)); state.chanKey = await crypto.subtle.importKey('raw', keyBytes, {name:'AES-GCM'}, false, ['encrypt','decrypt']); const rawB64 = btoa(String.fromCharCode(...keyBytes)); const selfPub = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||localStorage.getItem('dev_pub_jwk')||'null'); if (selfPub){ const secSelf = await dmSharedSecret(selfPub); const kek = await hkdfToAesKey(secSelf, 'CHAN:'+state.channel); const myWrap = await encrypt(rawB64, kek); await fetch('/api/messages/chan_key', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({channel: state.channel, uid, cipher: myWrap})}); try{ localStorage.setItem('chan_key::'+state.channel, rawB64);}catch{} if (state.channel.startsWith('DM:')){ const other = state.channel.split(':').find(x=>x && x!=='DM' && x!==uid); if (other){ try{ const dk = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(other)}`); const sec = await dmSharedSecret(dk.jwk); const kek2 = await hkdfToAesKey(sec, 'CHAN:'+state.channel); const wrap = await encrypt(rawB64, kek2); await fetch('/api/messages/chan_key/batch', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({channel: state.channel, uid, wraps: {[other]: wrap}})});}catch{} } } } }catch{} }

      async function connectChannel(channel, label){
        state.channel = channel; state.label = label;
        titleEl.textContent = label;
        try{ await ensureChannelKey(); }catch{}
        await refreshChat();
        if (_msgTimer) clearInterval(_msgTimer);
        _msgTimer = setInterval(refreshChat, 4000);
        sEl.textContent = `Conectado a "${label}"`;
        const writingDisabled = (role==='R-AUD') || (label==='Avisos' && role!=='R-ADM');
        tEl.disabled = writingDisabled; sendBtn.disabled = writingDisabled;
        if (writingDisabled) sendBtn.title = 'Solo lectura'; else sendBtn.title='';
      }

      const _readMarked = new Set();
      const readModal = document.getElementById('readModal');
      const readList = document.getElementById('readList');
      const readClose = document.getElementById('readClose');
      const openReadModal = (entries)=>{
        if (!readModal || !readList) return;
        const fmt = (ts)=>{ try{ return (ts||'').split('.')[0].replace('T',' ');}catch{ return ts||''; } };
        readList.innerHTML = (entries||[]).map(x=>`<div class="read-item"><div>${(x.nombre||x.uid||'') + ' ' + (x.apellido||'')}</div><div class="muted">${fmt(x.read_at||'')}</div></div>`).join('') || '<div class="muted">Nadie aún.</div>';
        readModal.classList.add('show');
      };
      if (readClose){ readClose.onclick = ()=> readModal.classList.remove('show'); }
      if (readModal){ readModal.addEventListener('click', (e)=>{ if (e.target===readModal) readModal.classList.remove('show'); }); }
      async function refreshChat(){
        if (!state.channel) return;
        try{
          const rows = await getJSON(`/api/messages?grupo=${encodeURIComponent(state.channel)}&uid=${encodeURIComponent(uid)}&limit=200`);
          // Si no hay clave aún, intentaremos mostrar placeholders
          const atBottom = (listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight) < 80;
          let html = '';
          const readsMap = {};
          for (const r of rows.slice().reverse()){
            const it = { id:r.msg_id, uid:r.remitente_uid||'-', at:r.creado_en||'', ct:r.contenido||'', name:`${r.remitente_nombre||r.remitente_uid||''} ${r.remitente_apellido||''}`.trim(), reads: (r.leido_por||[]) };
            readsMap[it.id] = it.reads || [];
            let pt = null;
            if (state.channel.startsWith('DM:')){
              // Primero intentar clave de canal
              try{ const obj = JSON.parse(it.ct); if (obj && obj.__gm__ && obj.scheme==='ck' && obj.ct && state.chanKey){ pt = await decrypt(obj.ct, state.chanKey); } }catch{}
              if (pt==null){
                // Fallback a ECDH par-a-par (legado)
                const other = (it.uid === uid) ? (state.channel.split(':').find(x => x && x !== 'DM' && x !== uid)) : it.uid;
                let k = dmKeyCache.get(other);
                if (!k){
                  try{ const dk = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(other)}`); const secret = await dmSharedSecret(dk.jwk); k = await hkdfToAesKey(secret, `DM:${[uid, other].sort().join(':')}`); dmKeyCache.set(other, k);}catch{}
                }
                if (k) pt = await decrypt(it.ct, k);
              }
            } else {
              // Grupo: dos formatos
              try{
                const obj = JSON.parse(it.ct);
                if (obj && obj.__gm__ && obj.parts){
                  let part = obj.parts[uid];
                  if (part){
                    // derive DM key with sender (fallback a mi propia pub si soy el remitente)
                    let k = dmKeyCache.get(it.uid);
                    if (!k){
                      try{
                        let jwk;
                        if (it.uid === uid){
                          jwk = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||'null');
                        } else {
                          const dk = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(it.uid)}`);
                          jwk = dk.jwk;
                        }
                        if (jwk){
                          const secret = await dmSharedSecret(jwk);
                          k = await hkdfToAesKey(secret, `DM:${[uid, it.uid].sort().join(':')}`);
                          dmKeyCache.set(it.uid, k);
                        }
                      }catch{}
                    }
                    pt = await decrypt(part, k);
                  }
                  // Si no hay part para mí y yo fui el remitente, intentar backfill automático + para destinatarios faltantes
                  if (!pt && it.uid === uid){
                    try{
                      const keys = Object.keys(obj.parts||{}).filter(x=>x && x!== uid);
                      if (keys.length){
                        const any = keys[0];
                        // Obtener la pubkey del destinatario 'any' y descifrar su parte para recuperar plaintext
                        const dk2 = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(any)}`);
                        const sec2 = await dmSharedSecret(dk2.jwk);
                        const k2 = await hkdfToAesKey(sec2, `DM:${[uid, any].sort().join(':')}`);
                        const plain = await decrypt(obj.parts[any], k2);
                        if (plain!=null){
                          // Cifrar mi propia part y enviarla al servidor
                          const selfPub = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||localStorage.getItem('dev_pub_jwk')||'null');
                          if (selfPub){
                            const secSelf = await dmSharedSecret(selfPub);
                            const kSelf = await hkdfToAesKey(secSelf, `DM:${[uid, uid].sort().join(':')}`);
                            const myPart = await encrypt(plain, kSelf);
                            await fetch('/api/messages/backfill_self', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({msg_id: it.id, uid, part: myPart})}).catch(()=>{});
                            pt = plain;
                          }
                          // Backfill para destinatarios faltantes con devkey (envío por lotes)
                          try{
                            // Determinar rol del grupo activo para obtener devkeys
                            const g = state.channel; const roleFor = (gx)=> gx==='IAM'?'R-ADM': gx==='IM'?'R-IM': gx==='AC'?'R-AC': gx==='Mon'?'R-MON': null;
                            const role = roleFor(g);
                            let keylist = (g==='Avisos')
                              ? await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&all=1`)
                              : await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&role=${encodeURIComponent(role||'')}`);
                            if (g !== 'Avisos'){
                              try{
                                const admins = await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&role=R-ADM`);
                                keylist = (keylist||[]).concat(admins||[]);
                              }catch{}
                            }
                            const missing = {};
                            for (const rec of (keylist||[])){
                              const ruid = rec.uid; if (!ruid || ruid===uid) continue;
                              if (!obj.parts[ruid]){
                                try{
                                  const secR = await dmSharedSecret(rec.jwk);
                                  const kR = await hkdfToAesKey(secR, `DM:${[uid, ruid].sort().join(':')}`);
                                  missing[ruid] = await encrypt(plain, kR);
                                }catch{}
                              }
                            }
                            const count = Object.keys(missing).length;
                            if (count){
                              await fetch('/api/messages/backfill_parts', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({msg_id: it.id, uid, parts: missing})}).catch(()=>{});
                            }
                          }catch{}
                        }
                      }
                    }catch{}
                  }
                }
              }catch{
                // legacy: intentar con state.key (si existiera de versiones anteriores)
                if (state.key) pt = await decrypt(it.ct, state.key);
              }
            }
            const safe = (s)=>{ if (s==null) return ''; return String(s).replace(/[&<>]/g, c=> ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); };
            const fmt = (ts)=>{ try{ return (ts||'').split('.')[0].split('T')[1]||ts; }catch{ return ts||''; } };
            const content = pt != null ? safe(pt).replace(/\n/g,'<br>') : '<span class="muted">[contenido cifrado]</span>';
            const cls = (it.uid === uid) ? 'me' : 'other';
            const showName = cls !== 'me';
            const who = safe(it.name||it.uid);
            const infoBtn = (Array.isArray(it.reads) && it.reads.length) ? `<span class="info" data-info="${it.id}" title="Leído por">Info</span>` : '';
            html += `
              <div class="chat-row ${cls}" data-id="${it.id}">
                <div class="bubble ${cls}">
                  ${showName ? `<div class="head">${who}</div>` : ''}
                  <div>${content}</div>
                  <div class="foot"><span class="muted">${fmt(it.at)}</span>${infoBtn}</div>
                </div>
              </div>`;
          }
          listEl.innerHTML = html || '<div class="muted" style="padding:6px">Sin mensajes.</div>';
          if (atBottom) { listEl.scrollTop = listEl.scrollHeight; }
          // bind info buttons
          try{
            listEl.querySelectorAll('.info').forEach(el=>{
              el.addEventListener('click', ()=>{
                const id = el.getAttribute('data-info');
                openReadModal(readsMap[id] || []);
              });
            });
          }catch{}
          // Marcar como leídos los mensajes visibles que no sean míos
          try{
            const toMark = rows.filter(r => r.remitente_uid && r.remitente_uid !== uid && !_readMarked.has(r.msg_id));
            if (toMark.length){
              await Promise.allSettled(toMark.map(r=> fetch('/api/messages/read', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({msg_id:r.msg_id, uid})}).then(()=>{_readMarked.add(r.msg_id);})));
            }
          }catch{}
        }catch(e){ listEl.innerHTML = `<div class="muted" style="padding:6px">Error: ${e.message}</div>`; }
      }

      // Pintar grupos y manejar clicks
      try{
        const colorFor = (g)=> ({IAM:'#2563eb', IM:'#0ea5e9', AC:'#7c3aed', Mon:'#22c55e', Avisos:'#dc2626'})[g] || '#64748b';
        const hexToRgb = (hex)=>{ const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex); return m? {r:parseInt(m[1],16), g:parseInt(m[2],16), b:parseInt(m[3],16)}: {r:100,g:116,b:139}; };
        const bgStyle = (hex)=>{ const {r,g,b}=hexToRgb(hex); return `background:linear-gradient(180deg, rgba(${r},${g},${b},0.20), rgba(${r},${g},${b},0.32)); border:1px solid rgba(${r},${g},${b},0.45); color:#0b2a3c;`; };
        groupsBox.innerHTML = allowedGroups.map(g=>{
          const col = colorFor(g);
          return `
          <button class="btn btn-ghost" data-g="${g}" style="justify-content:flex-start;width:100%;position:relative;${bgStyle(col)}">
            <span class="dot" id="dot-${g}" style="position:absolute;left:8px;top:12px;width:10px;height:10px;border-radius:50%;background:${col};display:none"></span>
            <div style="display:flex;align-items:center;gap:8px;width:100%">
              <div style="flex:1;text-align:left">
                <div style="font-weight:700">${g}</div>
                <div id="sub-${g}" class="muted" style="font-size:.82rem;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">—</div>
              </div>
              <div id="time-${g}" class="muted" style="font-size:.82rem"></div>
            </div>
          </button>`;
        }).join('');
        Array.from(groupsBox.querySelectorAll('button')).forEach(b=>{
          b.addEventListener('click', async ()=>{
            const g = b.getAttribute('data-g');
            const channel = g; // API usa nombre simple para grupos
            await connectChannel(channel, g);
          });
        });
      }catch{}

      async function refreshSummaries(){
        try{
          const sum = await getJSON(`/api/messages/summary?uid=${encodeURIComponent(uid)}`);
          const dmDot = document.getElementById('dmDot');
          if (dmDot){ dmDot.style.display = (sum && sum.dm_unread>0) ? 'inline-block' : 'none'; }
          const rows = (sum && sum.groups) || [];
          const fmtShort = (ts)=>{ if(!ts) return ''; const x = ts.split('T')[1]||ts; return x.split('.')[0]; };
          for (const r of rows){
            const g = r.grupo; const last = r.last;
            const dot = document.getElementById(`dot-${g}`);
            if (dot){ dot.style.display = (r.unread>0) ? 'inline-block' : 'none'; }
            const timeEl = document.getElementById(`time-${g}`);
            const subEl = document.getElementById(`sub-${g}`);
            if (last){
              // intentar descifrar preview
              let preview = '[cifrado]';
              try{
                if (g === 'Avisos' || g==='IM' || g==='IAM' || g==='AC' || g==='Mon'){
                  const sender = last.remitente_uid;
                  let text = null;
                  try{
                    const obj = JSON.parse(last.contenido||'null');
                    if (obj && obj.__gm__ && obj.parts && obj.parts[uid]){
                      let jwk;
                      if (sender === uid){
                        jwk = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||'null');
                      } else {
                        const dk = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(sender)}`);
                        jwk = dk && dk.jwk;
                      }
                      if (jwk){
                        const secret = await dmSharedSecret(jwk);
                        const k = await hkdfToAesKey(secret, `DM:${[uid, sender].sort().join(':')}`);
                        text = await decrypt(obj.parts[uid], k);
                      }
                    }
                  }catch{}
                  preview = text || preview;
                }
              }catch{}
              if (subEl){
                const who = `${last.remitente_nombre||last.remitente_uid||''} ${last.remitente_apellido||''}`.trim();
                subEl.textContent = (who ? `~${who}: ` : '') + (preview || '');
              }
              if (timeEl){ timeEl.textContent = fmtShort(last.creado_en||''); }
            } else {
              if (subEl) subEl.textContent = '—';
              if (timeEl) timeEl.textContent = '';
            }
          }
        }catch{}
      }
      // refrescar al entrar y cada 6s
      await refreshSummaries();
      setInterval(refreshSummaries, 6000);

      // DM por email
      if (openDmBtn){
        openDmBtn.addEventListener('click', async ()=>{
          const email = (emailEl && emailEl.value || '').trim(); if (!email) return;
          try{
            const u = await getJSON(`/api/users/lookup?email=${encodeURIComponent(email)}&uid=${encodeURIComponent(uid)}`);
            if (!u || !u.uid) { alert('No encontrado'); return; }
            const ids = [uid, u.uid].sort();
            const channel = `DM:${ids[0]}:${ids[1]}`;
            const label = `${u.nombre||''} ${u.apellido||''}`.trim() || u.email || u.uid;
            await connectChannel(channel, label);
          }catch(e){ alert('Error: '+e.message); }
        });
      }

      // Limpiar caché de claves derivadas (no pide contraseña)
      if (keyBtn){ keyBtn.addEventListener('click', async ()=>{ if (!state.channel){ alert('Selecciona un chat'); return;} try{ dmKeyCache.clear(); }catch{} await refreshChat(); }); }

      // Botón de sincronización manual (rellena partes faltantes para mensajes donde soy remitente)
      async function getKeylistForGroup(g){
        const roleFor = (gx)=> gx==='IAM'?'R-ADM': gx==='IM'?'R-IM': gx==='AC'?'R-AC': gx==='Mon'?'R-MON': null;
        const role = roleFor(g);
        let keylist = (g==='Avisos')
          ? await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&all=1`)
          : await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&role=${encodeURIComponent(role||'')}`);
        if (g !== 'Avisos'){
          try{
            const admins = await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&role=R-ADM`);
            keylist = (keylist||[]).concat(admins||[]);
          }catch{}
        }
        return keylist||[];
      }
      async function backfillChannel(){
        if (!state.channel || state.channel.startsWith('DM:')){ alert('Solo para grupos'); return; }
        try{
          const rows = await getJSON(`/api/messages?grupo=${encodeURIComponent(state.channel)}&uid=${encodeURIComponent(uid)}&limit=200`);
          const keylist = await getKeylistForGroup(state.channel);
          const selfPub = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||localStorage.getItem('dev_pub_jwk')||'null');
          for (const r of rows){
            if (r.remitente_uid !== uid) continue;
            let obj = null; try{ obj = JSON.parse(r.contenido||''); }catch{}
            if (!obj || !obj.__gm__) continue;
            // Obtener plaintext desde cualquier parte existente
            let plain = null;
            try{
              if (obj.parts && typeof obj.parts==='object'){
                // preferir mi propia parte si existe
                if (obj.parts[uid] && selfPub){
                  const secSelf = await dmSharedSecret(selfPub); const kSelf = await hkdfToAesKey(secSelf, `DM:${[uid, uid].sort().join(':')}`);
                  plain = await decrypt(obj.parts[uid], kSelf);
                }
                if (plain==null){
                  const otherIds = Object.keys(obj.parts).filter(x=>x && x!==uid);
                  if (otherIds.length){
                    const any = otherIds[0];
                    const dk = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(any)}`);
                    const sec = await dmSharedSecret(dk.jwk); const k = await hkdfToAesKey(sec, `DM:${[uid, any].sort().join(':')}`);
                    plain = await decrypt(obj.parts[any], k);
                  }
                }
              }
            }catch{}
            if (plain==null) continue;
            // Backfill self si falta
            try{
              if (!obj.parts[uid] && selfPub){
                const secSelf = await dmSharedSecret(selfPub); const kSelf = await hkdfToAesKey(secSelf, `DM:${[uid, uid].sort().join(':')}`);
                const myPart = await encrypt(plain, kSelf);
                await fetch('/api/messages/backfill_self', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({msg_id:r.msg_id, uid, part: myPart})});
              }
            }catch{}
            // Backfill destinatarios faltantes
            const missing = {};
            for (const rec of keylist){
              const rid = rec.uid; if (!rid || rid===uid) continue;
              if (!obj.parts[rid]){
                try{
                  const secR = await dmSharedSecret(rec.jwk); const kR = await hkdfToAesKey(secR, `DM:${[uid, rid].sort().join(':')}`);
                  missing[rid] = await encrypt(plain, kR);
                }catch{}
              }
            }
            if (Object.keys(missing).length){
              await fetch('/api/messages/backfill_parts', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({msg_id:r.msg_id, uid, parts: missing})});
            }
          }
          await refreshChat(); await refreshSummaries();
          alert('Sincronización de partes completada.');
        }catch(e){ alert('Error al sincronizar: '+e.message); }
      }
      if (syncBtn){ syncBtn.addEventListener('click', backfillChannel); }

      // Envío (con guardia anti-doble envío)
      let _sending = false;
      async function doSend(){
        if (_sending) return; _sending = true;
        if (role === 'R-AUD') return;
        const txt = (tEl.value||'').trim(); if (!txt) return;
        if (!state.channel){ sEl.textContent = 'Selecciona un chat'; return; }
        try{
          let contenido = '';
          if (state.channel.startsWith('DM:')){
            if (state.chanKey){
              const ct = await encrypt(txt, state.chanKey);
              contenido = JSON.stringify({__gm__:true, from: uid, scheme:'ck', ct});
            } else {
              const other = state.channel.split(':').find(x=>x && x!== 'DM' && x!== uid);
              const dk = await getJSON(`/api/users/devkey?uid=${encodeURIComponent(uid)}&target=${encodeURIComponent(other)}`);
              const secret = await dmSharedSecret(dk.jwk);
              const k = await hkdfToAesKey(secret, `DM:${[uid, other].sort().join(':')}`);
              contenido = await encrypt(txt, k);
            }
          } else {
            // Grupo: empaquetar por-recipient
            const roleFor = (g)=> g==='IAM'?'R-ADM': g==='IM'?'R-IM': g==='AC'?'R-AC': g==='Mon'?'R-MON': null;
            const role = roleFor(state.channel);
            let keylist = (state.channel==='Avisos')
              ? await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&all=1`)
              : await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&role=${encodeURIComponent(role||'')}`);
            if (state.channel !== 'Avisos'){
              try{
                const admins = await getJSON(`/api/users/devkeys?uid=${encodeURIComponent(uid)}&role=R-ADM`);
                keylist = (keylist||[]).concat(admins||[]);
              }catch{}
            }
            const parts = {};
            for (const rec of keylist){
              try{
                const secret = await dmSharedSecret(rec.jwk);
                const k = await hkdfToAesKey(secret, `DM:${[uid, rec.uid].sort().join(':')}`);
                parts[rec.uid] = await encrypt(txt, k);
              }catch{}
            }
            // Incluye siempre al emisor para que pueda leer su propio mensaje
            try{
              if (!parts[uid]){
                const myPub = JSON.parse(sessionStorage.getItem('dev_pub_jwk')||'null');
                if (myPub){
                  const mySecret = await dmSharedSecret(myPub);
                  const myKey = await hkdfToAesKey(mySecret, `DM:${[uid, uid].sort().join(':')}`);
                  parts[uid] = await encrypt(txt, myKey);
                }
              }
            }catch{}
            contenido = JSON.stringify({__gm__:true, from: uid, parts});
          }
          const payload = { remitente_uid: uid, grupo: state.channel, contenido };
          const r = await fetch(`/api/messages?uid=${encodeURIComponent(uid)}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
          const j = await r.json().catch(()=>({detail:'error'}));
          if (!r.ok){ throw new Error(j.detail || 'error'); }
          tEl.value = '';
          await refreshChat();
          try{ listEl.scrollTop = listEl.scrollHeight; }catch{}
        }catch(e){ alert('Error: '+e.message); }
        finally { _sending = false; }
      }
      sendBtn.addEventListener('click', doSend);
      try{ tEl.addEventListener('keydown', (ev)=>{ if (ev.key === 'Enter' && !ev.shiftKey){ ev.preventDefault(); doSend(); } }); }catch{}
    })();

    if (role === 'R-ADM' || role === 'R-IM' || role === 'R-AUD') {
      async function refreshDB(){
        const dbdata = await getJSON(`/api/db/all?uid=${encodeURIComponent(uid)}`);
        window.__dbdata = dbdata;

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
            <td style=\"font-family:monospace\">${s.session_id}</td>
            <td>${s.uid||''}</td>
            <td>${s.state||''}</td>
            <td>${s.created_at||''}</td>
            <td>${s.expires_at||''}</td>
          </tr>`).join('');

        const eBody = document.getElementById('db-events');
        const fmtCtx = (c)=>{ try{ return c? JSON.stringify(c):''; }catch{ return ''; } };
        eBody.innerHTML = (dbdata.eventos||[]).map(e => `
          <tr>
            <td>${e.id}</td>
            <td>${e.event}</td>
            <td>${e.actor_uid||''}</td>
            <td>${e.source||''}</td>
            <td>${e.ts||''}</td>
            <td style=\"max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\">${fmtCtx(e.context)}</td>
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
      }

      await refreshDB();
      window.__refreshDB = refreshDB; // para invocar desde SSE

      // CSV helpers
      const toCSV = (rows, headers, selector)=>{
        const escape = (v)=>{
          if (v===null||v===undefined) return '';
          const s = String(v).replaceAll('"','""');
          return '"'+s+'"';
        };
        const head = headers.map(h=>escape(h.label)).join(',');
        const lines = rows.map(r=> headers.map(h=> escape(selector(r,h.key))).join(','));
        return [head, ...lines].join('\n');
      };
      const download = (name, csv)=>{
        const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = name;
        document.body.appendChild(a); a.click(); a.remove();
      };

      const btnUsers = document.getElementById('csv-users');
      const runDownloadAnim = (btnId, work)=>{
        const root = document.getElementById(btnId);
        if (!root) { work(); return; }
        const icon = root.querySelector('.upy-dl');
        const bar  = icon && icon.querySelector('.bar');
        const C = 283; let p=0;
        if (bar){ bar.style.strokeDashoffset = C; icon.classList.remove('complete','error','paused'); }
        // Animate while seeding CSV synchronously
        const step = ()=>{ if (!bar) return; p+=35; if (p>95) p=95; bar.style.strokeDashoffset = (C - (C*p/100)); if (p<95) setTimeout(step, 25); };
        step();
        try { work(); }
        catch(e){ if (icon) icon.classList.add('error'); throw e; }
        finally{
          if (bar && icon){
            bar.style.strokeDashoffset = 0; icon.classList.add('complete');
            setTimeout(()=>{ icon.classList.remove('complete','error','paused'); bar.style.strokeDashoffset = C; }, 900);
          }
        }
      };

      const logCsv = (name)=>{ try{ fetch(`/api/log/csv?uid=${encodeURIComponent(uid)}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({table:name})}).catch(()=>{});}catch{}};

      if (btnUsers) btnUsers.onclick = ()=> runDownloadAnim('csv-users', ()=>{
        logCsv('usuarios');
        const rows = (window.__dbdata && window.__dbdata.usuarios) || [];
        const headers = [
          {key:'uid',label:'UID'}, {key:'nombre',label:'Nombre'}, {key:'apellido',label:'Apellido'},
          {key:'email',label:'Email'}, {key:'rol',label:'Rol'}, {key:'estado',label:'Estado'},
          {key:'qr_status',label:'QR Status'}, {key:'qr_card_id',label:'Card ID'}, {key:'ultimo_acceso',label:'Ultimo acceso'}
        ];
        const csv = toCSV(rows, headers, (r,k)=> r[k]);
        download('usuarios.csv', csv);
      });

      const btnSess = document.getElementById('csv-sessions');
      if (btnSess) btnSess.onclick = ()=> runDownloadAnim('csv-sessions', ()=>{
        logCsv('auth_sessions');
        const rows = (window.__dbdata && window.__dbdata.auth_sessions) || [];
        const headers = [
          {key:'session_id',label:'Session ID'},{key:'uid',label:'UID'},{key:'state',label:'State'},
          {key:'created_at',label:'Creado'},{key:'expires_at',label:'Expira'}
        ];
        const csv = toCSV(rows, headers, (r,k)=> r[k]);
        download('auth_sessions.csv', csv);
      });

      const btnEv = document.getElementById('csv-events');
      if (btnEv) btnEv.onclick = ()=> runDownloadAnim('csv-events', ()=>{
        logCsv('eventos');
        const rows = (window.__dbdata && window.__dbdata.eventos) || [];
        const headers = [
          {key:'id',label:'ID'},{key:'event',label:'Tipo'},{key:'actor_uid',label:'Actor'},
          {key:'source',label:'Source'},{key:'ts',label:'Fecha'},{key:'context',label:'Contexto'}
        ];
        const csv = toCSV(rows, headers, (r,k)=> k==='context' ? JSON.stringify(r[k]||{}) : r[k]);
        download('eventos.csv', csv);
      });

      const btnCams = document.getElementById('csv-cams');
      if (btnCams) btnCams.onclick = ()=> runDownloadAnim('csv-cams', ()=>{
        logCsv('devices_cameras');
        const rows = (window.__dbdata && window.__dbdata.devices && window.__dbdata.devices.cameras) || [];
        const headers = [
          {key:'id',label:'ID'},{key:'name',label:'Nombre'},{key:'ip',label:'IP'},
          {key:'url',label:'URL'},{key:'status',label:'Estado'},{key:'location',label:'Ubicacion'},
          {key:'last_seen',label:'Ultimo'}
        ];
        const csv = toCSV(rows, headers, (r,k)=> r[k]);
        download('devices_cameras.csv', csv);
      });

      const btnQR = document.getElementById('csv-qr');
      if (btnQR) btnQR.onclick = ()=> runDownloadAnim('csv-qr', ()=>{
        logCsv('devices_qr_scanners');
        const rows = (window.__dbdata && window.__dbdata.devices && window.__dbdata.devices.qr_scanners) || [];
        const headers = [
          {key:'id',label:'ID'},{key:'name',label:'Nombre'},{key:'ip',label:'IP'},
          {key:'url',label:'URL'},{key:'status',label:'Estado'},{key:'location',label:'Ubicacion'},
          {key:'last_seen',label:'Ultimo'}
        ];
        const csv = toCSV(rows, headers, (r,k)=> r[k]);
        download('devices_qr_scanners.csv', csv);
      });

      const btnNFC = document.getElementById('csv-nfc');
      if (btnNFC) btnNFC.onclick = ()=> runDownloadAnim('csv-nfc', ()=>{
        logCsv('devices_nfc');
        const rows = (window.__dbdata && window.__dbdata.devices && window.__dbdata.devices.nfc) || [];
        const headers = [
          {key:'id',label:'ID'},{key:'name',label:'Nombre'},{key:'ip',label:'IP'},
          {key:'port',label:'Puerto'},{key:'status',label:'Estado'},{key:'location',label:'Ubicacion'},
          {key:'last_seen',label:'Ultimo'}
        ];
        const csv = toCSV(rows, headers, (r,k)=> r[k]);
        download('devices_nfc.csv', csv);
      });
      const form = document.getElementById('userForm');
      if (form){
        if (role === 'R-AUD') {
          // Solo lectura: deshabilitar inputs/botón y no adjuntar handler
          try{
            form.querySelectorAll('input').forEach(el=>{ el.disabled = true; });
            const btn = form.querySelector('button'); if (btn) { btn.disabled = true; btn.title = 'Solo lectura (Auditor)'; }
          }catch{}
        } else {
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
      if (_dbTimer) clearInterval(_dbTimer);
      _dbTimer = setInterval(async ()=>{
        try{
          const dbdata = await getJSON(`/api/db/all?uid=${encodeURIComponent(uid)}`);
          // Update sessions only and events table to keep cost reasonable
          const sBody2 = document.getElementById('db-sessions');
          sBody2.innerHTML = (dbdata.auth_sessions||[]).map(s => `
            <tr>
              <td style="font-family:monospace">${s.session_id}</td>
              <td>${s.uid||''}</td>
              <td>${s.state||''}</td>
              <td>${s.created_at||''}</td>
              <td>${s.expires_at||''}</td>
            </tr>`).join('');
          const eBody2 = document.getElementById('db-events');
          const fmtCtx2 = (c)=>{ try{ return c? JSON.stringify(c):''; }catch{ return ''; } };
          eBody2.innerHTML = (dbdata.eventos||[]).map(e => `
            <tr>
              <td>${e.id}</td>
              <td>${e.event}</td>
              <td>${e.actor_uid||''}</td>
              <td>${e.source||''}</td>
              <td>${e.ts||''}</td>
              <td style="max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${fmtCtx2(e.context)}</td>
            </tr>`).join('');
        }catch{}
      }, 10000);
    }
    if (role === 'R-ADM' || role === 'R-AC' || role === 'R-AUD') {
      const renderAC = async ()=>{
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
      };
      await renderAC();
      if (_acTimer) clearInterval(_acTimer);
      _acTimer = setInterval(renderAC, 5000);
    }
  }catch(e){ console.error(e); }
}

// Logout
document.getElementById('logout').addEventListener('click', ()=>{
  try{
    const u = localStorage.getItem('uid') || sessionStorage.getItem('uid') || '';
    fetch(`/api/auth/logout?uid=${encodeURIComponent(u)}`, {method:'POST'}).catch(()=>{});
  }catch{}
  localStorage.clear(); sessionStorage.clear();
  location.replace('login.html?msg=loggedout');
});

try{ document.addEventListener('DOMContentLoaded', loadMe); }catch{}
// Asegura inicialización incluso si el listener llega tarde
try{ loadMe(); }catch{}

// Color coding de logs: asigna color segun el tipo (nivel) detectado en el texto
(function(){
  const levelFor = (t)=>{
    const raw = t || '';
    const s = raw.toLowerCase();
    // Notificaciones explícitas
    if (raw === 'login_success_pending_qr') return 'blue'; // notificación
    if (raw === 'login_credentials_ok') return 'green';    // credenciales correctas
    if (raw === 'login_completed') return 'green';         // sesión completa
    if (raw === 'qr_session_expired') return 'yellow';     // tiempo agotado
    if (raw === 'qr_session_not_found') return 'red';      // error: sesión inexistente
    // Escaneos QR
    if (raw === 'qr_scanned_mismatch') return 'orange';    // QR ajeno (alerta naranja)
    if (raw === 'qr_scanned_fail') return 'yellow';        // fallo genérico (alerta amarilla)
    // Eventos de aprovisionamiento (pedidos): azules
    if (raw === 'user_created') return 'blue';
    if (raw === 'qr_assigned') return 'blue';
    // Escalado de intentos fallidos (amarillo -> naranja -> rojo)
    if (raw === 'login_failed_warn') return 'yellow';
    if (raw === 'login_failed_timeout') return 'orange';
    if (raw === 'login_failed_lock' || raw === 'login_failed_lock_active') return 'red';
    // Errores graves
    if (/(failed|error|denied|not_found)/.test(s)) return 'red';
    // Tiempo agotado / expirado -> amarillo (alerta leve)
    if (/(timeout|expired)/.test(s)) return 'yellow';
    // Avisos leves
    if (/(attempt|pending|warn)/.test(s)) return 'yellow';
    // Completado/éxito operativo
    if (/(success|ok|created|assigned|completed)/.test(s)) return 'green';
    // Informativo por defecto
    return 'blue';
  };
  const colorize = ()=>{
    const box = document.getElementById('logs');
    if (!box) return;
    Array.from(box.children).forEach(div => {
      const b = div.querySelector && div.querySelector('b');
      const tipo = b ? b.textContent : (div.textContent || '');
      const lvl = levelFor(tipo);
      const cls = 'log-border-' + lvl;
      if (!div.classList.contains(cls)){
        div.classList.add(cls);
      }
    });
  };
  setInterval(colorize, 1000);
})();
