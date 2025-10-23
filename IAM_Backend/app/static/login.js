// login.js — Autenticación y paso a QR

const alertBox = document.getElementById('alert');
const emailEl  = document.getElementById('email');
const passEl   = document.getElementById('password');
const btn      = document.getElementById('btnLogin');

(function showQSMessage(){
  const msg = new URLSearchParams(location.search).get('msg');
  if(!msg) return;
  const map = {
    timeout: 'Tiempo de autenticación agotado, vuelve a iniciar sesión.',
    loggedout: 'Sesión finalizada.',
    mismatch: 'El QR no pertenece al usuario logueado. Vuelve a iniciar sesión.',
    nosession: 'Sesión no encontrada. Inicia sesión nuevamente.',
    denied: 'Acceso denegado. Inicia sesión.'
  };
  showAlert(map[msg] || msg, msg === 'timeout' ? 'error' : 'info');
})();

function showAlert(text, kind='error'){
  alertBox.textContent = text;
  alertBox.className = `alert ${kind}`;
  alertBox.style.display = 'block';
}

async function doLogin(){
  const email = (emailEl.value || '').trim();
  const password = passEl.value || '';
  if(!email || !password){
    showAlert('Ingresa correo y contraseña.', 'error'); return;
  }
  btn.disabled = true;

  try{
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ email, password })
    });
    if(!r.ok){
      const e = await r.json().catch(()=>({detail:'Credenciales inválidas'}));
      throw new Error(e.detail || 'Error de autenticación');
    }
    const data = await r.json();
    // Esperado: { uid, rol, session_id, expires_at }
    const uid = data.uid;
    const rol = data.rol;
    const sessId = data.session_id;

    let expMs = 0;
    if (typeof data.expires_at === 'number') {
      expMs = data.expires_at > 10_000_000_000 ? data.expires_at : data.expires_at * 1000;
    } else if (typeof data.expires_at === 'string') {
      const t = Date.parse(data.expires_at); expMs = isNaN(t)?0:t;
    }

    if(!uid || !rol || !sessId || !expMs) throw new Error('Respuesta de sesión inválida');

    // Para QR (sesión corta)
    sessionStorage.setItem('session_id', sessId);
    sessionStorage.setItem('expires_at', String(expMs));
    sessionStorage.setItem('uid', uid);

    // Para panel (se completará tras QR OK)
    localStorage.setItem('uid', uid);
    localStorage.setItem('rol', rol);
    localStorage.removeItem('auth_ok');
    localStorage.removeItem('auth_expires');

    location.replace('qr.html');
  }catch(e){
    showAlert(e.message || 'Error de autenticación', 'error');
  }finally{
    btn.disabled = false;
  }
}

btn.addEventListener('click', doLogin);
passEl.addEventListener('keydown', (ev)=>{ if(ev.key==='Enter') doLogin(); });
