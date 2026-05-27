function calcFund(slotValue, rate){
  const slots = Number(document.getElementById('slots')?.value || 0);
  const principal = slots * Number(slotValue);
  const maturity = principal * (1 + Number(rate)/100);
  const principalEl = document.getElementById('principalPreview');
  const maturityEl = document.getElementById('maturityPreview');
  if(principalEl) principalEl.textContent = principal.toLocaleString('en-IN',{style:'currency',currency:'INR'});
  if(maturityEl) maturityEl.textContent = maturity.toLocaleString('en-IN',{style:'currency',currency:'INR'});
}
