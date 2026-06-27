/**
 * data_processing.js — 数据处理与计算
 */
(function () {
  'use strict';

  var PI = Math.PI;
  var LAMBDA = 632.8e-9; // 632.8 nm

  // --- Single calculation ---
  var calcBtn = document.getElementById('calculateBtn');
  if (calcBtn) {
    calcBtn.addEventListener('click', function () {
      var f = parseFloat(document.getElementById('f').value);
      var deltaX = parseFloat(document.getElementById('deltaX').value);
      var H0 = parseFloat(document.getElementById('H0').value);
      var h = parseFloat(document.getElementById('h').value);
      var L = parseFloat(document.getElementById('L').value);
      var rho = parseFloat(document.getElementById('rho').value);
      var sigma0 = parseFloat(document.getElementById('sigma0').value);

      if ([f, deltaX, H0, h, L, rho].some(isNaN) || f <= 0 || deltaX <= 0 || L <= 0) {
        alert('请填写所有必填参数（标准值可选）');
        return;
      }

      var omega = 2 * PI * f;
      var H = H0 - h;
      var alpha = Math.atan(H / L);
      var beta = Math.atan((deltaX + H) / L);
      var delta = beta - alpha;

      var k = (2 * PI / LAMBDA) * Math.sin(delta / 2) *
        (Math.sin(alpha + delta / 2) + Math.sin(alpha - delta / 2));

      var sigma = rho * omega * omega / (k * k * k);

      document.getElementById('resultDelta').textContent = (delta * 180 / PI).toFixed(4) + '°';
      document.getElementById('resultK').textContent = k.toFixed(2);
      document.getElementById('resultSigma').textContent = sigma.toFixed(6);

      if (!isNaN(sigma0) && sigma0 > 0) {
        var err = Math.abs(sigma - sigma0) / sigma0 * 100;
        document.getElementById('resultError').textContent = err.toFixed(2) + '%';
      } else {
        document.getElementById('resultError').textContent = '—';
      }

      var results = document.getElementById('calculateResults');
      if (results) results.classList.remove('hidden');

      if (window.ExperimentSession) {
        window.ExperimentSession.markStepDone('process');
        window.ExperimentSession.addActivity('完成表面张力计算');
      }
    });
  }

  // --- Add data row ---
  var addBtn = document.getElementById('addDataBtn');
  var dataInputs = document.getElementById('dataInputs');
  if (addBtn && dataInputs) {
    addBtn.addEventListener('click', function () {
      var row = document.createElement('div');
      row.className = 'process-data-row';
      row.innerHTML =
        '<div class="process-field"><label>波数 <span class="unit">k (m⁻¹)</span></label><input type="number" class="k-input" placeholder="请输入实验数据"></div>' +
        '<div class="process-field"><label>频率 <span class="unit">f (Hz)</span></label><input type="number" class="f-input" placeholder="请输入实验数据"></div>' +
        '<button type="button" class="process-data-remove remove-data-btn" aria-label="删除行"><i class="fa fa-times"></i></button>';
      dataInputs.appendChild(row);
      row.querySelector('.remove-data-btn').addEventListener('click', function () {
        if (dataInputs.children.length > 1) row.remove();
      });
    });
  }

  // Remove existing rows
  document.querySelectorAll('.remove-data-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var row = this.closest('.process-data-row');
      if (row && dataInputs && dataInputs.children.length > 1) row.remove();
    });
  });

  // --- Fit calculation ---
  var fitBtn = document.getElementById('fitBtn');
  if (fitBtn) {
    fitBtn.addEventListener('click', function () {
      var kInputs = document.querySelectorAll('.k-input');
      var fInputs = document.querySelectorAll('.f-input');
      var rho = parseFloat(document.getElementById('fitRho').value) || 1000;
      var sigma0 = parseFloat(document.getElementById('fitSigma0').value);

      var kArr = [], fArr = [];
      kInputs.forEach(function (inp, i) {
        var k = parseFloat(inp.value);
        var f = parseFloat(fInputs[i] && fInputs[i].value);
        if (!isNaN(k) && !isNaN(f) && k > 0 && f > 0) {
          kArr.push(k);
          fArr.push(f);
        }
      });

      if (kArr.length < 2) {
        alert('请至少输入 2 组有效数据');
        return;
      }

      // Linear fit: omega = a * k^(3/2) => ln(omega) = ln(a) + 1.5*ln(k)
      var lnK = kArr.map(function (k) { return Math.log(k); });
      var lnOmega = fArr.map(function (f) { return Math.log(2 * PI * f); });

      var n = lnK.length;
      var sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
      for (var i = 0; i < n; i++) {
        sumX += lnK[i];
        sumY += lnOmega[i];
        sumXY += lnK[i] * lnOmega[i];
        sumX2 += lnK[i] * lnK[i];
      }
      var slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
      var intercept = (sumY - slope * sumX) / n;
      var a = Math.exp(intercept);

      var sigma = rho * a * a / 4;

      // R²
      var meanY = sumY / n;
      var ssTot = 0, ssRes = 0;
      for (var i = 0; i < n; i++) {
        var pred = intercept + slope * lnK[i];
        ssRes += (lnOmega[i] - pred) * (lnOmega[i] - pred);
        ssTot += (lnOmega[i] - meanY) * (lnOmega[i] - meanY);
      }
      var r2 = 1 - ssRes / ssTot;

      document.getElementById('fitParamA').textContent = a.toFixed(6);
      document.getElementById('fitSigma').textContent = sigma.toFixed(6);
      document.getElementById('fitR2').textContent = r2.toFixed(6);

      if (!isNaN(sigma0) && sigma0 > 0) {
        var err = Math.abs(sigma - sigma0) / sigma0 * 100;
        document.getElementById('fitError').textContent = err.toFixed(2) + '%';
      } else {
        document.getElementById('fitError').textContent = '—';
      }

      var fitResults = document.getElementById('fitResults');
      if (fitResults) fitResults.classList.remove('hidden');
    });
  }

  // --- Compare ---
  var compareManual = document.getElementById('manual-deltaX');
  if (compareManual) {
    compareManual.addEventListener('input', function () {
      var aiVal = parseFloat(document.getElementById('compare-ai-dx') && document.getElementById('compare-ai-dx').textContent);
      var manualVal = parseFloat(this.value);
      if (!isNaN(aiVal) && !isNaN(manualVal) && manualVal > 0) {
        var diff = Math.abs(aiVal - manualVal) / manualVal * 100;
        document.getElementById('compare-diff-pct').textContent = diff.toFixed(2) + '%';
      }
    });
  }
})();
