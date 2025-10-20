(function(){
  const ok = localStorage.getItem('auth_ok') === 'true';
  const exp = parseInt(localStorage.getItem('auth_expires')||'0',10);
  if(!ok || Date.now() >= exp){
    localStorage.clear();
    location.replace('login.html');
  }
})();
