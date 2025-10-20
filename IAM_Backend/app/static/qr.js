// qr.js — 60s + auto-cámara + sin campo manual + fallback servidor
// Descripción:
//  - Tras el login el backend crea una sesión corta (AuthSession) y redirige a qr.html
//  - Aquí intentamos leer un QR y validarlo contra /api/qr/scan
//  - Si el QR corresponde al mismo usuario de la sesión → habilitamos sesión de 4h y vamos a app.html
//  - Si el QR es de otro usuario o expiró → regresamos a login con el motivo

const sessionId = sessionStorage.getItem('session_id');
const timerEl   = document.getElementById('timer');
if (!sessionId) { sessionStorage.clear(); location.replace('login.html'); }

const MAX_TIME = 60;
let countdown = MAX_TIME;
let tHandle;

function updateTimer(){
  const mm = String(Math.floor(countdown/60)).padStart(2,'0');
  const ss = String(countdown%60).padStart(2,'0');
  timerEl.textContent = `${mm}:${ss}`;
}
function startTimer(){
  updateTimer();
  tHandle = setInterval(()=>{
    countdown--;
    updateTimer();
    if(countdown<=0){
      clearInterval(tHandle); stopCamera();
      sessionStorage.clear();
      location.replace('login.html?msg=timeout');
    }
  },1000);
}

// UI
// Referencias de elementos y helpers de layout/estado visual del recuadro
const fileInput  = document.getElementById('fileInput');
const btnCamOn   = document.getElementById('btnCamOn');
const btnCamOff  = document.getElementById('btnCamOff');
const compatMsg  = document.getElementById('compatMsg');
const aimBox     = document.getElementById('aimBox');
const msgBox     = document.getElementById('msg');
function layoutAimBox(){
  if(!video) return;
  const vw = video.clientWidth || 0;
  const vh = video.clientHeight || 0;
  if(!vw || !vh) return;
  const side = Math.floor(Math.min(vw, vh) * 0.68); // 68% del lado menor
  aimBox.style.width = side + 'px';
  aimBox.style.height = side + 'px';
}
function setCompat(m){ compatMsg.textContent = m || ''; }
function aimOk(ok){ aimBox.classList.toggle('ok', !!ok); }

// Verify with server → valida el valor QR contra la sesión creada en /api/auth/login
async function verifyQR(qrval){
  try{
    const r = await fetch('/api/qr/scan',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ session_id: sessionId, qr_value: qrval })
    });
    if(!r.ok){
      let errDetail = 'No autorizado'; let reason = '';
      try{ const ej = await r.json(); errDetail = ej.detail||errDetail; reason = ej.reason||''; }catch{}
      if (r.status===403 && (reason==='session_user_mismatch' || (errDetail||'').toLowerCase().includes('belong'))){
        clearInterval(tHandle); stopCamera(); sessionStorage.clear();
        location.replace('login.html?msg=mismatch'); return;
      }
      if (r.status===400 && reason==='session_expired'){
        clearInterval(tHandle); stopCamera(); sessionStorage.clear();
        location.replace('login.html?msg=timeout'); return;
      }
      throw new Error(errDetail || 'No autorizado');
    }
    const j = await r.json();
    if(j && j.ok){
      clearInterval(tHandle); stopCamera(); aimOk(true);
      // habilita sesión para app.html (4 horas)
      localStorage.setItem('auth_ok','true');
      localStorage.setItem('auth_expires', String(Date.now()+4*60*60*1000));
      // uid ya estaba guardado en login.js
      location.replace('app.html');
    }else{ throw new Error('QR inválido'); }
  }catch(e){ aimOk(false); msgBox.textContent = 'Error: '+e.message; }
}

// Camera + fallback
const video        = document.getElementById('video');
const scannerBlock = document.getElementById('scannerBlock');
let stream=null, scanning=false, detector=null;
const canvas = document.createElement('canvas'); const ctx = canvas.getContext('2d');

async function startCamera(){
  if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
    setCompat('Tu navegador no expone la cámara. Usa “Tomar foto”.');
    return false;
  }
  try{
    stream = await navigator.mediaDevices.getUserMedia({
      video:{ facingMode:{ideal:'environment'}, width:{ideal:1280}, height:{ideal:720} }, audio:false
    });
  }catch(err){ setCompat('No se pudo acceder a la cámara: '+err.message); return false; }

  video.srcObject = stream; await video.play();
  scannerBlock.style.display = 'block';
  btnCamOn.disabled = true; btnCamOff.disabled = false;
  setCompat('');
  layoutAimBox();

  scanning = true;

  if ('BarcodeDetector' in window){
    try{ detector = new BarcodeDetector({formats:['qr_code']}); requestAnimationFrame(scanLocalLoop); }
    catch{ detector = null; }
  }
  setTimeout(scanServerLoop, 400);
  return true;
}
function stopCamera(){
  scanning=false;
  if(stream){ stream.getTracks().forEach(t=>t.stop()); stream=null; }
  scannerBlock.style.display='none';
  btnCamOn.disabled=false; btnCamOff.disabled=true;
}
btnCamOn.addEventListener('click', startCamera);
btnCamOff.addEventListener('click', stopCamera);
window.addEventListener('resize', layoutAimBox);

async function scanLocalLoop(){
  if(!scanning || !detector) return;
  try{
    const codes = await detector.detect(video);
    if(codes && codes.length){
      const val = (codes[0].rawValue||'').trim();
      if(val){ scanning=false; aimOk(true); await verifyQR(val); return; }
    }
  }catch{}
  requestAnimationFrame(scanLocalLoop);
}
async function scanServerLoop(){
  if(!scanning) return;
  const vw = video.videoWidth||640, vh = video.videoHeight||480;
  canvas.width=vw; canvas.height=vh; ctx.drawImage(video,0,0,vw,vh);
  const blob = await new Promise(res=>canvas.toBlob(res,'image/jpeg',0.85));
  const fd = new FormData(); fd.append('image', blob, 'frame.jpg');
  try{
    const r = await fetch('/api/qr/decode',{method:'POST', body: fd});
    if(r.ok){ const j = await r.json(); if(j && j.value){ scanning=false; aimOk(true); await verifyQR(String(j.value).trim()); return; } }
  }catch{}
  setTimeout(scanServerLoop, 800);
}

// Foto (fallback manual)
fileInput.addEventListener('change', async ev=>{
  const f = ev.target.files && ev.target.files[0]; if(!f) return;
  const fd = new FormData(); fd.append('image', f);
  try{
    const r = await fetch('/api/qr/decode',{method:'POST', body: fd});
    if(r.ok){ const j = await r.json(); if(j && j.value){ aimOk(true); await verifyQR(String(j.value).trim()); return; } }
    msgBox.textContent = 'No se detectó QR en la foto.';
  }catch{ msgBox.textContent = 'Error al procesar la foto.'; }
  finally{ ev.target.value=''; }
});

// Inicio
document.addEventListener('DOMContentLoaded', async ()=>{
  startTimer();
  await startCamera(); // auto
});
window.addEventListener('beforeunload', stopCamera);
