/**
 * analysis.js — 分析引擎（模拟）
 */
(function () {
  'use strict');

  var analyzeBtn = document.getElementById('analyze-btn-ready');
  var loadingEl = document.getElementById('loading');
  var loadingBar = document.getElementById('loading-bar');
  var loadingElapsed = document.getElementById('loading-elapsed');
  var loadingHint = document.getElementById('loading-hint');
  var chartsSection = document.getElementById('charts-section');
  var resultsSection = document.getElementById('results');

  function showLoading() {
    if (loadingEl) loadingEl.classList.remove('hidden');
  }
  function hideLoading() {
    if (loadingEl) loadingEl.classList.add('hidden');
  }

  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', function () {
      showLoading();
      var start = Date.now();
      var hints = [
        '初始化分析引擎...',
        '加载 SIREN 模型...',
        'PINNs 物理约束校验...',
        '亚像素寻峰计算中...',
        '生成测量结果...'
      ];
      var step = 0;
      var timer = setInterval(function () {
        var elapsed = ((Date.now() - start) / 1000).toFixed(1);
        if (loadingElapsed) loadingElapsed.textContent = elapsed + 's';
        var pct = Math.min(95, (elapsed / 8) * 100);
        if (loadingBar) loadingBar.style.width = pct + '%';
        var newStep = Math.min(hints.length - 1, Math.floor(elapsed / 1.6));
        if (newStep !== step) {
          step = newStep;
          if (loadingHint) loadingHint.textContent = hints[step];
          if (window.PipelineAnimation) {
            window.PipelineAnimation.activateStep(step);
          }
        }
        if (elapsed >= 8) {
          clearInterval(timer);
          if (loadingBar) loadingBar.style.width = '100%';
          if (loadingHint) loadingHint.textContent = '分析完成！';
          setTimeout(function () {
            hideLoading();
            if (chartsSection) chartsSection.classList.remove('hidden');
            if (resultsSection) resultsSection.classList.remove('hidden');
            if (window.ExperimentSession) {
              window.ExperimentSession.markStepDone('capture');
              window.ExperimentSession.addActivity('完成静态图像采集分析');
            }
          }, 500);
        }
      }, 100);
    });
  }
})();
