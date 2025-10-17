function showToast(msg){
  const t=document.getElementById('toast');
  if(!t) return;
  t.textContent=msg;
  t.style.display='block';
  setTimeout(()=>t.style.display='none',2500);
}
async function postJSON(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const ct = r.headers.get('content-type')||'';
  const data = ct.includes('application/json')? await r.json(): await r.text();
  if(!r.ok){ throw new Error((data && data.detail) || r.statusText); }
  return data;
}
