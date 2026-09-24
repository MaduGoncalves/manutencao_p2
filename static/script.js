const U = '/api/q';

async function z(u) {
  try {
    const r = await fetch(U + u, { method: u ? 'POST' : 'GET' });
    d(await r.json());
  } catch (e) { console.error(e); }
}

function y() {
  const v = parseFloat(document.getElementById('q').value);
  if (!isNaN(v) && v >= 0) z('/m/' + Math.round(v * 60));
}

function h(ms) {
  const s = Math.ceil(ms / 1000);
  return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
}

function d(o) {
  document.getElementById('p0').textContent = o.p[0];
  document.getElementById('p1').textContent = o.p[1];
  document.getElementById('f0').textContent = o.f[0];
  document.getElementById('f1').textContent = o.f[1];
  const e = document.getElementById('t0');
  e.textContent = h(o.t);
  e.classList.toggle('z', o.t === 0);
}

z('');
setInterval(() => z(''), 500);
