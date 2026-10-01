from __future__ import annotations

import json
from pathlib import Path
import pytest

from PIL import Image

# Benchmark Ground-Truth indices validated by human aesthetic curator
KANA_GOLDEN_INDICES = [1, 2, 3, 4, 15, 34, 46, 49, 58, 72]
XISHI_GOLDEN_INDICES = [1, 3, 4, 12, 16, 20, 23, 35, 36, 47, 53, 56, 64, 71, 72]

# False positives that must be filtered out
NEGATIVE_SAMPLES = [
    ("喵屋和次元依西施详细对比", "对比"),
    ("喵屋小铺vs三分妄想西施原皮对比", "对比"),
    ("西施原皮盘点ing", "盘点"),
    ("这个摄影拍的什么东西，这么黑", "拍的什么东西"),
    ("西施cos 某🐟后期 拿美颜来骗钱跑路", "跑路"),
    ("【西施】新版官方建模三视图", "建模"),
    ("总150🥕集齐各家优点的漫好音西施cos", "测评"),
    ("宿迁cos体验馆 西施cos正片一条龙", "一条龙"),
    ("张雅倩的西施cos服是哪家的呀？", "cos服"),
    ("大家都在搜", "大家都在搜"),
]


def test_aesthetic_funnel_rejects_buyer_and_scandal_noise():
    from tools.sample_benchmark_200 import NEGATIVE_TYPE_MARKERS
    
    # Verify our negative markers library catches all buyer-review & scam/rant posts
    for title, expected_hit in NEGATIVE_SAMPLES:
        hit = any(marker in title for marker in NEGATIVE_TYPE_MARKERS)
        assert hit, f"Expected negative marker for '{title}', but none hit"


def test_golden_aesthetic_samples_pass_dimension_and_quality_gates():
    kana_manifest_path = Path(r"D:\AI PROJECTS\inspection-arima-kana-100\manifest.json")
    xishi_manifest_path = Path(r"D:\AI PROJECTS\inspection-xishi-100\manifest.json")

    if not kana_manifest_path.is_file() or not xishi_manifest_path.is_file():
        pytest.skip("Manifest files not found locally, skipping live manifest check")

    kana_data = json.loads(kana_manifest_path.read_text(encoding="utf-8"))
    xishi_data = json.loads(xishi_manifest_path.read_text(encoding="utf-8"))

    # Test Kana Golden 10
    kana_items = [d for d in kana_data if d["index"] in KANA_GOLDEN_INDICES]
    assert len(kana_items) == 10
    for it in kana_items:
        w, h = [int(x) for x in it["dimensions"].split("x")]
        assert max(w, h) >= 600, f"Kana #{it['index']} failed max dimension check"
        assert min(w, h) >= 240, f"Kana #{it['index']} failed min dimension check"

    # Test Xishi Golden 15
    xishi_items = [d for d in xishi_data if d["index"] in XISHI_GOLDEN_INDICES]
    assert len(xishi_items) == 15
    for it in xishi_items:
        w, h = [int(x) for x in it["dimensions"].split("x")]
        assert max(w, h) >= 600, f"Xishi #{it['index']} failed max dimension check"
        assert min(w, h) >= 240, f"Xishi #{it['index']} failed min dimension check"
