/**
 * pipeline_animation.js — 分析流水线动画
 */
(function () {
  'use strict';

  var STEPS = ['预处理', '标尺识别', '光强提取', 'SIREN 拟合', 'PINN 优化', '结果输出'];
  var currentStep = -1;

  function activateStep(idx) {
    if (idx < 0 || idx >= STEPS.length) return;
    // Mark previous steps as done
    for (var i = 0; i < idx; i++) {
      var card = document.getElementById('pcard-' + i);
      var dot = document.getElementById('pdot-' + i);
      if (card) card.classList.add('card-done');
      if (dot) { dot.style.background = '#10b981'; dot.style.borderColor = '#10b981'; }
    }
    // Activate current
    var card = document.getElementById('pcard-' + idx);
    var dot = document.getElementById('pdot-' + idx);
    if (card) { card.classList.add('card-active'); card.classList.remove('card-done'); }
    if (dot) { dot.classList.add('step-glow'); dot.style.background = '#33b0e5'; dot.style.borderColor = '#33b0e5'; }
    currentStep = idx;
  }

  function completeStep(idx) {
    var card = document.getElementById('pcard-' + idx);
    var dot = document.getElementById('pdot-' + idx);
    if (card) { card.classList.remove('card-active'); card.classList.add('card-done'); }
    if (dot) { dot.classList.remove('step-glow'); dot.style.background = '#10b981'; dot.style.borderColor = '#10b981'; }
  }

  window.PipelineAnimation = {
    activateStep: activateStep,
    completeStep: completeStep,
    STEPS: STEPS
  };
})();
