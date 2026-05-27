function calcFund(slotValue, rate){
  const slots = Number(document.getElementById('slots')?.value || 0);
  const principal = slots * Number(slotValue);
  const maturity = principal * (1 + Number(rate)/100);
  const principalEl = document.getElementById('principalPreview');
  const maturityEl = document.getElementById('maturityPreview');
  if(principalEl) principalEl.textContent = principal.toLocaleString('en-IN',{style:'currency',currency:'INR'});
  if(maturityEl) maturityEl.textContent = maturity.toLocaleString('en-IN',{style:'currency',currency:'INR'});
}

function startQrTimer(){
  const status = document.getElementById('qrStatus');
  if(!status) return;
  const exp = new Date(status.dataset.exp).getTime();
  const regen = new Date(status.dataset.regen).getTime();
  const btn = document.getElementById('refreshQrBtn');
  function tick(){
    const now = Date.now();
    const expLeft = Math.max(0, Math.floor((exp - now)/1000));
    const regenLeft = Math.max(0, Math.floor((regen - now)/1000));
    if(expLeft > 0){
      status.innerHTML = `QR valid for <b>${expLeft}s</b>`;
      status.className = 'qr-status live';
    } else {
      status.innerHTML = regenLeft > 0 ? `QR expired. Fresh QR unlocks in <b>${regenLeft}s</b>` : 'QR expired. Generate a fresh QR.';
      status.className = 'qr-status expired';
    }
    if(btn){ btn.disabled = regenLeft > 0; btn.textContent = regenLeft > 0 ? `Fresh QR in ${regenLeft}s` : 'Generate fresh QR'; }
  }
  tick(); setInterval(tick, 1000);
}

document.addEventListener('DOMContentLoaded', startQrTimer);
