import cv2
import numpy as np
import torch
from typing import Tuple, Dict


class DiffractionDataLoader:
    """衍射图像数据加载器"""
    
    def __init__(self, image_path: str):
        self.image_path = image_path
        self.original_image = None
        self.gray_image = None
        self.diffraction_region = None
        self.ruler_region = None
        self.image_tensor = None
        
    def load_image(self) -> np.ndarray:

        self.original_image = cv2.imread(self.image_path)
        if self.original_image is None:
            try:
                data = np.fromfile(self.image_path, dtype=np.uint8)
                self.original_image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            except Exception:
                self.original_image = None
        if self.original_image is None:
            raise FileNotFoundError(f"无法加载图像：{self.image_path}")
        return self.original_image
    
    def convert_to_gray(self, method: str = 'mean') -> np.ndarray:
        if self.original_image is None:
            self.load_image()
        
        if method == 'weighted':
            # 使用加权平均：0.299R + 0.587G + 0.114B
            self.gray_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        else:
            # 简单平均
            self.gray_image = np.mean(self.original_image, axis=2).astype(np.uint8)
        
        return self.gray_image
    
    def normalize_image(self, image: np.ndarray = None) -> torch.Tensor:
        if image is None:
            if self.gray_image is None:
                self.convert_to_gray()
            image = self.gray_image
        
        # Min-Max 归一化
        img_min = np.min(image)
        img_max = np.max(image)
        normalized = (image.astype(np.float32) - img_min) / (img_max - img_min + 1e-8)
        
        # 转换为 Tensor (C, H, W)
        self.image_tensor = torch.from_numpy(normalized).unsqueeze(0).float()
        return self.image_tensor
    
    def auto_crop_regions(self, diffraction_y_range: Tuple[int, int] = None,
                         ruler_x_range: Tuple[int, int] = None) -> Dict[str, np.ndarray]:
        if self.gray_image is None:
            self.convert_to_gray()
        
        height, width = self.gray_image.shape
        
        # 如果没有指定范围，使用自动检测
        if diffraction_y_range is None:
            # 自动检测衍射条纹区域（基于垂直投影）
            vertical_projection = np.sum(self.gray_image, axis=1)
            # 找到信号最强的区域
            threshold = 0.5 * np.max(vertical_projection)
            signal_indices = np.where(vertical_projection > threshold)[0]
            if len(signal_indices) > 0:
                y_min = max(0, signal_indices[0] - 10)
                y_max = min(height, signal_indices[-1] + 10)
            else:
                y_min, y_max = height // 3, 2 * height // 3
        
        if ruler_x_range is None:
            x_min = int(width * 0.8)
            x_max = width
        
        self.diffraction_region = self.gray_image
        
        self.ruler_region = self.gray_image[:, x_min:x_max]
        
        return {
            'diffraction': self.diffraction_region,
            'ruler': self.ruler_region,
            'full': self.gray_image
        }
    
    def _choose_profile_direction(self, image: np.ndarray) -> str:
        """
        判断条纹走向：毛细波衍射常见为水平条纹（沿图像 y 方向取剖面）。
        排除右侧标尺区域，避免把刻度误当作条纹。
        """
        from scipy.signal import find_peaks as fp
        from scipy.ndimage import gaussian_filter1d as gf

        height, width = image.shape
        strip_w = max(int(width * 0.72), width // 2)
        roi = image[:, :strip_w]

        h_proj = np.mean(roi, axis=0).astype(np.float64)
        v_proj = np.mean(roi, axis=1).astype(np.float64)
        h_smooth = gf(h_proj, sigma=3)
        v_smooth = gf(v_proj, sigma=3)

        v_dist = max(20, height // 35)
        h_dist = max(20, strip_w // 35)
        v_prom = max(float(np.std(v_smooth)) * 0.15, 2.0)
        h_prom = max(float(np.std(h_smooth)) * 0.15, 2.0)

        v_peaks, _ = fp(v_smooth, distance=v_dist, prominence=v_prom)
        h_peaks, _ = fp(h_smooth, distance=h_dist, prominence=h_prom)

        print(
            f"[调试] 方向检测 ROI宽={strip_w} — "
            f"垂直峰:{len(v_peaks)} 水平峰:{len(h_peaks)} 图像:{height}x{width}"
        )

        if len(v_peaks) >= 3 and len(h_peaks) < 3:
            return 'vertical'
        if len(h_peaks) >= 3 and len(v_peaks) < 3:
            return 'horizontal'
        if len(v_peaks) >= 3 and len(h_peaks) >= 3:
            if len(v_peaks) >= len(h_peaks):
                return 'vertical'
            return 'horizontal'
        if len(v_peaks) >= 2 and len(h_peaks) < 2:
            return 'vertical'
        if len(h_peaks) >= 2 and len(v_peaks) < 2:
            return 'horizontal'

        v_std = float(np.std(v_smooth))
        h_std = float(np.std(h_smooth))
        print(f"[DEBUG] 峰数不足，比较投影起伏 V_std={v_std:.2f} H_std={h_std:.2f}")
        return 'vertical' if v_std >= h_std * 0.85 else 'horizontal'

    def extract_horizontal_profile(self, image: np.ndarray = None,
                                   y_center: int = None) -> np.ndarray:
        if image is None:
            if self.diffraction_region is None:
                self.auto_crop_regions()
            image = self.diffraction_region

        direction = self._choose_profile_direction(image)
        if direction == 'vertical':
            print('[DEBUG] 使用垂直光强剖面（水平条纹 / 沿 y 寻峰）')
            return self._extract_vertical_profile(image)
        print('[DEBUG] 使用水平光强剖面（垂直条纹 / 沿 x 寻峰）')
        return self._extract_horizontal_classic(image)

    def _extract_vertical_profile(self, image: np.ndarray) -> np.ndarray:
        """
        提取垂直方向的光强分布（适用于垂直条纹）

        Args:
            image: 输入灰度图像

        Returns:
            垂直方向的光强分布（1D数组）
        """
        height, width = image.shape

        # 找中心位置（最亮的 x 列），排除最右侧 20% 避免标尺干扰
        search_width = max(width * 3 // 4, 1)
        vertical_proj = np.sum(image[:, :int(search_width)], axis=0)
        center_x = np.argmax(vertical_proj)

        # 取中心附近多列的平均以增强信噪比
        window = min(80, width // 5)
        x_start = max(0, center_x - window)
        x_end = min(width, center_x + window)

        print(f"[DEBUG] Vertical profile - center_x={center_x}, x_range=[{x_start}, {x_end}], search_width={int(search_width)}")

        # 计算平均剖面（沿垂直方向）
        strip = image[:, x_start:x_end]
        profile = np.mean(strip, axis=1).astype(np.float32)

        print(f"[DEBUG] Raw profile length: {len(profile)}")

        # 平滑
        from scipy.ndimage import gaussian_filter1d
        profile = cv2.GaussianBlur(profile.reshape(-1, 1), (1, 11), 0).flatten()

        # 尝试找 3 个峰并裁剪到局部区域
        from scipy.signal import find_peaks

        smoothed = gaussian_filter1d(profile, sigma=4)
        peaks, properties = find_peaks(smoothed, distance=max(30, height//30),
                                        prominence=max(2, np.std(smoothed) * 0.2))

        print(f"[DEBUG] Detected {len(peaks)} candidate peaks in vertical profile")

        if len(peaks) >= 3:
            peak_heights = smoothed[peaks]
            top_3_idx = np.argsort(peak_heights)[-3:][::-1]
            top_3_peaks = sorted(peaks[top_3_idx])

            print(f"[DEBUG] Top-3 peak positions (image Y): {top_3_peaks}")
            print(f"[DEBUG] Top-3 peak intensities: {[f'{smoothed[p]:.1f}' for p in top_3_peaks]}")

            dx1 = top_3_peaks[1] - top_3_peaks[0]
            dx2 = top_3_peaks[2] - top_3_peaks[1]
            margin = int(max(dx1, dx2) * 0.8)
            margin = max(margin, 50)

            y_start = max(0, top_3_peaks[0] - margin)
            y_end = min(height, top_3_peaks[2] + margin)

            profile = profile[y_start:y_end]

            self.profile_crop_info = {
                'direction': 'vertical',
                'y_start': y_start,
                'y_end': y_end,
                'peak_positions': [p - y_start for p in top_3_peaks],
                'original_height': height,
                'original_peak_positions': top_3_peaks,
                'peak_intensities': [smoothed[p] for p in top_3_peaks]
            }

            print(f"[DEBUG] Cropped to [{y_start}, {y_end}], final length: {len(profile)}")
        elif len(peaks) >= 2:
            peak_heights = smoothed[peaks]
            top_2_idx = np.argsort(peak_heights)[-2:][::-1]
            top_2_peaks = sorted(peaks[top_2_idx])
            margin = int((top_2_peaks[1] - top_2_peaks[0]) * 1.2)
            margin = max(margin, 100)
            y_start = max(0, top_2_peaks[0] - margin)
            y_end = min(height, top_2_peaks[1] + margin)
            profile = profile[y_start:y_end]

            self.profile_crop_info = {
                'direction': 'vertical',
                'y_start': y_start,
                'y_end': y_end,
                'peak_positions': [p - y_start for p in top_2_peaks],
                'original_height': height,
                'original_peak_positions': top_2_peaks,
                'peak_intensities': [smoothed[p] for p in top_2_peaks]
            }
            print(f"[DEBUG] Only {len(peaks)} peaks found, cropped to [{y_start},{y_end}]")
        else:
            print(f"[DEBUG] Less than 2 peaks found, returning full profile")
            self.profile_crop_info = None

        return profile

    def _extract_horizontal_classic(self, image: np.ndarray) -> np.ndarray:
        """
        经典的水平剖面提取（适用于水平条纹）

        Args:
            image: 输入灰度图像

        Returns:
            水平方向的光强分布（1D数组）
        """
        height, width = image.shape

        # 找到中心位置（最亮的 y 行）
        horizontal_proj = np.sum(image, axis=1)
        center_y = np.argmax(horizontal_proj)

        # 取中心附近多行的平均以增强信噪比
        window = min(100, height // 4)
        y_start = max(0, center_y - window)
        y_end = min(height, center_y + window)

        # 计算平均剖面
        profile = np.mean(image[y_start:y_end, :], axis=0).astype(np.float32)

        # 平滑
        profile = cv2.GaussianBlur(profile.reshape(1, -1), (15, 1), 0).flatten()

        # 尝试找 3 个峰并裁剪到局部区域
        from scipy.signal import find_peaks
        from scipy.ndimage import gaussian_filter1d

        smoothed = gaussian_filter1d(profile, 5)
        peaks, _ = find_peaks(smoothed, distance=100, prominence=5)

        if len(peaks) >= 3:
            # 找最强的 3 个峰
            peak_heights = smoothed[peaks]
            top_3_idx = np.argsort(peak_heights)[-3:][::-1]
            top_3_peaks = sorted(peaks[top_3_idx])

            # 计算间距和裁剪范围
            dx1 = top_3_peaks[1] - top_3_peaks[0]
            dx2 = top_3_peaks[2] - top_3_peaks[1]
            margin = max(dx1, dx2) * 0.7

            x_start = max(0, int(top_3_peaks[0] - margin))
            x_end = min(width, int(top_3_peaks[2] + margin))

            # 裁剪到局部区域
            profile = profile[x_start:x_end]

            # 保存裁剪信息供后续使用
            self.profile_crop_info = {
                'direction': 'horizontal',
                'x_start': x_start,
                'x_end': x_end,
                'peak_positions': [p - x_start for p in top_3_peaks],
                'original_width': width
            }

        return profile
    
    def get_coordinates(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取像素坐标（用于后续物理坐标转换）

        Returns:
            (坐标数组, 坐标数组) - 根据剖面方向返回对应的坐标
        """
        if self.diffraction_region is None:
            self.auto_crop_regions()

        # 如果有裁剪信息，使用裁剪后的范围
        if hasattr(self, 'profile_crop_info') and self.profile_crop_info:
            direction = self.profile_crop_info.get('direction', 'horizontal')

            if direction == 'vertical':
                # 垂直剖面：返回y坐标
                y_start = self.profile_crop_info['y_start']
                y_end = self.profile_crop_info['y_end']
                coords = np.arange(y_end - y_start) + y_start  # 保持原始坐标
            else:
                # 水平剖面：返回x坐标
                x_start = self.profile_crop_info['x_start']
                x_end = self.profile_crop_info['x_end']
                coords = np.arange(x_end - x_start) + x_start  # 保持原始坐标
        else:
            # 无裁剪信息，使用完整范围
            height, width = self.diffraction_region.shape
            # 默认使用宽度（水平方向）
            coords = np.arange(width)

        # 返回两个相同的数组（兼容性）
        return coords, coords
    
    def process(self) -> Dict:
        """
        完整的图像处理流程
        
        Returns:
            包含所有处理结果的字典
        """
        # 1. 加载图像
        self.load_image()
        
        # 2. 转换为灰度图
        self.convert_to_gray()
        
        # 3. 归一化
        self.normalize_image()
        
        # 4. 自动剪切区域
        regions = self.auto_crop_regions()
        
        # 5. 提取水平剖面
        profile = self.extract_horizontal_profile()
        
        # 6. 获取坐标
        x_coords, y_coords = self.get_coordinates()
        
        return {
            'original': self.original_image,
            'gray': self.gray_image,
            'tensor': self.image_tensor,
            'regions': regions,
            'profile': profile,
            'x_coords': x_coords,
            'y_coords': y_coords,
            'diffraction_region': self.diffraction_region,
            'ruler_region': self.ruler_region
        }


def load_and_process_image(image_path: str, return_loader: bool = False):
    """
    便捷函数：加载并处理衍射图像
    
    Args:
        image_path: 图像路径
        return_loader: 是否同时返回loader实例
        
    Returns:
        处理结果字典，或者 (字典, loader) 元组
    """
    loader = DiffractionDataLoader(image_path)
    result = loader.process()
    if return_loader:
        return result, loader
    return result


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        print("请提供图像路径")
        sys.exit(1)
    
    result = load_and_process_image(image_path)
    print(f"图像加载成功：{result['original'].shape}")
    print(f"灰度图：{result['gray'].shape}")
    print(f"衍射区域：{result['diffraction_region'].shape}")
    print(f"标尺区域：{result['ruler_region'].shape}")
    print(f"光强剖面：{result['profile'].shape}")
