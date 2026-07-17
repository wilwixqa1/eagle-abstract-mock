document.addEventListener('DOMContentLoaded', function(){
  var t = document.querySelector('.navtoggle');
  var n = document.querySelector('.nav nav');
  if(!t || !n) return;
  t.addEventListener('click', function(){
    var open = n.classList.toggle('open');
    t.setAttribute('aria-expanded', open);
  });
});
