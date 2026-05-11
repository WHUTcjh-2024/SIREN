import cv2
import numpy as np
import easyocr
import shutil
import tempfile
import os
import re
from typing import List, Dict, Optional


class RulerReader:
    """刻度尺读取器 — 基于EasyOCR的10/20/30cm定位"""

    def __init__(self, languages: List[str] = ['en'], gpu: bool = False):
        self.reader = easyocr.Reader(languages, gpu=gpu)
        self.ruler_detections = []
        self.mapping = None

    @staticmethod
    def _ascii_path(path: str) -> str:
        try:
            path.encode('ascii')
            return path
        except UnicodeEncodeError:
            d = tempfile.gettempdir()
            dst = os.path.join(d, "_ruler_tmp.png")
            shutil.copy2(path, dst)
            return dst

    @staticmethod
    def _extract_digits(text: str) -> str:
        return ''.join(c for c in text if c.isdigit())

    @staticmethod
    def _match_priority(text: str, target: int) -> int:
        cleaned = RulerReader._extract_digits(text)
        if cleaned == str(target):
            return 3
        if target == 30 and cleaned in ('3O', '3o', '3Q', '30'):
            return 2
        if target == 20 and cleaned in ('2O', '2o', '2Q', 'Z0', '20'):
            return 2
        if target == 10 and cleaned in ('1O', '1o', '1Q', 'l0', '10'):
            return 2
        if target == 30 and cleaned == '3':
            return 1
        if target == 20 and cleaned == '2':
            return 1
        if target == 10 and cleaned == '1':
            return 1
        return 0

    def detect_ruler_numbers(self, image_path: str) -> List[Dict]:
        ascii_path = self._ascii_path(image_path)
        img = cv2.imread(ascii_path)
        if img is None:
            raise FileNotFoundError(f"无法加载图像: {image_path}")

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        crop_x = int(w * 0.65)
        crop = gray[:, crop_x:]
        crop_h, crop_w = crop.shape

        rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)

        enhanced = cv2.bitwise_not(rotated)
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(enhanced)

        gamma = np.power(rotated.astype(np.float32) / 255.0, 0.6) * 255.0
        gamma = gamma.astype(np.uint8)

        all_results = []
        for img_pass, label in [(rotated, 'raw'), (enhanced, 'enhanced'), (gamma, 'gamma')]:
            results = self.reader.readtext(img_pass)
            for (bbox, text, conf) in results:
                if conf < 0.05:
                    continue
                cx_rot = float(np.mean([p[0] for p in bbox]))
                cy_rot = float(np.mean([p[1] for p in bbox]))
                orig_y = crop_h - 1 - int(round(cx_rot))
                orig_x = crop_x + int(round(cy_rot))
                if not (0 <= orig_y < h):
                    continue
                all_results.append({
                    'value': -1,
                    'text': text.strip(),
                    'conf': float(conf),
                    'orig_y': orig_y,
                    'orig_x': orig_x,
                    'pass': label,
                })

        best_match = {}
        for r in all_results:
            for target in (30, 20, 10):
                prio = self._match_priority(r['text'], target)
                if prio > 0:
                    key = (target, r['text'].strip(), r['pass'])
                    if target not in best_match or prio > best_match[target][0] or (
                            prio == best_match[target][0] and r['conf'] > best_match[target][1]['conf']):
                        best_match[target] = (prio, r)

        found = {}
        match_log = []
        for target in (30, 20, 10):
            if target in best_match:
                prio, r = best_match[target]
                found[target] = {
                    'value': target,
                    'orig_y': r['orig_y'],
                    'orig_x': r['orig_x'],
                    'confidence': r['conf'],
                    'text': r['text'],
                    'pass': r['pass'],
                    '_prio': prio,
                }
                match_log.append(f"{target}cm@y={r['orig_y']}(prio={prio},text='{r['text']}',conf={r['conf']:.2f},pass={r['pass']})")

        print(f"  [Ruler OCR] Matched: {', '.join(match_log)}")

        found = self._deduplicate(found)

        valid_vals = [v for v in (30, 20, 10) if v in found]

        def _infer_missing(found, h):
            if 20 in found and 30 in found and 10 not in found:
                y20, y30 = found[20]['orig_y'], found[30]['orig_y']
                d = abs(y30 - y20)
                y10 = y20 + d if y30 < y20 else y20 - d
                if 0 <= y10 < h:
                    found[10] = {
                        'value': 10, 'orig_y': int(round(y10)),
                        'orig_x': found[20]['orig_x'],
                        'confidence': -1, 'inferred': True,
                    }

            if 10 in found and 20 in found and 30 not in found:
                y10, y20 = found[10]['orig_y'], found[20]['orig_y']
                d = abs(y20 - y10)
                y30 = y20 - d if y20 > y10 else y20 + d
                if 0 <= y30 < h:
                    found[30] = {
                        'value': 30, 'orig_y': int(round(y30)),
                        'orig_x': found[20]['orig_x'],
                        'confidence': -1, 'inferred': True,
                    }

            if 10 in found and 30 in found and 20 not in found:
                y10, y30 = found[10]['orig_y'], found[30]['orig_y']
                d = abs(y30 - y10)
                y20 = y10 + d // 2 if y10 < y30 else y10 - d // 2
                if 0 <= y20 < h:
                    found[20] = {
                        'value': 20, 'orig_y': int(round(y20)),
                        'orig_x': found[10]['orig_x'],
                        'confidence': -1, 'inferred': True,
                    }

        _infer_missing(found, h)

        if 10 in found and 20 in found and 30 in found:
            y10, y20, y30 = found[10]['orig_y'], found[20]['orig_y'], found[30]['orig_y']
            d_10_20 = abs(y20 - y10)
            d_20_30 = abs(y30 - y20)
            if d_10_20 > 0 and d_20_30 > 0:
                ratio = d_10_20 / max(d_20_30, 1)
                if ratio < 0.2 or ratio > 5.0:
                    pairs_sorted = sorted([(10, y10), (20, y20), (30, y30)], key=lambda x: x[1])
                    if pairs_sorted[0][0] == 30:
                        found[10]['orig_y'] = pairs_sorted[2][1]
                        found[20]['orig_y'] = pairs_sorted[1][1]
                        found[30]['orig_y'] = pairs_sorted[0][1]
                    elif pairs_sorted[2][0] == 10:
                        found[10]['orig_y'] = pairs_sorted[0][1]
                        found[20]['orig_y'] = pairs_sorted[1][1]
                        found[30]['orig_y'] = pairs_sorted[2][1]

        seen_y = {}
        for val in list(found.keys()):
            y = found[val]['orig_y']
            if y in seen_y:
                if val < seen_y[y]:
                    found.pop(val, None)
                else:
                    found.pop(seen_y[y], None)
                    seen_y[y] = val
            else:
                seen_y[y] = val

        detections = sorted(found.values(), key=lambda x: -x['value'])
        if detections:
            print(f"  [Ruler OCR] Found {len(detections)} marks: " +
                  ", ".join(f"{d['value']}cm@y={d['orig_y']}" +
                            (f"(conf={d['confidence']:.2f})" if not d.get('inferred') else "(inf)")
                            for d in detections))
        else:
            print(f"  [Ruler OCR] No marks detected. Raw text samples: " +
                  ", ".join(f"'{r['text']}'({r['conf']:.2f})" for r in all_results[:8]))

        self.ruler_detections = detections
        return detections

    def _deduplicate(self, found: dict) -> dict:
        items = list(found.items())
        to_remove = set()
        for i, (v1, d1) in enumerate(items):
            for j, (v2, d2) in enumerate(items):
                if v1 >= v2 or v1 in to_remove or v2 in to_remove:
                    continue
                if abs(d1['orig_y'] - d2['orig_y']) < 40:
                    if d1.get('inferred') and not d2.get('inferred'):
                        to_remove.add(v1)
                    elif d2.get('inferred') and not d1.get('inferred'):
                        to_remove.add(v2)
                    elif d1['confidence'] < d2['confidence']:
                        to_remove.add(v1)
                    elif d1['confidence'] > d2['confidence']:
                        to_remove.add(v2)
                    else:
                        to_remove.add(min(v1, v2))
        for v in to_remove:
            found.pop(v, None)
        return found

    @staticmethod
    def build_ruler_mapping(detections: List[Dict]) -> Optional[Dict]:
        if len(detections) < 2:
            return None
        pixels = np.array([d['orig_y'] for d in detections])
        cms = np.array([d['value'] for d in detections])
        slope, intercept = np.polyfit(pixels, cms, 1)
        predicted = slope * pixels + intercept
        ss_res = np.sum((cms - predicted) ** 2)
        ss_tot = np.sum((cms - np.mean(cms)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'n_points': len(detections),
            'anchors': detections,
        }

    @staticmethod
    def pixel_to_cm(mapping: Dict, pixel_y: float) -> float:
        return mapping['slope'] * pixel_y + mapping['intercept']

    def calibrate(self, image_path: str) -> Dict:
        detections = self.detect_ruler_numbers(image_path)
        mapping = self.build_ruler_mapping(detections)
        self.mapping = mapping
        return {
            'detections': detections,
            'mapping': mapping,
            'scale_factor': mapping['slope'] if mapping else None,
            'detected_count': len(detections),
        }

    @staticmethod
    def _detect_ruler_column(gray: np.ndarray) -> int:
        h, w = gray.shape
        right_part = gray[:, int(w * 0.6):]
        rp_h, rp_w = right_part.shape
        vertical_std = np.std(right_part, axis=0)
        col_idx = np.argmax(vertical_std)
        ruler_x = int(w * 0.6) + col_idx
        return ruler_x

    def _preprocess_pipelines(self, crop: np.ndarray) -> List[Dict]:
        rotated = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
        results = []
        results.append({'name': 'raw', 'image': rotated.copy(), 'weight': 1.0})
        enhanced2 = cv2.bitwise_not(rotated)
        clahe2 = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced2 = clahe2.apply(enhanced2)
        results.append({'name': 'invert_clahe', 'image': enhanced2, 'weight': 1.2})
        return results


class TPSCorrector:
    def __init__(self):
        self.transform_matrix = None

    def correct(self, image: np.ndarray, ruler_data: Dict = None) -> np.ndarray:
        return image


class CalibrationPipeline:
    def __init__(self, languages: List[str] = ['en'], gpu: bool = False):
        self.ruler_reader = RulerReader(languages=languages, gpu=gpu)
        self.calibration_result = None

    def process(self, image_path: str) -> Dict:
        self.calibration_result = self.ruler_reader.calibrate(image_path)
        return self.calibration_result