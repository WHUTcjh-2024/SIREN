/**
 * formula_katex.js — KaTeX 公式渲染
 * 如果 KaTeX CDN 可用则渲染，否则保留纯文本占位
 */
(function () {
  'use strict';

  var loaded = false;

  function ensureLoaded(cb) {
    if (loaded || window.katex) { loaded = true; cb(); return; }
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
    document.head.appendChild(link);

    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
    s.onload = function () { loaded = true; cb(); };
    s.onerror = function () { loaded = true; cb(); };
    document.head.appendChild(s);
  }

  function boot(root) {
    if (!window.katex) return;
    var els = root.querySelectorAll('.formula-katex-display[data-tex], .formula-katex-inline[data-tex]');
    els.forEach(function (el) {
      if (el.dataset.rendered) return;
      try {
        katex.render(el.getAttribute('data-tex'), el, {
          throwOnError: false,
          displayMode: el.classList.contains('formula-katex-display')
        });
        el.dataset.rendered = '1';
      } catch (e) { /* keep placeholder */ }
    });
  }

  window.FormulaKatex = { ensureLoaded: ensureLoaded, boot: boot };
})();
