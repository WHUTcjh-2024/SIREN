"""
Combined analysis test script: ruler mapping + SIREN subpixel peak refinement + horizontal profile extraction
"""

import os
import sys
import glob
import json
import cv2
import argparse
import shutil
import numpy as np
from scipy.ndimage import gaussian_filter1d as gf1d
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import easyocr

from main import DiffractionAnalysisPipeline

IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output_combined')


def get_test_images():
    exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')
    images = [os.path.join(IMAGE_DIR, f) for f in sorted(os.listdir(IMAGE_DIR))
              if f.lower().endswith(exts) and not f.startswith('.')]
    return images


def _smooth_profile(profile):
    return gf1d(profile.astype(np.float64), sigma=0.5)


def _find_center_peak(valid_peaks, x_coords):
    center_idx, center_I = max(valid_peaks, key=lambda x: x[1])

    center_x = x_coords[center_idx]
    n = len(x_coords)
    window = n // 6
    left_bound = center_x - window
    right_bound = center_x + window

    nearby = [(i, v) for i, v in valid_peaks
              if left_bound <= x_coords[i] <= right_bound]

    if len(nearby) < 3:
        return center_idx, center_I

    avg_I = np.mean([v for _, v in nearby])
    std_I = np.std([v for _, v in nearby])
    noise_floor = avg_I - 0.3 * std_I

    main_peaks = [(i, v) for i, v in nearby if v > noise_floor]
    if main_peaks:
        center_idx, center_I = max(main_peaks, key=lambda x: x[1])

    return center_idx, center_I


def _find_side_peak(valid_peaks, x_coords, center, direction, x_min, x_max,
                    profile=None, min_sep_ratio=0.25, max_dist=None):
    if direction == 'left':
        candidates = [(i, v) for i, v in valid_peaks
                      if x_coords[i] < x_coords[center] - 30
                      and x_coords[i] >= x_min]
    else:
        candidates = [(i, v) for i, v in valid_peaks
                      if x_coords[i] > x_coords[center] + 30
                      and x_coords[i] <= x_max]

    if not candidates:
        return None, 0.0

    min_dist = abs(x_coords[center] - x_coords[candidates[0][0]]) * min_sep_ratio
    if min_dist < 10:
        min_dist = 10

    if direction == 'left':
        candidates = [(i, v) for i, v in candidates
                      if x_coords[center] - x_coords[i] >= min_dist]
    else:
        candidates = [(i, v) for i, v in candidates
                      if x_coords[i] - x_coords[center] >= min_dist]

    if max_dist is not None:
        if direction == 'left':
            candidates = [(i, v) for i, v in candidates
                          if x_coords[center] - x_coords[i] <= max_dist]
        else:
            candidates = [(i, v) for i, v in candidates
                          if x_coords[i] - x_coords[center] <= max_dist]

    if not candidates:
        max_dist_candidates = [(i, v) for i, v in valid_peaks
                               if (direction == 'left' and x_coords[i] < x_coords[center] - 30) or
                                  (direction == 'right' and x_coords[i] > x_coords[center] + 30)]
        if direction == 'left':
            max_dist_candidates = [(i, v) for i, v in max_dist_candidates
                                   if x_coords[center] - x_coords[i] >= min_dist]
        else:
            max_dist_candidates = [(i, v) for i, v in max_dist_candidates
                                   if x_coords[i] - x_coords[center] >= min_dist]
        candidates = max_dist_candidates

    if not candidates:
        return None, 0.0

    best_peak = None
    best_symmetry = -1.0

    for idx, I in candidates:
        delta = abs(x_coords[idx] - x_coords[center])

        if profile is not None:
            n = len(profile)
            half_window = max(5, int(delta * 0.3))
            center_i = int(center)
            side_i = idx

            c_start = max(0, center_i - half_window)
            c_end = min(n, center_i + half_window + 1)
            s_start = max(0, side_i - half_window)
            s_end = min(n, side_i + half_window + 1)

            center_seg = profile[c_start:c_end]
            side_seg = profile[s_start:s_end]

            c_norm = center_seg / (center_seg.max() + 1e-8)
            s_norm = side_seg / (side_seg.max() + 1e-8)

            min_len = min(len(c_norm), len(s_norm))
            c_norm = c_norm[:min_len]
            s_norm = s_norm[:min_len]

            symmetry = np.exp(-np.sum((c_norm - s_norm) ** 2) / min_len)
        else:
            symmetry = 1.0

        I_ratio = I / (profile[int(center)] + 1e-8) if profile is not None else 1.0
        I_score = min(I_ratio, 1.0)

        score = symmetry * 0.6 + I_score * 0.4

        if score > best_symmetry:
            best_symmetry = score
            best_peak = idx

    if best_peak is None and len(candidates) > 0:
        best_peak = max(candidates, key=lambda x: x[1])[0]
        best_symmetry = 0.05
        print(f"  弱峰fallback: direction={direction}, peak_idx={best_peak}")

    if best_peak is None:
        return None, 0.0

    return best_peak, best_symmetry


def find_bright_peaks(pipeline, override_profile=None, override_x_coords=None):
    if override_profile is not None:
        profile = override_profile.astype(np.float64)
    else:
        profile = pipeline.results['_full_profile']['profile'].astype(np.float64)

    if override_x_coords is not None:
        x_coords = override_x_coords
    else:
        x_coords = pipeline.results['_full_profile']['x_coords']

    n = len(profile)

    initial_peaks = pipeline.results.get('initial_peaks')
    adaptive_max_dist = None
    if initial_peaks and len(initial_peaks.get('positions', [])) >= 3:
        positions = sorted(initial_peaks['positions'])
        spacings = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
        if spacings:
            min_spacing = min(spacings)
            adaptive_max_dist = min_spacing * 3.0
            print(f"  初始峰间距: {spacings}, max_dist={adaptive_max_dist:.1f}px")

    smoothed = _smooth_profile(profile)

    local_max = []
    for i in range(1, n - 1):
        if smoothed[i] > smoothed[i - 1] and smoothed[i] > smoothed[i + 1]:
            local_max.append(i)

    noise_floor = float(np.percentile(smoothed, 5))
    noise_sigma = float(np.std(smoothed))
    valid_threshold = noise_floor + noise_sigma * 0.2

    valid_peaks = [(i, float(smoothed[i])) for i in local_max if smoothed[i] > valid_threshold]

    if len(valid_peaks) < 2:
        return None

    print(f"  邻域极大值: {len(local_max)}个 → 有效峰: {len(valid_peaks)}个")

    center_idx, center_I = _find_center_peak(valid_peaks, x_coords)

    print(f"  中央(0级): idx={center_idx} I={center_I:.1f} px={x_coords[center_idx]:.4f}")

    neg_idx, neg_sym = _find_side_peak(valid_peaks, x_coords, center_idx, 'left',
                                        x_min=x_coords[0], x_max=x_coords[-1],
                                        profile=smoothed, max_dist=adaptive_max_dist)
    if neg_idx is None:
        return None

    pos_idx, pos_sym = _find_side_peak(valid_peaks, x_coords, center_idx, 'right',
                                        x_min=x_coords[0], x_max=x_coords[-1],
                                        profile=smoothed, max_dist=adaptive_max_dist)
    if pos_idx is None:
        return None

    neg_dist = abs(x_coords[center_idx] - x_coords[neg_idx])
    pos_dist = abs(x_coords[pos_idx] - x_coords[center_idx])

    if neg_dist > 0 and pos_dist > 0:
        if neg_dist > pos_dist * 2.5 or pos_dist > neg_dist * 2.5:
            max_dist = min(neg_dist, pos_dist) * 2.0
            if adaptive_max_dist is not None:
                max_dist = min(max_dist, adaptive_max_dist)
            if neg_dist > pos_dist * 2.5:
                new_neg_idx, new_neg_sym = _find_side_peak(
                    valid_peaks, x_coords, center_idx, 'left',
                    x_min=x_coords[0], x_max=x_coords[-1],
                    profile=smoothed, max_dist=max_dist)
                if new_neg_idx is not None:
                    neg_idx = new_neg_idx
                    neg_sym = new_neg_sym
            if pos_dist > neg_dist * 2.5:
                new_pos_idx, new_pos_sym = _find_side_peak(
                    valid_peaks, x_coords, center_idx, 'right',
                    x_min=x_coords[0], x_max=x_coords[-1],
                    profile=smoothed, max_dist=max_dist)
                if new_pos_idx is not None:
                    pos_idx = new_pos_idx
                    pos_sym = new_pos_sym

    dx1 = abs(x_coords[pos_idx] - x_coords[center_idx])
    dx2 = abs(x_coords[center_idx] - x_coords[neg_idx])

    print(f"  -1级(左): idx={neg_idx} I={smoothed[neg_idx]:.1f} px={x_coords[neg_idx]:.4f}  Δ={dx2:.4f}px")
    print(f"  +1级(右): idx={pos_idx} I={smoothed[pos_idx]:.1f} px={x_coords[pos_idx]:.4f}  Δ={dx1:.4f}px")

    three_peaks = {
        'center': {
            'pixel': x_coords[center_idx],
            'index': center_idx,
            'intensity': center_I
        },
        'neg': {
            'pixel': x_coords[neg_idx],
            'index': neg_idx,
            'intensity': float(smoothed[neg_idx]),
            'symmetry_score': neg_sym
        },
        'pos': {
            'pixel': x_coords[pos_idx],
            'index': pos_idx,
            'intensity': float(smoothed[pos_idx]),
            'symmetry_score': pos_sym
        }
    }

    return three_peaks


def _compute_h0_local(center_px, ruler_detections):
    ruler_dict = {d['value']: d['orig_y'] for d in ruler_detections}
    center_y = center_px

    if 20 in ruler_dict and 30 in ruler_dict:
        y20 = ruler_dict[20]
        y30 = ruler_dict[30]
        if abs(y20 - y30) < 1:
            return None
        h0 = 20 + 10.0 * abs(y20 - center_y) / abs(y20 - y30)
        print(f"  [H0局部] center={center_y:.1f}px, 20cm@y={y20}, 30cm@y={y30}, H0=20+10*|{y20}-{center_y:.1f}|/|{y20}-{y30}|={h0:.4f}cm")
        return h0
    elif 10 in ruler_dict and 20 in ruler_dict:
        y10 = ruler_dict[10]
        y20 = ruler_dict[20]
        if abs(y10 - y20) < 1:
            return None
        h0 = 10 + 10.0 * abs(y10 - center_y) / abs(y10 - y20)
        print(f"  [H0局部] center={center_y:.1f}px, 10cm@y={y10}, 20cm@y={y20}, H0=10+10*|{y10}-{center_y:.1f}|/|{y10}-{y20}|={h0:.4f}cm")
        return h0
    return None


def _compute_combined_result(image_data, three_peaks, mapping, ax,
                             title_prefix="", show_ruler=True,
                             roi_only=False):
    diffraction_region = image_data['diffraction_region']
    if diffraction_region is None:
        print(f"  [WARN] No diffraction region for {title_prefix}")
        return None

    if len(diffraction_region.shape) == 2:
        display_img = cv2.cvtColor(diffraction_region, cv2.COLOR_GRAY2RGB)
    else:
        display_img = diffraction_region.copy()

    h, w = display_img.shape[:2]

    center_px = three_peaks['center']['pixel']
    neg_px = three_peaks['neg']['pixel']
    pos_px = three_peaks['pos']['pixel']

    cv2.line(display_img, (0, int(center_px)), (w, int(center_px)), (0, 0, 255), 2)
    cv2.line(display_img, (0, int(neg_px)), (w, int(neg_px)), (0, 220, 0), 2)
    cv2.line(display_img, (0, int(pos_px)), (w, int(pos_px)), (0, 220, 0), 2)

    ruler_dets = image_data.get('ruler_detections', [])

    if show_ruler:
        for det in ruler_dets:
            ry = det['orig_y']
            val = det['value']
            cv2.line(display_img, (0, ry), (w, ry), (0, 180, 255), 1)
            cv2.putText(display_img, f"{val}cm", (5, ry - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 1)

    if mapping:
        slope = mapping['slope']
        intercept = mapping['intercept']

        center_cm_global = slope * center_px + intercept
        neg_cm = slope * neg_px + intercept
        pos_cm = slope * pos_px + intercept

        delta_neg_px = abs(center_px - neg_px)
        delta_pos_px = abs(pos_px - center_px)
        delta_neg_cm = abs(center_cm_global - neg_cm)
        delta_pos_cm = abs(pos_cm - center_cm_global)

        h0_cm_local = _compute_h0_local(center_px, ruler_dets)
        h0_cm = h0_cm_local if h0_cm_local is not None else center_cm_global

        label_y = int(center_px) - 15
        if label_y < 20:
            label_y = int(center_px) + 20
        cv2.putText(display_img, f"H0={h0_cm:.2f}cm ({center_px:.1f}px)",
                    (10, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        mid_neg = int((neg_px + center_px) / 2)
        cv2.putText(display_img, f"Dx2={delta_neg_px:.1f}px={delta_neg_cm:.3f}cm",
                    (10, mid_neg), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 0), 1)

        mid_pos = int((center_px + pos_px) / 2)
        cv2.putText(display_img, f"Dx1={delta_pos_px:.1f}px={delta_pos_cm:.3f}cm",
                    (10, mid_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 0), 1)

    ax.imshow(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB))
    ax.set_title(f"{title_prefix}H0={h0_cm:.2f}cm  Dx1={delta_pos_cm:.3f}cm  Dx2={delta_neg_cm:.3f}cm"
                 if mapping else f"{title_prefix}Peak Detection", fontsize=9)
    ax.axis('off')

    return display_img


def _extract_roi_from_combined(rgb, three_peaks):
    if rgb is None:
        return None
    h, w = rgb.shape[:2]

    center_px = int(three_peaks['center']['pixel'])
    neg_px = int(three_peaks['neg']['pixel'])
    pos_px = int(three_peaks['pos']['pixel'])

    y_min = max(0, min(neg_px, center_px, pos_px) - 30)
    y_max = min(h, max(neg_px, center_px, pos_px) + 30)

    roi = rgb[y_min:y_max, :, :]
    return roi


def analyze_single(image_path, reader, output_dir):
    print(f"\n{'=' * 60}")
    bn = os.path.basename(image_path)
    print(f"  {bn}")
    print(f"{'=' * 60}")

    out_dir = os.path.join(output_dir, os.path.splitext(bn)[0])
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    print("\n--- 步骤1: SIREN拟合 + 子像素峰值定位 ---")
    try:
        pipeline = DiffractionAnalysisPipeline(image_path)
        pipeline.run(save_dir=out_dir)
    except Exception as e:
        print(f"  [ERROR] Pipeline failed: {e}")
        return None

    if not pipeline.system.three_peaks:
        print("  [ERROR] No peaks found")
        return None

    tp_system = pipeline.system.three_peaks
    print(f"  系统SIREN峰值:")
    print(f"    center={tp_system['center']['pixel']:.4f}px")
    print(f"    neg={tp_system['neg']['pixel']:.4f}px")
    print(f"    pos={tp_system['pos']['pixel']:.4f}px")

    print("\n--- 步骤2: 条纹峰值筛选（选最对称峰）---")
    fp = pipeline.results['_full_profile']
    profile = fp['profile']
    x_coords = fp['x_coords']

    three_peaks = find_bright_peaks(pipeline, override_profile=profile, override_x_coords=x_coords)

    if three_peaks is None:
        print("  [WARN] find_bright_peaks failed, falling back to system peaks")
        three_peaks = tp_system
    else:
        dx1_check = abs(three_peaks['pos']['pixel'] - three_peaks['center']['pixel'])
        dx2_check = abs(three_peaks['center']['pixel'] - three_peaks['neg']['pixel'])
        if dx1_check > 0 and dx2_check > 0:
            ratio = min(dx1_check, dx2_check) / max(dx1_check, dx2_check)
            print(f"  对称性检查: Dx1={dx1_check:.1f}px Dx2={dx2_check:.1f}px ratio={ratio:.3f}")
            if ratio < 0.5:
                print(f"  [WARN] 严重不对称 (ratio={ratio:.3f} < 0.5), 回退到系统SIREN峰值")
                three_peaks = tp_system

    pipeline.system.three_peaks = three_peaks

    print(f"\n  最终峰位:")
    print(f"    center: idx={three_peaks['center']['index']} I={three_peaks['center']['intensity']:.1f} px={three_peaks['center']['pixel']:.4f}")
    print(f"    neg:    idx={three_peaks['neg']['index']} I={three_peaks['neg']['intensity']:.1f} px={three_peaks['neg']['pixel']:.4f}")
    print(f"    pos:    idx={three_peaks['pos']['index']} I={three_peaks['pos']['intensity']:.1f} px={three_peaks['pos']['pixel']:.4f}")

    print("\n--- 步骤3: 标尺OCR识别 ---")
    mapping = pipeline.system.ruler_mapping
    ruler_detections = pipeline.system.ruler_detections

    if ruler_detections:
        print(f"  标尺OCR识别到 {len(ruler_detections)} 个文本:")
        for det in ruler_detections:
            print(f"    '{det['value']}' (置信度: {det['confidence']:.3f}) @ ({det['orig_y']}, {det['orig_x']})")

    if mapping:
        print(f"  标尺映射: cm = {mapping['slope']:.8f} * px + {mapping['intercept']:.4f}")
        print(f"  R² = {mapping['r_squared']:.6f}")

        for pt in mapping.get('anchors', []):
            val = pt['value']
            oy = pt['orig_y']
            predicted = mapping['slope'] * oy + mapping['intercept']
            print(f"    {val}cm @ y={oy}px | predicted={predicted:.2f}cm | conf={pt['confidence']:.3f}")

    print("\n--- 步骤4: 建立标尺映射 + 计算H0 ---")
    center_px = three_peaks['center']['pixel']

    if mapping:
        slope = mapping['slope']
        intercept = mapping['intercept']

        center_cm_global = slope * center_px + intercept
        neg_cm = slope * three_peaks['neg']['pixel'] + intercept
        pos_cm = slope * three_peaks['pos']['pixel'] + intercept

        h0_cm_local = _compute_h0_local(center_px, ruler_detections)
        h0_cm = h0_cm_local if h0_cm_local is not None else center_cm_global

        px_per_cm = 1.0 / abs(slope)
    else:
        h0_cm = None
        px_per_cm = None

    delta_neg_px = abs(center_px - three_peaks['neg']['pixel'])
    delta_pos_px = abs(three_peaks['pos']['pixel'] - center_px)

    if mapping:
        delta_neg_cm = abs(center_cm_global - neg_cm)
        delta_pos_cm = abs(pos_cm - center_cm_global)
        delta_avg_cm = (delta_neg_cm + delta_pos_cm) / 2
    else:
        delta_neg_cm = None
        delta_pos_cm = None
        delta_avg_cm = None

    if h0_cm is not None:
        print(f"  标尺映射: cm = {mapping['slope']:.8f} * px + {mapping['intercept']:.4f}")
        print(f"  R² = {mapping['r_squared']:.6f}")
        print(f"  中央亮纹位置: {center_px:.4f} px")
        print(f"  H0 = {h0_cm:.4f} cm")
        print(f"  Dx1 (+1级间距): {delta_pos_px:.4f} px = {delta_pos_cm:.6f} cm")
        print(f"  Dx2 (-1级间距): {delta_neg_px:.4f} px = {delta_neg_cm:.6f} cm")
        print(f"  Dx (平均间距):  {delta_avg_cm:.6f} cm")
    else:
        print(f"  [WARN] No ruler mapping available")
        print(f"  中央亮纹位置: {center_px:.4f} px")
        print(f"  Dx1 (+1级间距): {delta_pos_px:.4f} px")
        print(f"  Dx2 (-1级间距): {delta_neg_px:.4f} px")

    print("\n--- 步骤5: 输出验收图（原图标注6条线）---")
    original_img = cv2.imread(image_path)
    if original_img is None:
        print(f"  [ERROR] 无法读取原图: {image_path}")
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

    center_y = int(round(center_px))
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

    ann_path = os.path.join(out_dir, f"{os.path.splitext(bn)[0]}_annotated.png")
    cv2.imwrite(ann_path, ann)
    print(f"  验收图已保存: {ann_path}")

    combined_path = ann_path

    result = {
        'image': bn,
        'H0_cm': h0_cm,
        'delta_x1_px': delta_pos_px,
        'delta_x2_px': delta_neg_px,
        'delta_x1_cm': delta_pos_cm,
        'delta_x2_cm': delta_neg_cm,
        'delta_avg_cm': delta_avg_cm,
        'px_per_cm': px_per_cm,
        'center_px': center_px,
        'three_peaks': three_peaks,
        'ruler_mapping': mapping,
        'annotated_path': combined_path,
    }

    print(f"\n  ===== 结果汇总?=====")
    if h0_cm is not None:
        print(f"  H0 = {h0_cm:.4f} cm  ({center_px:.4f}px)")
        print(f"  Dx1 (+1级间距) = {delta_pos_px:.4f} px = {delta_pos_cm:.6f} cm")
        print(f"  Dx2 (-1级间距) = {delta_neg_px:.4f} px = {delta_neg_cm:.6f} cm")
        print(f"  Dx avg = {delta_avg_cm:.6f} cm")
    else:
        print(f"  H0 = N/A  ({center_px:.4f}px)")
        print(f"  Dx1 (+1级间距) = {delta_pos_px:.4f} px")
        print(f"  Dx2 (-1级间距) = {delta_neg_px:.4f} px")
    print(f"  验收图: {ann_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description='Combined analysis test')
    parser.add_argument('--image', '-i', help='Single image path')
    parser.add_argument('--output', '-o', default=OUTPUT_DIR, help='Output directory')
    args = parser.parse_args()

    print("=" * 70)
    print("  Combined Analysis Test: Ruler Mapping + SIREN Subpixel + Horizontal Profile")
    print("=" * 70)

    print("\n[1/3] Initializing EasyOCR reader...")
    reader = easyocr.Reader(['en'], gpu=False)
    print("  EasyOCR initialized")

    if args.image:
        images = [args.image]
    else:
        print(f"\n[2/3] Scanning test images from: {IMAGE_DIR}")
        images = get_test_images()
        if not images:
            print(f"  [ERROR] No test images found in {IMAGE_DIR}")
            return
        print(f"  Found {len(images)} images: {[os.path.basename(p) for p in images]}")

    print(f"\n[3/3] Processing images...")
    results = []
    for img_path in images:
        result = analyze_single(img_path, reader, args.output)
        if result:
            results.append(result)

    print(f"\n{'=' * 70}")
    print(f"  全部完成! {len(results)}/{len(images)} 成功")
    print(f"\n  {'图片':<30s} {'H0(cm)':>10s} {'Δx1(cm)':>10s} {'Δx2(cm)':>10s} {'Δx平均(cm)':>12s}")
    print(f"  {'-' * 29:<30s} {'-' * 10:>10s} {'-' * 10:>10s} {'-' * 10:>10s} {'-' * 12:>12s}")
    for r in results:
        h0 = f"{r['H0_cm']:.4f}" if r['H0_cm'] else "N/A"
        d1 = f"{r['delta_x1_cm']:.4f}" if r['delta_x1_cm'] else "N/A"
        d2 = f"{r['delta_x2_cm']:.4f}" if r['delta_x2_cm'] else "N/A"
        davg = f"{r['delta_avg_cm']:.4f}" if r['delta_avg_cm'] else "N/A"
        print(f"  {r['image']:<30s} {h0:>10s} {d1:>10s} {d2:>10s} {davg:>12s}")
    print(f"\n  结果目录: {args.output}")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
