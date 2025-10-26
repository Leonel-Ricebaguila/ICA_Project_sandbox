document.getElementById('btnLogin').addEventListener('click', async () => {
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  try{
    const out = await postJSON('/api/auth/login', {email, password});
    sessionStorage.setItem('session_id', out.session_id);
    sessionStorage.setItem('expires_at', String(out.expires_at*1000));
    location.replace('qr.html');
  }catch(e){
    showToast('Error: '+e.message);
    document.getElementById('msg').textContent = 'Credenciales inválidas o servidor no disponible.';
  }
});
