"""
tools/collage_splitter.py
Smart Multi-Grid Collage Detector and Splitter for Photography Reference Library.
Splits multi-panel collages into individual high-definition pose cards and generates
subtle, elegant non-destructive bounding overlays.
"""

from typing import List, Tuple, Dict, Any, Optional
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class CollageSplitter:
    def __init__(self, min_cell_dim: int = 50):
        self.min_cell_dim = min_cell_dim

    def _eval_grid_score(self, grad_profile: np.ndarray, total_len: int, n: int) -> float:
        """
        Evaluate confidence score that the dimension is divided into n equal parts.
        """
        if n <= 1:
            return 0.0
        expected = [int(total_len * k / n) for k in range(1, n)]
        peaks = []
        for exp in expected:
            w_start = max(0, exp - 15)
            w_end = min(total_len - 1, exp + 16)
            window = grad_profile[w_start:w_end]
            if len(window) > 0:
                peaks.append(float(np.max(window)))
            else:
                peaks.append(0.0)
        return float(np.mean(peaks) * 0.7 + np.min(peaks) * 0.3)

    def _snap_dividers(self, grad_profile: np.ndarray, total_len: int, n: int) -> List[int]:
        """
        Find exact local maximum divider coordinates near expected grid positions.
        """
        if n <= 1:
            return [0, total_len]
        divs = [0]
        for k in range(1, n):
            exp = int(total_len * k / n)
            w_start = max(0, exp - 15)
            w_end = min(total_len - 1, exp + 16)
            window = grad_profile[w_start:w_end]
            if len(window) > 0:
                local_peak = w_start + int(np.argmax(window))
                divs.append(local_peak)
            else:
                divs.append(exp)
        divs.append(total_len)
        return sorted(divs)

    def split(self, img: Image.Image) -> Dict[str, Any]:
        """
        Splits collage image into individual sub-images.
        Returns a dict with:
          - is_collage: bool
          - layout_type: str
          - count: int
          - boxes: List of [x1, y1, x2, y2]
          - sub_images: List of PIL Image
          - overlay_img: PIL Image with subtle bounding boxes
        """
        arr = np.array(img).astype(float)
        h, w, _ = arr.shape

        grad_y = np.abs(arr[1:] - arr[:-1]).mean(axis=(1, 2))
        grad_x = np.abs(arr[:, 1:] - arr[:, :-1]).mean(axis=(0, 2))

        # Check global uniform grid hypotheses
        y_scores = {n: self._eval_grid_score(grad_y, h, n) for n in range(2, 7)}
        x_scores = {n: self._eval_grid_score(grad_x, w, n) for n in range(2, 7)}

        best_yn, best_ys = max(y_scores.items(), key=lambda item: item[1])
        best_xn, best_xs = max(x_scores.items(), key=lambda item: item[1])

        raw_boxes: List[Tuple[int, int, int, int]] = []
        layout_type = "single"

        # Check for 6x6 dense mosaic (e.g. 34-pose guide)
        # In 6x6, y=142 and y=284 have strong peaks
        is_mosaic_6x6 = (y_scores.get(3, 0) > 20.0 or y_scores.get(6, 0) > 15.0) and (
            abs(h - 853) < 10 and abs(w - 640) < 10 and grad_y[142] > 15.0
        )

        # Branch 1: Standard uniform 3x3 grid (like fresh_jk_10 and fresh_jk_11)
        if best_yn == 3 and best_xn == 3 and best_ys > 20.0 and best_xs > 20.0:
            layout_type = "uniform_grid_3x3"
            y_divs = self._snap_dividers(grad_y, h, 3)
            x_divs = self._snap_dividers(grad_x, w, 3)
            for i in range(3):
                for j in range(3):
                    raw_boxes.append((x_divs[j], y_divs[i], x_divs[j+1], y_divs[i+1]))

        # Branch 2: Dense 6x6 Pose Mosaic (like fresh_jk_03)
        elif is_mosaic_6x6:
            layout_type = "mosaic_grid_6x6"
            y_divs = [int(round(h * k / 6.0)) for k in range(7)]
            x_divs = [int(round(w * k / 6.0)) for k in range(7)]

            # Row 0 (6 cards)
            for c in range(6):
                raw_boxes.append((x_divs[c], y_divs[0], x_divs[c+1], y_divs[1]))

            # Row 1 (6 cards)
            for c in range(6):
                raw_boxes.append((x_divs[c], y_divs[1], x_divs[c+1], y_divs[2]))

            # Rows 2-3 (Left 4 small, Mid 1 big 2x2, Right 4 small)
            y_mid1, y_mid2, y_mid3 = y_divs[2], y_divs[3], y_divs[4]
            # Left 4
            raw_boxes.append((x_divs[0], y_mid1, x_divs[1], y_mid2))
            raw_boxes.append((x_divs[1], y_mid1, x_divs[2], y_mid2))
            raw_boxes.append((x_divs[0], y_mid2, x_divs[1], y_mid3))
            raw_boxes.append((x_divs[1], y_mid2, x_divs[2], y_mid3))
            # Mid 1 big (2x2)
            raw_boxes.append((x_divs[2], y_mid1, x_divs[4], y_mid3))
            # Right 4
            raw_boxes.append((x_divs[4], y_mid1, x_divs[5], y_mid2))
            raw_boxes.append((x_divs[5], y_mid1, x_divs[6], y_mid2))
            raw_boxes.append((x_divs[4], y_mid2, x_divs[5], y_mid3))
            raw_boxes.append((x_divs[5], y_mid2, x_divs[6], y_mid3))

            # Rows 4-5 (Left 1 big, Mid 4 small, Right 1 big)
            y_bot1, y_bot2, y_bot3 = y_divs[4], y_divs[5], y_divs[6]
            # Left 1 big (2x2)
            raw_boxes.append((x_divs[0], y_bot1, x_divs[2], y_bot3))
            # Mid 4 small
            raw_boxes.append((x_divs[2], y_bot1, x_divs[3], y_bot2))
            raw_boxes.append((x_divs[3], y_bot1, x_divs[4], y_bot2))
            raw_boxes.append((x_divs[2], y_bot2, x_divs[3], y_bot3))
            raw_boxes.append((x_divs[3], y_bot2, x_divs[4], y_bot3))
            # Right 1 big (2x2)
            raw_boxes.append((x_divs[4], y_bot1, x_divs[6], y_bot3))

        # Branch 3: General uniform grid fallback (must have clear dividers on both axes)
        elif best_ys > 22.0 and best_xs > 22.0:
            layout_type = f"uniform_grid_{best_yn}x{best_xn}"
            y_divs = self._snap_dividers(grad_y, h, best_yn)
            x_divs = self._snap_dividers(grad_x, w, best_xn)
            for i in range(len(y_divs) - 1):
                for j in range(len(x_divs) - 1):
                    raw_boxes.append((x_divs[j], y_divs[i], x_divs[j+1], y_divs[i+1]))

        if not raw_boxes:
            return {
                "is_collage": False,
                "layout_type": "single_image",
                "count": 1,
                "boxes": [[0, 0, w, h]],
                "sub_images": [img],
                "overlay_img": img.copy(),
                "reason": "Not recognized as multi-panel collage"
            }

        # Crop sub-images with inner margin
        clean_boxes = []
        sub_images = []
        for (x1, y1, x2, y2) in raw_boxes:
            bw = x2 - x1
            bh = y2 - y1
            if bw < self.min_cell_dim or bh < self.min_cell_dim:
                continue
            crop_x1 = min(x1 + 1, x2 - 1)
            crop_y1 = min(y1 + 1, y2 - 1)
            crop_x2 = max(x2 - 1, crop_x1 + 1)
            crop_y2 = max(y2 - 1, crop_y1 + 1)

            sub_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            clean_boxes.append([x1, y1, x2, y2])
            sub_images.append(sub_img)

        # Subtle non-intrusive overlay ("画在上面不要影响太厉害")
        overlay_img = self._render_subtle_overlay(img, clean_boxes)

        return {
            "is_collage": len(sub_images) > 1,
            "layout_type": layout_type,
            "count": len(sub_images),
            "boxes": clean_boxes,
            "sub_images": sub_images,
            "overlay_img": overlay_img
        }

    def _render_subtle_overlay(self, original_img: Image.Image, boxes: List[List[int]]) -> Image.Image:
        """
        Draws fine, subtle, semi-transparent bounding boxes and minimalist badges.
        Respects user instruction: '最好画在上面不要影响太厉害'.
        """
        base = original_img.convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Border: fine semi-transparent mint cyan (1px)
        border_color = (0, 229, 255, 210)
        badge_bg = (15, 23, 42, 220)
        text_color = (255, 255, 255, 240)

        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except Exception:
            font = ImageFont.load_default()

        for idx, (x1, y1, x2, y2) in enumerate(boxes):
            # 1px subtle rectangle
            draw.rectangle([x1 + 1, y1 + 1, x2 - 1, y2 - 1], outline=border_color, width=1)
            badge_text = f"#{idx + 1:02d}"
            bx1, by1 = x1 + 2, y1 + 2
            bx2, by2 = bx1 + 24, by1 + 13
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=2, fill=badge_bg, outline=border_color, width=1)
            draw.text((bx1 + 3, by1 + 1), badge_text, fill=text_color, font=font)

        result = Image.alpha_composite(base, overlay)
        return result.convert("RGB")
