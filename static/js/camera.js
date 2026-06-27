/**
 * camera.js — 摄像头控制与图像采集
 */
(function () {
  'use strict';

  var video = document.getElementById('camera-preview');
  var canvas = document.getElementById('capture-canvas');
  var startBtn = document.getElementById('start-camera-btn');
  var captureBtn = document.getElementById('capture-btn');
  var releaseBtn = document.getElementById('release-camera-btn');
  var confirmBtn = document.getElementById('confirm-camera-btn');
  var cameraSelect = document.getElementById('camera-select');
  var statusDot = document.getElementById('capture-status-dot');
  var statusText = document.getElementById('capture-status-text');
  var placeholder = document.getElementById('camera-placeholder');
  var scanOverlay = document.getElementById('capture-scan-overlay');
  var viewportMeta = document.getElementById('viewport-resolution');

  var stream = null;

  function setStatus(text, active) {
    if (statusText) statusText.textContent = text;
    if (statusDot) {
      statusDot.className = 'capture-status-dot' + (active ? ' pulse-dot' : '');
    }
  }

  function showVideo() {
    if (video) { video.classList.add('active'); video.style.display = 'block'; }
    if (placeholder) placeholder.style.display = 'none';
  }
  function hideVideo() {
    if (video) { video.classList.remove('active'); video.style.display = 'none'; }
    if (placeholder) placeholder.style.display = '';
  }

  if (startBtn) {
    startBtn.addEventListener('click', async function () {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1440 } } });
        if (video) { video.srcObject = stream; video.play(); }
        showVideo();
        setStatus('采集中', true);
        if (startBtn) startBtn.style.display = 'none';
        if (captureBtn) captureBtn.classList.remove('hidden');
        if (releaseBtn) releaseBtn.classList.remove('hidden');
        if (viewportMeta) {
          var track = stream.getVideoTracks()[0];
          var settings = track.getSettings();
          viewportMeta.textContent = (settings.width || '—') + ' × ' + (settings.height || '—');
        }
      } catch (err) {
        setStatus('摄像头不可用', false);
        alert('无法访问摄像头：' + err.message);
      }
    });
  }

  if (captureBtn) {
    captureBtn.addEventListener('click', function () {
      if (!video || !canvas || !stream) return;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      var ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      var dataUrl = canvas.toDataURL('image/png');

      // Show scan overlay briefly
      if (scanOverlay) {
        scanOverlay.classList.remove('hidden');
        setTimeout(function () { scanOverlay.classList.add('hidden'); }, 2500);
      }

      // Display captured image
      var capturedImg = document.getElementById('captured-image');
      var capturedPreview = document.getElementById('captured-preview');
      var frameEmpty = document.getElementById('capture-frame-empty');
      if (capturedImg) capturedImg.src = dataUrl;
      if (capturedPreview) capturedPreview.classList.remove('hidden');
      if (frameEmpty) frameEmpty.classList.add('hidden');

      setStatus('已采集', true);
    });
  }

  if (releaseBtn) {
    releaseBtn.addEventListener('click', function () {
      if (stream) {
        stream.getTracks().forEach(function (t) { t.stop(); });
        stream = null;
      }
      hideVideo();
      setStatus('待机', false);
      if (startBtn) startBtn.style.display = '';
      if (captureBtn) captureBtn.classList.add('hidden');
      if (releaseBtn) releaseBtn.classList.add('hidden');
    });
  }

  // Upload handling
  var uploadInput = document.getElementById('upload-input');
  if (uploadInput) {
    uploadInput.addEventListener('change', function (e) {
      var file = e.target.files[0];
      if (!file) return;
      var reader = new FileReader();
      reader.onload = function (ev) {
        var capturedImg = document.getElementById('captured-image');
        var capturedPreview = document.getElementById('captured-preview');
        var frameEmpty = document.getElementById('capture-frame-empty');
        if (capturedImg) capturedImg.src = ev.target.result;
        if (capturedPreview) capturedPreview.classList.remove('hidden');
        if (frameEmpty) frameEmpty.classList.add('hidden');
        setStatus('已导入', true);
      };
      reader.readAsDataURL(file);
    });
  }

  // Quick actions
  var quickOpen = document.getElementById('quick-open-camera');
  if (quickOpen) quickOpen.addEventListener('click', function () { if (startBtn) startBtn.click(); });

  var quickUpload = document.getElementById('upload-input-quick');
  if (quickUpload) {
    quickUpload.addEventListener('change', function (e) {
      if (uploadInput && e.target.files[0]) {
        var dt = new DataTransfer();
        dt.items.add(e.target.files[0]);
        uploadInput.files = dt.files;
        uploadInput.dispatchEvent(new Event('change'));
      }
    });
  }
})();
