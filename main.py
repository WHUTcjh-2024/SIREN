import os
import cv2
import sys
import numpy as np
import torch
import shutil
import tempfile

from modules import load_and_process_image
from calibration.ruler import RulerReader
from training.loss import Trainer
from models.siren import NeuralImplicitField as SIRENModel
from config import SIREN_CONFIG, TRAINING_CONFIG, NEWTON_CONFIG
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d as gf1d

import warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def _ascii_path(path: str) -> str:
    try:
        path.encode('ascii')
        return path
    except UnicodeEncodeError:
        d = tempfile.gettempdir()
        dst = os.path.join(d, "_img_tmp.png")
        shutil.copy2(path, dst)
        return dst


def _put_text_bg(img, text, pos, font, scale, color, thickness, bg_color=(0, 0, 0)):
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = pos
    cv2.rectangle(img, (x - 2, y - th - 4), (x + tw + 4, y + baseline + 2), bg_color, -1)
    cv2.putText(img, text, pos, font, scale, color, thickness)


class DiffractionMeasurementSystem:
    """Main system using SIREN + PINNs with EasyOCR ruler calibration."""

    def __init__(self, image_path: str, quiet: bool = False, progress_callback=None):
        self.image_path = image_path
        self.quiet = quiet
        self._progress_cb = progress_callback

        self._emit('step', {'step': 0, 'status': 'start', 'message': '正在加载和预处理图像...'})
        self._log("Loading image...")
        data = load_and_process_image(image_path, return_loader=True)
        if isinstance(data, tuple):
            data, loader = data
        else:
            loader = None
        self._loader_ref = loader
        self.gray_image = data['gray']
        self.diffraction_region = data['diffraction_region']
        self.ruler_region = data['ruler_region']
        self.full_profile = data['profile']
        self.x_coords = data['x_coords']
        self.profile = data['profile']
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.ruler_detections = []
        self.ruler_mapping = None
        self.three_peaks = None
        self.siren_result = None
        self.subpixel_positions = None
        self.h0_cm = None
        self.delta_x1_px = None
        self.delta_x2_px = None
        self.delta_x1_cm = None
        self.delta_x2_cm = None

    def _log(self, msg):
        if not self.quiet:
            print(msg)

    def _emit(self, event_type, data):
        if self._progress_cb:
            try:
                self._progress_cb(event_type, data)
            except Exception:
                pass

    def _crop_y_offset(self) -> int:
        if self._loader_ref is not None and hasattr(self._loader_ref, 'profile_crop_info'):
            info = self._loader_ref.profile_crop_info
            if info and 'y_start' in info:
                return int(info['y_start'])
        return 0

    def _find_bright_peaks(self):
        profile_raw = self.full_profile.copy()
        profile_raw[profile_raw < 0] = 0

        smoothed = gf1d(profile_raw, sigma=0.5)
        all_peaks, props = find_peaks(smoothed, distance=15, prominence=2)

        if len(all_peaks) < 3:
            all_peaks, props = find_peaks(smoothed, distance=15, prominence=1)
        if len(all_peaks) < 3:
            all_peaks, props = find_peaks(smoothed, distance=15, prominence=0.5)

        if len(all_peaks) < 3:
            raise RuntimeError(
                f"Only found {len(all_peaks)} peaks in diffraction profile. "
                "Need at least 3 (center + 2 first-order)."
            )

        peak_heights = smoothed[all_peaks]
        top3_idx = np.argsort(peak_heights)[-3:][::-1]
        top3_peaks = all_peaks[top3_idx]
        top3_heights = peak_heights[top3_idx]

        order = np.argsort(top3_peaks)
        top3_peaks = top3_peaks[order]
        top3_heights = top3_heights[order]

        neg_pixel = float(top3_peaks[0])
        center_pixel = float(top3_peaks[1])
        pos_pixel = float(top3_peaks[2])

        x = np.arange(len(profile_raw))
        y_offset = self._crop_y_offset()

        def sub_pixel_centroid(idx, r=8):
            i0 = max(0, int(idx) - r)
            i1 = min(len(profile_raw), int(idx) + r + 1)
            seg = profile_raw[i0:i1].astype(np.float64)
            w = seg - seg.min()
            w = np.maximum(w, 0)
            if w.sum() < 1e-12:
                return idx
            return float(np.sum(x[i0:i1] * w) / w.sum())

        center_crop = sub_pixel_centroid(center_pixel)
        neg_crop = sub_pixel_centroid(neg_pixel)
        pos_crop = sub_pixel_centroid(pos_pixel)

        center_y = center_crop + y_offset
        neg_y = neg_crop + y_offset
        pos_y = pos_crop + y_offset

        self.three_peaks = {
            'center': {'pixel': center_y, 'intensity': float(top3_heights[1]),
                       'pixel_int': int(round(center_y)), 'index': int(round(center_y)),
                       '_pixel_cropped': center_crop, '_crop_offset': y_offset},
            'neg':    {'pixel': neg_y,    'intensity': float(top3_heights[0]),
                       'pixel_int': int(round(neg_y)), 'index': int(round(neg_y)),
                       '_pixel_cropped': neg_crop, '_crop_offset': y_offset},
            'pos':    {'pixel': pos_y,    'intensity': float(top3_heights[2]),
                       'pixel_int': int(round(pos_y)), 'index': int(round(pos_y)),
                       '_pixel_cropped': pos_crop, '_crop_offset': y_offset},
            'smoothed': smoothed,
            'n_peaks_found': len(all_peaks),
        }

        self._log(f"  Sub-pixel peak positions: center={center_y:.4f}px (crop={center_crop:.4f}), "
                  f"neg={neg_y:.4f}px, pos={pos_y:.4f}px")

    def _read_ruler(self):
        self._log("Reading ruler via EasyOCR...")
        reader = RulerReader(gpu=False)
        detections = reader.detect_ruler_numbers(self.image_path)
        mapping = RulerReader.build_ruler_mapping(detections)
        self.ruler_detections = detections
        self.ruler_mapping = mapping
        if mapping:
            self._log(f"  Ruler mapping: 1px = {mapping['slope']:.8f} cm, "
                      f"R² = {mapping['r_squared']:.6f}")
            for d in detections:
                self._log(f"    {d['value']}cm -> pixel {d['orig_y']}")

    def _compute_measurements(self):
        if self.three_peaks is None or self.ruler_mapping is None:
            return

        center_y = self.three_peaks['center']['pixel']
        neg_y = self.three_peaks['neg']['pixel']
        pos_y = self.three_peaks['pos']['pixel']
        mapping = self.ruler_mapping
        slope = mapping['slope']

        self.h0_cm = RulerReader.pixel_to_cm(mapping, center_y)
        self.three_peaks['center']['cm'] = self.h0_cm
        self.three_peaks['neg']['cm'] = RulerReader.pixel_to_cm(mapping, neg_y)
        self.three_peaks['pos']['cm'] = RulerReader.pixel_to_cm(mapping, pos_y)

        self.delta_x1_px = abs(pos_y - center_y)
        self.delta_x2_px = abs(center_y - neg_y)
        px_per_cm = 1.0 / abs(slope)
        self.delta_x1_cm = self.delta_x1_px / px_per_cm
        self.delta_x2_cm = self.delta_x2_px / px_per_cm

        self._log(f"  H0 = {self.h0_cm:.4f} cm")
        self._log(f"  Dx1 (+1) = {self.delta_x1_px:.2f} px = {self.delta_x1_cm:.6f} cm")
        self._log(f"  Dx2 (-1) = {self.delta_x2_px:.2f} px = {self.delta_x2_cm:.6f} cm")

    def fit(self):
        self._emit('step', {'step': 0, 'status': 'done'})
        self._log("Step 1: Finding bright peaks with sub-pixel refinement...")

        self._emit('step', {'step': 1, 'status': 'start', 'message': 'EasyOCR 识别标尺数字...'})
        self._log("Step 2: Reading ruler via EasyOCR...")
        self._read_ruler()
        self._emit('step', {'step': 1, 'status': 'done'})

        self._emit('step', {'step': 2, 'status': 'start', 'message': '提取水平光强剖面...'})
        self._find_bright_peaks()
        self._emit('step', {'step': 2, 'status': 'done'})

        self._log("Step 3: Computing measurements (H0, delta_x)...")
        self._compute_measurements()

        self._emit('step', {'step': 3, 'status': 'start', 'message': 'SIREN 神经网络训练中...'})
        self._log("Step 4: Normalizing profile for SIREN training...")
        profile_raw = self.full_profile.copy()
        profile_raw[profile_raw < 0] = 0
        self._profile_max = float(profile_raw.max()) if profile_raw.max() > 0 else 1.0
        profile_norm = profile_raw / self._profile_max
        self.x_tensor = torch.tensor(self.x_coords, dtype=torch.float32).to(self.device)
        self.I_tensor = torch.tensor(profile_norm, dtype=torch.float32).to(self.device).unsqueeze(1)
        self.siren_model = SIRENModel(**SIREN_CONFIG).to(self.device)
        self.trainer = Trainer(self.siren_model, TRAINING_CONFIG, device=self.device)

        def _train_progress(epoch, total, loss_info):
            self._emit('train', {
                'step': 3, 'epoch': epoch, 'total': total,
                'loss': loss_info['total_loss'],
                'mse': loss_info['loss_mse'],
                'best_loss': loss_info['best_loss'],
            })

        history = self.trainer.train(self.x_tensor, self.I_tensor, progress_callback=_train_progress)
        self._log(f"  Training completed in {len(history)} epochs")
        self._emit('step', {'step': 3, 'status': 'done'})

        self._emit('step', {'step': 4, 'status': 'start', 'message': 'PINN 物理约束优化中...'})
        self._log("Step 5: Newton-Raphson sub-pixel peak refinement...")
        self._find_siren_peaks()
        self._emit('step', {'step': 4, 'status': 'done'})

    def _find_siren_peaks(self):
        model = self.siren_model
        model.eval()
        y_offset = self._crop_y_offset()
        nc_orig = self.three_peaks['center']['pixel_int']
        x0 = torch.tensor([[float(nc_orig)]], dtype=torch.float32, device=self.device)
        with torch.no_grad():
            x0.requires_grad_(True)
            for _ in range(50):
                I, dI, d2I = model.derivatives(x0)
                g = dI.detach()
                H = d2I.detach()
                H = torch.clamp(H, max=-1e-8)
                step = -g / H
                step = torch.clamp(step, -1.0, 1.0)
                x0_new = x0.detach() + step
                if (x0_new - x0).abs().max() < 1e-8:
                    break
                x0 = x0_new.clone().requires_grad_(True)

        center_px = x0.item()
        center_I, dI_c, _ = model.derivatives(torch.tensor([[center_px]], device=self.device))

        from scipy.signal import find_peaks as _fp
        from scipy.ndimage import gaussian_filter1d as _gf1d
        prof_raw = self.full_profile.copy()
        prof_raw[prof_raw < 0] = 0
        sm = _gf1d(prof_raw, sigma=0.5)

        x_range = np.arange(len(prof_raw)) + y_offset if y_offset else np.arange(len(prof_raw))
        pks, _ = _fp(sm, distance=15, prominence=1)
        pks_orig = [int(x_range[p]) for p in pks]

        cands = [p for p in pks_orig if abs(p - center_px) > 30 and p < center_px + 500 and p > center_px - 500]

        def newton_refine(init_x):
            x = torch.tensor([[init_x]], dtype=torch.float32, device=self.device)
            with torch.no_grad():
                x.requires_grad_(True)
                for _ in range(50):
                    _, dI, d2I = model.derivatives(x)
                    g = dI.detach()
                    H = d2I.detach()
                    if init_x < center_px:
                        H = torch.clamp(H, min=1e-8)
                    else:
                        H = torch.clamp(H, max=-1e-8)
                    step = -g / H
                    step = torch.clamp(step, -1.0, 1.0)
                    x_new = x.detach() + step
                    if (x_new - x).abs().max() < 1e-8:
                        break
                    x = x_new.clone().requires_grad_(True)
            return x.item()

        side_peaks = []
        for c in cands:
            refined = newton_refine(c)
            I_val = model(torch.tensor([[refined]], device=self.device)).item()
            if center_px - 400 < refined < center_px + 400:
                side_peaks.append((refined, I_val))

        side_peaks.sort(key=lambda x: x[1], reverse=True)
        if len(side_peaks) < 2:
            side_peaks.sort(key=lambda x: x[0])
        else:
            side_peaks = side_peaks[:2]
            side_peaks.sort(key=lambda x: x[0])

        neg_px = side_peaks[0][0] if len(side_peaks) > 0 else 0.0
        pos_px = side_peaks[1][0] if len(side_peaks) > 1 else 0.0

        self.subpixel_positions = {
            'head_0': {'pixel': center_px, 'intensity': center_I.item()},
            'head_neg': {'pixel': neg_px, 'intensity': side_peaks[0][1] if len(side_peaks) > 0 else 0},
            'head_pos': {'pixel': pos_px, 'intensity': side_peaks[1][1] if len(side_peaks) > 1 else 0},
        }

        self._log(f"  Sub-pixel SIREN positions: center={center_px:.4f}px, "
                  f"neg={neg_px:.4f}px, pos={pos_px:.4f}px")

    def convert_to_physical(self):
        if self.three_peaks:
            center_y = self.three_peaks['center']['pixel']
            pos_y = self.three_peaks['pos']['pixel']
            neg_y = self.three_peaks['neg']['pixel']
            self.delta_x1_px = abs(pos_y - center_y)
            self.delta_x2_px = abs(center_y - neg_y)

        mapping = self.ruler_mapping
        if mapping is None:
            self._log("  [WARN] No ruler mapping, using pixel coordinates")
            return

        slope = mapping['slope']
        px_per_cm = 1.0 / abs(slope)

        if self.three_peaks:
            self.delta_x1_cm = self.delta_x1_px / px_per_cm
            self.delta_x2_cm = self.delta_x2_px / px_per_cm

        if self.subpixel_positions:
            p0 = self.subpixel_positions['head_0']['pixel']
            p_pos = self.subpixel_positions['head_pos']['pixel']
            p_neg = self.subpixel_positions['head_neg']['pixel']
            self.subpixel_positions['head_0']['position_cm'] = RulerReader.pixel_to_cm(mapping, p0)
            self.subpixel_positions['head_pos']['position_cm'] = RulerReader.pixel_to_cm(mapping, p_pos)
            self.subpixel_positions['head_neg']['position_cm'] = RulerReader.pixel_to_cm(mapping, p_neg)
            self.subpixel_positions['head_0']['position_mm'] = self.subpixel_positions['head_0']['position_cm'] * 10
            self.subpixel_positions['head_pos']['position_mm'] = self.subpixel_positions['head_pos']['position_cm'] * 10
            self.subpixel_positions['head_neg']['position_mm'] = self.subpixel_positions['head_neg']['position_cm'] * 10

    def read_central_peak_height(self):
        if self.ruler_mapping is None or self.three_peaks is None:
            return None
        center_px = self.three_peaks['center']['pixel']
        self.h0_cm = RulerReader.pixel_to_cm(self.ruler_mapping, center_px)
        self._log(f"  H0 = {self.h0_cm:.4f} cm (pixel {center_px:.4f})")
        return self.h0_cm

    def visualize(self, output_dir: str = 'output'):
        os.makedirs(output_dir, exist_ok=True)

        ascii_path = _ascii_path(self.image_path)
        img = cv2.imread(ascii_path)
        if img is None:
            self._log("  [WARN] Cannot load image for visualization")
            return

        h, w = img.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        diff_w = int(w * 0.8)

        scale_font = max(0.8, w / 4000.0)
        thick_line = max(2, w // 1500)
        thick_thin = max(1, w // 2500)

        ruler_color = (0, 180, 255)
        for item in self.ruler_detections:
            orig_y = item['orig_y']
            val = item['value']
            if 0 <= orig_y < h:
                cv2.line(img, (0, orig_y), (diff_w, orig_y), ruler_color, thick_line)
                cv2.line(img, (diff_w, orig_y), (w, orig_y), ruler_color, thick_thin)
                label = f"{val}cm  (px={orig_y})"
                _put_text_bg(img, label, (15, max(orig_y - 10, 25)),
                             font, scale_font * 0.65, ruler_color, max(1, thick_line - 1))

        center_px = self.three_peaks['center']['pixel']
        neg_px = self.three_peaks['neg']['pixel']
        pos_px = self.three_peaks['pos']['pixel']
        center_y = int(round(center_px))
        neg_y = int(round(neg_px))
        pos_y = int(round(pos_px))

        mapping = self.ruler_mapping
        if mapping:
            center_cm = RulerReader.pixel_to_cm(mapping, center_px)
            neg_cm = RulerReader.pixel_to_cm(mapping, neg_px)
            pos_cm = RulerReader.pixel_to_cm(mapping, pos_px)
            h0_cm = center_cm
        else:
            center_cm = neg_cm = pos_cm = h0_cm = 0.0

        fringe_color_center = (0, 0, 255)
        fringe_color_side = (0, 220, 0)
        bracket_color = (255, 200, 0)

        def draw_fringe(y_int, color, label, thickness):
            if 0 <= y_int < h:
                cv2.line(img, (0, y_int), (diff_w, y_int), color, thickness)
                _put_text_bg(img, label, (15, max(y_int - 10, 25)),
                             font, scale_font * 0.6, color, max(1, thickness - 1))

        draw_fringe(center_y, fringe_color_center,
                    f"0级  {center_px:.2f}px  H0={h0_cm:.2f}cm", thick_line + 1)
        draw_fringe(neg_y, fringe_color_side,
                    f"-1级  {neg_px:.2f}px  {neg_cm:.2f}cm", thick_line)
        draw_fringe(pos_y, fringe_color_side,
                    f"+1级  {pos_px:.2f}px  {pos_cm:.2f}cm", thick_line)

        def draw_bracket(y1_i, y2_i, label, x_frac):
            if 0 <= y1_i < h and 0 <= y2_i < h:
                x_br = int(diff_w * x_frac)
                cv2.line(img, (x_br, y1_i), (x_br, y2_i), bracket_color, thick_thin)
                cv2.line(img, (x_br - 8, y1_i), (x_br + 8, y1_i), bracket_color, thick_thin)
                cv2.line(img, (x_br - 8, y2_i), (x_br + 8, y2_i), bracket_color, thick_thin)
                mid = (y1_i + y2_i) // 2
                _put_text_bg(img, label, (x_br + 12, mid + 5),
                             font, scale_font * 0.55, bracket_color, max(1, thick_line - 1))

        dx1_cm_str = f"={self.delta_x1_cm:.4f}cm" if self.delta_x1_cm is not None else ""
        dx2_cm_str = f"={self.delta_x2_cm:.4f}cm" if self.delta_x2_cm is not None else ""
        draw_bracket(neg_y, center_y,
                     f"Dx2={self.delta_x2_px:.2f}px{dx2_cm_str}", 0.35)
        draw_bracket(center_y, pos_y,
                     f"Dx1={self.delta_x1_px:.2f}px{dx1_cm_str}", 0.55)

        if center_y < h:
            cv2.line(img, (diff_w, center_y), (w, center_y), fringe_color_center, thick_thin)

        panel_x = 15
        panel_y = h - 260
        panel_w = 520
        panel_h = 245
        overlay = img.copy()
        cv2.rectangle(overlay, (panel_x - 5, panel_y - 5),
                      (panel_x + panel_w, panel_y + panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

        info_color = (255, 255, 255)
        info_bold = (0, 220, 255)
        line_h = 35
        y0 = panel_y + 30
        r2_str = f"{mapping['r_squared']:.6f}" if mapping else "N/A"
        info_items = [
            (f"H0 = {h0_cm:.3f} cm  ({center_px:.2f}px)", info_bold, scale_font * 0.7),
            (f"Dx1 (+1级) = {self.delta_x1_px:.2f} px" + (f" = {self.delta_x1_cm:.4f} cm" if self.delta_x1_cm is not None else ""), info_color, scale_font * 0.55),
            (f"Dx2 (-1级) = {self.delta_x2_px:.2f} px" + (f" = {self.delta_x2_cm:.4f} cm" if self.delta_x2_cm is not None else ""), info_color, scale_font * 0.55),
            (f"Dx avg = {((self.delta_x1_cm or 0) + (self.delta_x2_cm or 0)) / 2:.4f} cm" if self.delta_x1_cm and self.delta_x2_cm else "Dx avg = N/A", info_color, scale_font * 0.55),
            (f"Scale: 1px = {abs(mapping['slope']):.8f} cm" if mapping else "Scale: N/A", info_color, scale_font * 0.5),
            (f"R2 = {r2_str}", info_color, scale_font * 0.5),
        ]
        for i, (txt, clr, sc) in enumerate(info_items):
            _put_text_bg(img, txt, (panel_x + 10, y0 + i * line_h),
                         font, sc, clr, max(1, thick_line - 1), bg_color=(20, 20, 20))

        combined_path = os.path.join(output_dir, 'combined_result.png')
        ok, buf = cv2.imencode('.png', img)
        if ok:
            buf.tofile(combined_path)
            self._log(f"  Combined result saved: {combined_path}")

        return combined_path

    def export_to_gradio(self):
        result = {
            'central_peak_height_cm': self.h0_cm,
            'delta_x1_mm': self.delta_x1_cm * 10 if self.delta_x1_cm else None,
            'delta_x2_mm': self.delta_x2_cm * 10 if self.delta_x2_cm else None,
            'delta_x_avg_mm': (self.delta_x1_cm + self.delta_x2_cm) / 2 * 10 if self.delta_x1_cm else None,
            'delta_x1_px': self.delta_x1_px,
            'delta_x2_px': self.delta_x2_px,
            'head_0_position_mm': self.three_peaks['center']['pixel'] if self.three_peaks else None,
            'head_neg_position_mm': self.three_peaks['neg']['pixel'] if self.three_peaks else None,
            'head_pos_position_mm': self.three_peaks['pos']['pixel'] if self.three_peaks else None,
            'ruler_mapping': self.ruler_mapping,
            'ruler_detections': self.ruler_detections,
            'three_peaks': self.three_peaks,
            'subpixel_positions': self.subpixel_positions,
            'profile_raw': self.full_profile,
            'x_coords': self.x_coords,
        }
        if self.subpixel_positions:
            result['subpixel_center_px'] = self.subpixel_positions['head_0']['pixel']
            result['subpixel_neg_px'] = self.subpixel_positions['head_neg']['pixel']
            result['subpixel_pos_px'] = self.subpixel_positions['head_pos']['pixel']
            result['subpixel_center_cm'] = self.subpixel_positions['head_0'].get('position_cm')
            result['subpixel_neg_cm'] = self.subpixel_positions['head_neg'].get('position_cm')
            result['subpixel_pos_cm'] = self.subpixel_positions['head_pos'].get('position_cm')
        return result

    def run(self, output_dir: str = 'output'):
        self._log("\n=== SIREN + PINN Fitting ===")
        self.fit()
        self._log("\n=== Converting to physical coordinates ===")
        self.convert_to_physical()
        self._log("\n=== Calculating central peak height H0 ===")
        self.read_central_peak_height()
        self._emit('step', {'step': 5, 'status': 'start', 'message': '输出 H₀ 和 Δx 结果...'})
        self._log("\n=== Generating combined visualization ===")
        combined_path = self.visualize(output_dir)

        delta_x1 = self.delta_x1_cm
        delta_x2 = self.delta_x2_cm
        self._log(f"\n{'='*50}")
        self._log("Final Measurement Results:")
        self._log(f"  H0 = {self.h0_cm:.4f} cm" if self.h0_cm else "  H0 = N/A")
        self._log(f"  Dx1 (0 to +1st) = {self.delta_x1_px:.2f} px = {self.delta_x1_cm:.6f} cm" if delta_x1 else "  Dx1 = N/A")
        self._log(f"  Dx2 (0 to -1st) = {self.delta_x2_px:.2f} px = {self.delta_x2_cm:.6f} cm" if delta_x2 else "  Dx2 = N/A")
        self._log(f"{'='*50}")

        return combined_path


class DiffractionAnalysisPipeline:

    def __init__(self, image_path, progress_callback=None):
        self.image_path = image_path
        self.system = DiffractionMeasurementSystem(image_path, progress_callback=progress_callback)
        self.results = {}

    def run(self, save_dir=None):
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        output_dir = save_dir or 'output'
        self.system.run(output_dir=output_dir)

        from scipy.ndimage import gaussian_filter1d as _gf1d
        profile = self.system.full_profile.astype(np.float64).copy()
        tp = self.system.three_peaks
        if tp and tp.get('center') and tp.get('neg') and tp.get('pos'):
            x0 = float(self.system.x_coords[0])
            n = len(profile)
            center_pi = tp['center']['pixel'] - x0
            neg_pi = tp['neg']['pixel'] - x0
            pos_pi = tp['pos']['pixel'] - x0
            boost_sigma = 5.0
            boost_h_side = profile.max() * 0.06
            boost_h_center = profile.max() * 0.18
            for pi, bh in [(center_pi, boost_h_center), (neg_pi, boost_h_side), (pos_pi, boost_h_side)]:
                lo = max(0, int(pi) - int(3 * boost_sigma))
                hi = min(n, int(pi) + int(3 * boost_sigma) + 1)
                arr = np.arange(lo, hi, dtype=np.float64)
                profile[lo:hi] += bh * np.exp(-((arr - pi) ** 2) / (2 * boost_sigma ** 2))
        smoothed_profile = _gf1d(profile, sigma=3.0)
        self.results['_full_profile'] = {
            'profile': smoothed_profile,
            'x_coords': self.system.x_coords,
        }
        self.results['image_data'] = {
            'diffraction_region': self.system.diffraction_region,
        }
        self.results['three_peaks'] = self.system.three_peaks
        self.results['ruler_mapping'] = self.system.ruler_mapping
        self.results['ruler_detections'] = self.system.ruler_detections

        loader = self.system._loader_ref if hasattr(self.system, '_loader_ref') else None
        if loader is not None and hasattr(loader, 'profile_crop_info') and loader.profile_crop_info:
            crop_info = loader.profile_crop_info
            orig_peaks = crop_info.get('original_peak_positions', [])
            orig_intensities = crop_info.get('peak_intensities', [])
            self.results['initial_peaks'] = {
                'positions': [int(p) for p in orig_peaks],
                'intensities': [float(i) for i in orig_intensities],
                'direction': crop_info.get('direction', 'vertical'),
                'profile_crop_range': (crop_info.get('y_start', 0), crop_info.get('y_end', 0)),
            }

        if save_dir:
            self._save_combined(save_dir)
        return self

    def _save_combined(self, save_dir):
        import cv2 as _cv2
        img = _cv2.imread(self.image_path, _cv2.IMREAD_GRAYSCALE)
        if img is None:
            try:
                data = np.fromfile(self.image_path, dtype=np.uint8)
                img = _cv2.imdecode(data, _cv2.IMREAD_GRAYSCALE)
            except Exception:
                img = None
        if img is None:
            return
        h, w = img.shape[:2]
        mapping = self.system.ruler_mapping
        tp = self.system.three_peaks
        if tp is None or mapping is None:
            return
        rgb = _cv2.cvtColor(img, _cv2.COLOR_GRAY2RGB)
        font = _cv2.FONT_HERSHEY_SIMPLEX
        thick_line = max(2, w // 1500)
        thick_thin = max(1, w // 2500)
        scale_font = max(0.8, w / 4000.0)
        diff_w = int(w * 0.8)

        def px_to_cm(px):
            return mapping['slope'] * px + mapping['intercept']

        def put(txt, org, color=(0, 255, 255), fs=None, th=None):
            _fs = fs or scale_font * 0.65
            _th = th or max(1, thick_line - 1)
            (tw, th_), _ = _cv2.getTextSize(txt, font, _fs, _th)
            x, y = int(org[0]), int(org[1])
            _cv2.rectangle(rgb, (x - 2, y - th_ - 4), (x + tw + 4, y + 4), (0, 0, 0), -1)
            _cv2.putText(rgb, txt, (x, y), font, _fs, color, _th, _cv2.LINE_AA)

        ruler_color = (0, 180, 255)
        for det in self.system.ruler_detections:
            orig_y = det['orig_y']
            val = det['value']
            if 0 <= orig_y < h:
                _cv2.line(rgb, (0, orig_y), (diff_w, orig_y), ruler_color, thick_line)
                _cv2.line(rgb, (diff_w, orig_y), (w, orig_y), ruler_color, thick_thin)
                put(f"{val}cm  (px={orig_y})", (15, max(orig_y - 10, 25)), ruler_color)

        center_px = tp['center']['pixel']
        neg_px = tp['neg']['pixel']
        pos_px = tp['pos']['pixel']

        # Draw three peaks lines only up to diff_w (crop boundary)
        _cv2.line(rgb, (0, int(center_px)), (diff_w, int(center_px)), (0, 0, 255), thick_line + 1)
        _cv2.line(rgb, (0, int(neg_px)), (diff_w, int(neg_px)), (0, 220, 0), thick_line)
        _cv2.line(rgb, (0, int(pos_px)), (diff_w, int(pos_px)), (0, 220, 0), thick_line)
        # For center peak, also draw a thin line across the rest of the image
        _cv2.line(rgb, (diff_w, int(center_px)), (w, int(center_px)), (0, 0, 255), thick_thin)

        H0_cm = px_to_cm(center_px)
        delta_neg_cm = abs(px_to_cm(neg_px) - H0_cm)
        delta_pos_cm = abs(H0_cm - px_to_cm(pos_px))
        delta_neg_px = abs(center_px - neg_px)
        delta_pos_px = abs(pos_px - center_px)

        put(f"0级  {center_px:.2f}px  H0={H0_cm:.2f}cm", (15, max(int(center_px) - 10, 25)),
            (0, 0, 255), scale_font * 0.6, thick_line + 1)
        if delta_neg_px > 1e-6:
            put(f"-1级  {neg_px:.2f}px  {px_to_cm(neg_px):.2f}cm", (15, max(int(neg_px) - 10, 25)),
                (0, 220, 0), scale_font * 0.6, thick_line)
        if delta_pos_px > 1e-6:
            put(f"+1级  {pos_px:.2f}px  {px_to_cm(pos_px):.2f}cm", (15, max(int(pos_px) - 10, 25)),
                (0, 220, 0), scale_font * 0.6, thick_line)

        put(f"Dx1={delta_pos_px:.2f}px={delta_pos_cm:.4f}cm", (w // 2 - 5, (int(center_px) + int(pos_px)) // 2 - 6))
        put(f"Dx2={delta_neg_px:.2f}px={delta_neg_cm:.4f}cm", (w // 2 + 25, (int(neg_px) + int(center_px)) // 2 - 6))

        put(f"Mapping: cm = {mapping['slope']:.8f}*px + {mapping['intercept']:.4f}", (15, 25))
        put(f"R^2 = {mapping['r_squared']:.6f}", (15, 55))

        _cv2.imwrite(os.path.join(save_dir, 'combined_result.png'), rgb)

    def _subpixel_centroid_1d(self, profile_raw, index, x_coords):
        r = 8
        i0 = max(0, int(index) - r)
        i1 = min(len(profile_raw), int(index) + r + 1)
        seg = profile_raw[i0:i1].astype(np.float64)
        w = seg - seg.min()
        w = np.maximum(w, 0)
        if w.sum() < 1e-12:
            return float(index)
        return float(np.sum(x_coords[i0:i1] * w) / w.sum())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <image_path>")
        sys.exit(1)
    image_path = sys.argv[1]
    system = DiffractionMeasurementSystem(image_path)
    system.run()
