import os
import cv2
import json
import shutil
import tempfile
import uuid
import traceback
import queue
import threading

import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks as _scipy_find_peaks
from scipy.ndimage import gaussian_filter1d as _gf1d
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename
from openai import OpenAI

from main import DiffractionMeasurementSystem
from config import DEEPSEEK_CONFIG

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

deepseek_client = OpenAI(
    api_key=DEEPSEEK_CONFIG['api_key'],
    base_url=DEEPSEEK_CONFIG['base_url']
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')

app.config['OUTPUT_FOLDER'] = OUTPUT_DIR
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')


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
        return self


def _smooth_profile(profile):
    return _gf1d(profile.astype(np.float64), sigma=0.5)


def find_bright_peaks(pipeline, override_profile=None, override_x_coords=None):
    if override_profile is not None:
        profile = override_profile.astype(np.float64)
    else:
        profile = pipeline.results['_full_profile']['profile'].astype(np.float64)

    if override_x_coords is not None:
        x_coords = override_x_coords
    else:
        x_coords = pipeline.results['_full_profile']['x_coords']

    if len(x_coords) < 3 or len(profile) < 3:
        return None

    smoothed = _smooth_profile(profile)

    all_peaks, props = _scipy_find_peaks(
        smoothed,
        distance=max(1, len(x_coords) // 30),
        prominence=(smoothed.max() - smoothed.min()) * 0.01,
    )

    if len(all_peaks) == 0:
        return None

    max_idx = int(np.argmax(smoothed))

    center_candidates = all_peaks[np.abs(all_peaks - max_idx) <= 5]
    if len(center_candidates) > 0:
        center_local = int(center_candidates[np.argmax(smoothed[center_candidates])])
    else:
        center_local = max_idx

    center_x = x_coords[center_local]
    center_I = float(smoothed[center_local])

    left_peaks = all_peaks[all_peaks < center_local - 5]
    right_peaks = all_peaks[all_peaks > center_local + 5]

    neg_local = None
    if len(left_peaks) > 0:
        left_dists = center_local - left_peaks
        left_Is = smoothed[left_peaks]
        left_score = 0.3 * left_Is / (left_Is.max() + 1e-8) + 0.7 * (1.0 - left_dists / (center_local + 1e-8))
        neg_local = int(left_peaks[int(np.argmax(left_score))])

    pos_local = None
    if len(right_peaks) > 0:
        right_dists = right_peaks - center_local
        right_Is = smoothed[right_peaks]
        right_score = 0.3 * right_Is / (right_Is.max() + 1e-8) + 0.7 * (1.0 - right_dists / (len(x_coords) - center_local + 1e-8))
        pos_local = int(right_peaks[int(np.argmax(right_score))])

    if neg_local is None or pos_local is None:
        return None

    neg_x = x_coords[neg_local]
    neg_I = float(smoothed[neg_local])
    pos_x = x_coords[pos_local]
    pos_I = float(smoothed[pos_local])

    def _refine_peak(idx, s):
        n = len(s)
        if idx <= 0 or idx >= n - 1:
            return float(idx), float(s[idx])
        y_l, y_c, y_r = float(s[idx - 1]), float(s[idx]), float(s[idx + 1])
        denom = y_l - 2.0 * y_c + y_r
        if abs(denom) > 1e-12:
            delta = -0.5 * (y_l - y_r) / denom
            delta = max(-0.5, min(0.5, delta))
            interp_x = idx + delta
            interp_y = y_c - 0.25 * (y_l - y_r) * delta
            return interp_x, interp_y
        return float(idx), float(y_c)

    neg_pi, neg_I = _refine_peak(neg_local, smoothed)
    pos_pi, pos_I = _refine_peak(pos_local, smoothed)
    center_pi, center_I = _refine_peak(center_local, smoothed)

    _x_off = float(x_coords[0])
    neg_pi = x_coords[int(round(neg_pi))] if 0 <= int(round(neg_pi)) < len(x_coords) else neg_pi + _x_off
    pos_pi = x_coords[int(round(pos_pi))] if 0 <= int(round(pos_pi)) < len(x_coords) else pos_pi + _x_off
    center_pi = x_coords[int(round(center_pi))] if 0 <= int(round(center_pi)) < len(x_coords) else center_pi + _x_off

    print(f"  中央(0级): idx={center_local} I={center_I:.1f} px={center_pi:.4f}")
    print(f"  -1级(左侧): idx={neg_local} I={neg_I:.1f} px={neg_pi:.4f}  Δ={center_pi - neg_pi:.4f}px")
    print(f"  +1级(右侧): idx={pos_local} I={pos_I:.1f} px={pos_pi:.4f}  Δ={pos_pi - center_pi:.4f}px")

    return {
        'center': {'pixel': center_pi, 'index': center_local, 'intensity': center_I},
        'neg': {'pixel': neg_pi, 'index': neg_local, 'intensity': neg_I},
        'pos': {'pixel': pos_pi, 'index': pos_local, 'intensity': pos_I},
    }


def _compute_h0_local(center_px, ruler_detections, tolerance=150):
    candidates = [d for d in ruler_detections if abs(d['orig_y'] - center_px) <= tolerance]
    if len(candidates) < 2:
        return None
    candidates_sorted = sorted(candidates, key=lambda x: x['orig_y'])
    y_upper = candidates_sorted[0]['orig_y']
    val_upper = candidates_sorted[0]['value']
    y_lower = candidates_sorted[-1]['orig_y']
    val_lower = candidates_sorted[-1]['value']
    gap = y_upper - y_lower
    if abs(gap) < 1e-6:
        return None
    h0 = val_lower + (val_upper - val_lower) * abs(center_px - y_lower) / abs(gap)
    return h0


def create_annotated_image(image_path, three_peaks, ruler_detections, h0_cm, delta_pos_px, delta_neg_px,
                           delta_pos_cm, delta_neg_cm):
    original_img = cv2.imread(image_path)
    if original_img is None:
        return None

    ann = original_img.copy()
    h_img, w_img = ann.shape[:2]

    ruler_color = (0, 200, 255)
    for det in ruler_detections:
        ry = det['orig_y']
        val = det['value']
        cv2.line(ann, (0, ry), (w_img, ry), ruler_color, 2)
        label = f"{val}cm (y={ry}px)"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        tx = w_img - tw - 10
        ty = ry - 8
        if ty < th + 5:
            ty = ry + th + 8
        cv2.rectangle(ann, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (0, 0, 0), -1)
        cv2.putText(ann, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.6, ruler_color, 2)

    center_y = int(round(three_peaks['center']['pixel']))
    neg_y = int(round(three_peaks['neg']['pixel']))
    pos_y = int(round(three_peaks['pos']['pixel']))

    cv2.line(ann, (0, center_y), (w_img, center_y), (0, 0, 255), 3)
    c_label = f"Center (0) y={center_y}px H0={h0_cm:.2f}cm" if h0_cm else f"Center (0) y={center_y}px"
    (tw, th), _ = cv2.getTextSize(c_label, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
    cv2.rectangle(ann, (8, center_y - th - 10), (12 + tw, center_y - 4), (0, 0, 0), -1)
    cv2.putText(ann, c_label, (10, center_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

    cv2.line(ann, (0, pos_y), (w_img, pos_y), (0, 220, 0), 2)
    p1_label = f"+1st y={pos_y}px Dx1={delta_pos_px:.1f}px"
    if delta_pos_cm is not None:
        p1_label += f"={delta_pos_cm:.3f}cm"
    (tw, th), _ = cv2.getTextSize(p1_label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(ann, (8, pos_y - th - 10), (12 + tw, pos_y - 4), (0, 0, 0), -1)
    cv2.putText(ann, p1_label, (10, pos_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)

    cv2.line(ann, (0, neg_y), (w_img, neg_y), (0, 220, 0), 2)
    n1_label = f"-1st y={neg_y}px Dx2={delta_neg_px:.1f}px"
    if delta_neg_cm is not None:
        n1_label += f"={delta_neg_cm:.3f}cm"
    (tw, th), _ = cv2.getTextSize(n1_label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(ann, (8, neg_y + 8), (12 + tw, neg_y + 16 + th), (0, 0, 0), -1)
    cv2.putText(ann, n1_label, (10, neg_y + 8 + th), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)

    return ann


def draw_intensity_profile(pipeline, three_peaks, output_path):
    profile = pipeline.results['_full_profile']['profile']
    x_coords = pipeline.results['_full_profile']['x_coords']

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#E8E8E8')
    ax.set_facecolor('#F0F0F0')
    ax.plot(x_coords, profile, color='#555555', linewidth=1.2, alpha=0.9)

    peak_info = [
        (three_peaks['center']['pixel'], 'Center (0th)', 'red', '--'),
        (three_peaks['neg']['pixel'], '-1st Order', 'black', ':'),
        (three_peaks['pos']['pixel'], '+1st Order', 'black', ':'),
    ]
    for pos, label, color, ls in peak_info:
        idx = int(round(pos))
        if 0 <= idx < len(profile):
            ax.axvline(x=x_coords[idx], color=color, linestyle=ls, linewidth=1.0, alpha=0.8)
            ax.plot(x_coords[idx], profile[idx], marker='o', color=color, markersize=7,
                    label=f'{label}: x={x_coords[idx]:.1f}px, I={profile[idx]:.0f}')

    ax.set_xlabel('Pixel Coordinate', fontsize=12, fontweight='bold')
    ax.set_ylabel('Intensity', fontsize=12, fontweight='bold')
    ax.set_title('SIREN-Fitted Diffraction Profile', fontsize=14, fontweight='bold')
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='-', color='white')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_3d_surface(pipeline, output_path):
    gray = pipeline.system.gray_image
    if gray is None:
        return None
    h_full, w_full = gray.shape[:2]
    tp = pipeline.system.three_peaks
    if tp and tp.get('center') and tp.get('neg') and tp.get('pos'):
        center_y = tp['center']['pixel']
        neg_y = tp['neg']['pixel']
        pos_y = tp['pos']['pixel']
        peak_span = abs(pos_y - neg_y)
        y_margin = max(120, int(peak_span * 0.7))
        y_center = center_y
    else:
        proj_v = np.sum(gray, axis=1).astype(np.float64)
        proj_v_smooth = _gf1d(proj_v, sigma=10.0)
        y_center = int(np.argmax(proj_v_smooth))
        y_margin = 200
    y_lo = max(0, int(y_center - y_margin))
    y_hi = min(h_full, int(y_center + y_margin))
    stripe_band = gray[y_lo:y_hi, :]
    proj_h = np.sum(stripe_band, axis=0).astype(np.float64)
    proj_h_smooth = _gf1d(proj_h, sigma=8.0)
    h_peak_val = proj_h_smooth.max()
    h_threshold = h_peak_val * 0.05
    h_indices = np.where(proj_h_smooth > h_threshold)[0]
    if len(h_indices) > 10:
        x_lo = max(0, int(h_indices[0]) - 3)
        x_hi = min(w_full, int(h_indices[-1]) + 3)
    else:
        x_lo = 0
        x_hi = w_full
    if x_hi - x_lo > 600:
        x_center = (x_lo + x_hi) // 2
        x_lo = max(0, x_center - 300)
        x_hi = min(w_full, x_center + 300)
    crop_img = gray[y_lo:y_hi, x_lo:x_hi]
    if crop_img.size == 0:
        return None
    diff_rgb = cv2.cvtColor(crop_img, cv2.COLOR_GRAY2RGB).astype(np.float64)
    z_raw = np.mean(diff_rgb, axis=2)
    z = 255.0 - z_raw
    z_min, z_max = z.min(), z.max()
    if z_max - z_min > 1e-6:
        z = (z - z_min) / (z_max - z_min) * 255.0
    p_h, p_w = z.shape
    skip = max(1, int(np.ceil(max(p_h, p_w) / 200.0)))
    z = z[::skip, ::skip]
    diff_rgb = diff_rgb[::skip, ::skip]
    rgb_norm = diff_rgb / 255.0
    row_idx, col_idx = np.mgrid[0:z.shape[0], 0:z.shape[1]]
    xs = col_idx.flatten().tolist()
    ys = row_idx.flatten().tolist()
    zs = z.flatten().tolist()
    vc_raw = rgb_norm.reshape(-1, 3)
    vc_str = ['rgb(' + ','.join((c * 255).astype(int).astype(str)) + ')' for c in vc_raw]
    z_ratio = max(0.6, min(1.5, (x_hi - x_lo) / max(z_max - z_min, 1) * 0.15))
    trace = dict(type='mesh3d', x=xs, y=ys, z=zs,
                 vertexcolor=vc_str, delaunayaxis='z',
                 opacity=1, showscale=False, hoverinfo='skip',
                 lighting=dict(ambient=0.35, diffuse=0.75, specular=0.4,
                               roughness=0.25, fresnel=0.35))
    layout = dict(
        title=None,
        scene=dict(
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.9),
                        center=dict(x=0, y=0, z=-0.05),
                        up=dict(x=0, y=0, z=1)),
            aspectmode='manual',
            aspectratio=dict(x=1.2, y=1.0, z=z_ratio),
            xaxis=dict(title='X (along stripe)', font=dict(size=10, color='#607A8C'),
                        gridcolor='#E8F2F7', zerolinecolor='#C4D2DB',
                        backgroundcolor='#F8FAFB'),
            yaxis=dict(title='Y (across stripes)', font=dict(size=10, color='#607A8C'),
                        gridcolor='#E8F2F7', zerolinecolor='#C4D2DB',
                        backgroundcolor='#F8FAFB'),
            zaxis=dict(title='Intensity', font=dict(size=10, color='#607A8C'),
                        gridcolor='#E8F2F7', zerolinecolor='#C4D2DB'),
            bgcolor='#F8FAFB'),
        margin=dict(l=55, r=15, t=5, b=45),
        paper_bgcolor='#F8FAFB',
        dragmode='orbit')
    fig_dict = dict(data=[trace], layout=layout,
                    config=dict(responsive=True, displayModeBar=False, displaylogo=False))
    html_content = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8"><script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>body{{margin:0;padding:0;overflow:hidden}}</style></head><body>
<div id="plot" style="width:100vw;height:100vh"></div>
<script>Plotly.newPlot('plot',{json.dumps(fig_dict, default=str)});
window.addEventListener('message',function(e){{if(e.data==='save')Plotly.downloadImage('plot',{{format:'png',width:1200,height:750,filename:'3D_Surface'}})}});
</script></body></html>"""
    html_path = output_path.replace('.png', '.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return html_path


def _make_response(code, msg, data):
    return jsonify({'code': code, 'msg': msg, 'data': data})


def _cleanup_dir(dir_path):
    if not os.path.exists(dir_path):
        return
    for file_name in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file_name)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass


def _ensure_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path


# ========================= Page Routes =========================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/module2')
@app.route('/data-processing')
def module2():
    return render_template('data_processing.html')


@app.route('/module5')
@app.route('/laser-diffraction')
def module5():
    return render_template('laser_diffraction.html')


@app.route('/output/<path:filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route('/samples/<path:filename>')
def serve_samples(filename):
    return send_from_directory('static/samples', filename)


# ========================= Diffraction Analysis API =========================

@app.route('/api/laser-diffraction', methods=['POST'])
def laser_diffraction():
    temp_dir = None
    try:
        uploaded_files = request.files.getlist('images')
        if not uploaded_files or not uploaded_files[0].filename:
            return jsonify({'success': False, 'error': '请先上传图像'})

        file = uploaded_files[0]
        temp_dir = tempfile.mkdtemp()
        ext = os.path.splitext(file.filename)[1].lower() or '.png'
        image_path = os.path.join(temp_dir, f'input{ext}')
        file.save(image_path)

        original_img = cv2.imread(image_path)
        if original_img is None:
            return jsonify({'success': False, 'error': '无法读取图片文件'})

        pipeline = DiffractionAnalysisPipeline(image_path)
        pipeline.run(save_dir=os.path.join(OUTPUT_DIR, 'pipeline'))

        fp = pipeline.results['_full_profile']
        profile = fp['profile']
        x_coords = fp['x_coords']

        three_peaks = find_bright_peaks(pipeline, override_profile=profile, override_x_coords=x_coords)
        tp_system = pipeline.system.three_peaks

        if three_peaks is None:
            three_peaks = tp_system
        else:
            dx1_check = abs(three_peaks['pos']['pixel'] - three_peaks['center']['pixel'])
            dx2_check = abs(three_peaks['center']['pixel'] - three_peaks['neg']['pixel'])
            if dx1_check > 0 and dx2_check > 0:
                ratio = min(dx1_check, dx2_check) / max(dx1_check, dx2_check)
                if ratio < 0.5:
                    three_peaks = tp_system

        pipeline.system.three_peaks = three_peaks

        mapping = pipeline.system.ruler_mapping
        ruler_detections = pipeline.system.ruler_detections
        center_px = three_peaks['center']['pixel']

        if mapping:
            slope = mapping['slope']
            intercept = mapping['intercept']
            center_cm = slope * center_px + intercept
            h0_local = _compute_h0_local(center_px, ruler_detections)
            h0_cm = h0_local if h0_local else center_cm
        else:
            h0_cm = None

        delta_pos_px = abs(three_peaks['pos']['pixel'] - center_px)
        delta_neg_px = abs(center_px - three_peaks['neg']['pixel'])

        if mapping:
            delta_pos_cm = abs(mapping['slope']) * delta_pos_px
            delta_neg_cm = abs(mapping['slope']) * delta_neg_px
            delta_avg_cm = (delta_pos_cm + delta_neg_cm) / 2.0
            px_per_cm = 1.0 / abs(mapping['slope']) if abs(mapping['slope']) > 1e-12 else None
        else:
            delta_pos_cm = delta_neg_cm = delta_avg_cm = px_per_cm = None

        vis_dir = os.path.join(OUTPUT_DIR, 'pipeline')
        pipeline.system.visualize(output_dir=vis_dir)

        output_img_dir = _ensure_dir(os.path.join(OUTPUT_DIR, 'uploaded_image'))
        annotated_img = create_annotated_image(
            image_path, three_peaks, ruler_detections, h0_cm,
            delta_pos_px, delta_neg_px, delta_pos_cm, delta_neg_cm
        )
        annotated_path = None
        if annotated_img is not None:
            annotated_path = os.path.join(output_img_dir, f'annotated_{uuid.uuid4().hex[:8]}.png')
            cv2.imwrite(annotated_path, annotated_img)

        profile_path = os.path.join(output_img_dir, 'intensity_profile.png')
        draw_intensity_profile(pipeline, three_peaks, profile_path)

        gray_path = os.path.join(output_img_dir, 'gray_image.png')
        if pipeline.system.gray_image is not None:
            cv2.imwrite(gray_path, pipeline.system.gray_image)

        surface3d_path = os.path.join(output_img_dir, 'surface3d.html')
        draw_3d_surface(pipeline, surface3d_path)

        return jsonify({
            'success': True,
            'data': {
                'grayImage': f'/output/uploaded_image/gray_image.png?t={uuid.uuid4().hex}',
                'intensityProfile': f'/output/uploaded_image/intensity_profile.png?t={uuid.uuid4().hex}',
                'annotatedImage': f'/output/uploaded_image/{os.path.basename(annotated_path)}?t={uuid.uuid4().hex}' if annotated_path else None,
                'surface3d': f'/output/uploaded_image/surface3d.html?t={uuid.uuid4().hex}' if os.path.exists(surface3d_path) else None,
                'H0': round(float(h0_cm), 4) if h0_cm is not None else None,
                'deltaX1': round(float(delta_pos_cm), 4) if delta_pos_cm is not None else None,
                'deltaX2': round(float(delta_neg_cm), 4) if delta_neg_cm is not None else None,
                'avgDeltaX': round(float(delta_avg_cm), 4) if delta_avg_cm is not None else None,
                'deltaX1_px': round(float(delta_pos_px), 2),
                'deltaX2_px': round(float(delta_neg_px), 2),
                'pxPerCm': round(float(px_per_cm), 2) if px_per_cm is not None else None,
                'centerPx': round(float(center_px), 2),
                'rulerMapping': {
                    'slope': mapping['slope'],
                    'intercept': mapping['intercept'],
                } if mapping else None,
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'分析失败: {str(e)}'})
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.route('/api/laser-diffraction-stream', methods=['POST'])
def laser_diffraction_stream():
    temp_dir = None
    try:
        uploaded_files = request.files.getlist('images')
        if not uploaded_files or not uploaded_files[0].filename:
            return jsonify({'success': False, 'error': '请先上传图像'})

        file = uploaded_files[0]
        temp_dir = tempfile.mkdtemp()
        ext = os.path.splitext(file.filename)[1].lower() or '.png'
        image_path = os.path.join(temp_dir, f'input{ext}')
        file.save(image_path)

        original_img = cv2.imread(image_path)
        if original_img is None:
            return jsonify({'success': False, 'error': '无法读取图片文件'})
    except Exception as e:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'success': False, 'error': f'上传失败: {str(e)}'})

    event_queue = queue.Queue()

    def progress_callback(event_type, data):
        event_queue.put({'event': event_type, 'data': data})

    def run_analysis():
        try:
            pipeline = DiffractionAnalysisPipeline(image_path, progress_callback=progress_callback)
            pipeline.run(save_dir=os.path.join(OUTPUT_DIR, 'pipeline'))

            fp = pipeline.results['_full_profile']
            profile = fp['profile']
            x_coords = fp['x_coords']

            three_peaks = find_bright_peaks(pipeline, override_profile=profile, override_x_coords=x_coords)
            tp_system = pipeline.system.three_peaks

            if three_peaks is None:
                three_peaks = tp_system
            else:
                dx1_check = abs(three_peaks['pos']['pixel'] - three_peaks['center']['pixel'])
                dx2_check = abs(three_peaks['center']['pixel'] - three_peaks['neg']['pixel'])
                if dx1_check > 0 and dx2_check > 0:
                    ratio = min(dx1_check, dx2_check) / max(dx1_check, dx2_check)
                    if ratio < 0.5:
                        three_peaks = tp_system

            pipeline.system.three_peaks = three_peaks

            mapping = pipeline.system.ruler_mapping
            ruler_detections = pipeline.system.ruler_detections
            center_px = three_peaks['center']['pixel']

            if mapping:
                slope = mapping['slope']
                intercept = mapping['intercept']
                center_cm = slope * center_px + intercept
                h0_local = _compute_h0_local(center_px, ruler_detections)
                h0_cm = h0_local if h0_local else center_cm
            else:
                h0_cm = None

            delta_pos_px = abs(three_peaks['pos']['pixel'] - center_px)
            delta_neg_px = abs(center_px - three_peaks['neg']['pixel'])

            if mapping:
                delta_pos_cm = abs(mapping['slope']) * delta_pos_px
                delta_neg_cm = abs(mapping['slope']) * delta_neg_px
                delta_avg_cm = (delta_pos_cm + delta_neg_cm) / 2.0
                px_per_cm = 1.0 / abs(mapping['slope']) if abs(mapping['slope']) > 1e-12 else None
            else:
                delta_pos_cm = delta_neg_cm = delta_avg_cm = px_per_cm = None

            vis_dir = os.path.join(OUTPUT_DIR, 'pipeline')
            pipeline.system.visualize(output_dir=vis_dir)

            output_img_dir = _ensure_dir(os.path.join(OUTPUT_DIR, 'uploaded_image'))
            annotated_img = create_annotated_image(
                image_path, three_peaks, ruler_detections, h0_cm,
                delta_pos_px, delta_neg_px, delta_pos_cm, delta_neg_cm
            )
            annotated_path = None
            if annotated_img is not None:
                annotated_path = os.path.join(output_img_dir, f'annotated_{uuid.uuid4().hex[:8]}.png')
                cv2.imwrite(annotated_path, annotated_img)

            profile_path = os.path.join(output_img_dir, 'intensity_profile.png')
            draw_intensity_profile(pipeline, three_peaks, profile_path)

            gray_path = os.path.join(output_img_dir, 'gray_image.png')
            if pipeline.system.gray_image is not None:
                cv2.imwrite(gray_path, pipeline.system.gray_image)

            surface3d_path = os.path.join(output_img_dir, 'surface3d.html')
            draw_3d_surface(pipeline, surface3d_path)

            event_queue.put({
                'event': 'step',
                'data': {'step': 5, 'status': 'done'}
            })

            event_queue.put({
                'event': 'result',
                'data': {
                    'success': True,
                    'data': {
                        'grayImage': f'/output/uploaded_image/gray_image.png?t={uuid.uuid4().hex}',
                        'intensityProfile': f'/output/uploaded_image/intensity_profile.png?t={uuid.uuid4().hex}',
                        'annotatedImage': f'/output/uploaded_image/{os.path.basename(annotated_path)}?t={uuid.uuid4().hex}' if annotated_path else None,
                        'surface3d': f'/output/uploaded_image/surface3d.html?t={uuid.uuid4().hex}' if os.path.exists(surface3d_path) else None,
                        'H0': round(float(h0_cm), 4) if h0_cm is not None else None,
                        'deltaX1': round(float(delta_pos_cm), 4) if delta_pos_cm is not None else None,
                        'deltaX2': round(float(delta_neg_cm), 4) if delta_neg_cm is not None else None,
                        'avgDeltaX': round(float(delta_avg_cm), 4) if delta_avg_cm is not None else None,
                        'deltaX1_px': round(float(delta_pos_px), 2),
                        'deltaX2_px': round(float(delta_neg_px), 2),
                        'pxPerCm': round(float(px_per_cm), 2) if px_per_cm is not None else None,
                        'centerPx': round(float(center_px), 2),
                        'rulerMapping': {
                            'slope': mapping['slope'],
                            'intercept': mapping['intercept'],
                        } if mapping else None,
                    }
                }
            })
        except Exception as e:
            traceback.print_exc()
            event_queue.put({
                'event': 'error',
                'data': {'message': f'分析失败: {str(e)}'}
            })
        finally:
            event_queue.put(None)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                item = event_queue.get(timeout=120)
            except queue.Empty:
                yield json.dumps({'event': 'error', 'data': {'message': '分析超时'}}) + '\n'
                break
            if item is None:
                break
            yield json.dumps(item, ensure_ascii=False) + '\n'

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )


# ========================= Sample Images =========================

@app.route('/api/samples', methods=['GET'])
def get_samples():
    sample_files = [
        ('/samples/image1.png', '单缝衍射'),
        ('/samples/image2.png', '圆孔衍射'),
        ('/samples/image3.png', '光栅衍射'),
        ('/samples/image4.png', '矩孔衍射'),
    ]
    return jsonify({
        'code': 200,
        'msg': '获取示例图片成功',
        'data': {
            'images': [
                {'src': src, 'name': name}
                for src, name in sample_files
                if os.path.exists(os.path.join('static', 'samples', os.path.basename(src)))
            ]
        }
    })


# ========================= DeepSeek AI Assistant =========================

@app.route('/api/ask', methods=['POST'])
def ask_assistant():
    data = request.get_json(silent=True)
    question = (data or {}).get('question', '').strip()
    if not question:
        return jsonify({'answer': '请输入您的问题。'})

    try:
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_CONFIG['model'],
            messages=[
                {'role': 'system', 'content': DEEPSEEK_CONFIG['system_prompt']},
                {'role': 'user', 'content': question}
            ],
            max_tokens=DEEPSEEK_CONFIG['max_tokens'],
            temperature=DEEPSEEK_CONFIG['temperature']
        )
        answer = response.choices[0].message.content.strip()
        return jsonify({'answer': answer})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'answer': f'AI 助手暂时无法响应，请稍后重试。错误信息：{str(e)[:200]}'})


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
