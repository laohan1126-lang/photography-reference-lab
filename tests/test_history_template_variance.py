"""The faster flat-template check preserves the original channel-wise threshold."""
import cv2
import numpy as np
import pytest

from ref_lab.collection_history import _MatchContext


@pytest.mark.parametrize('amplitude', [0, 1, 2, 3, 4, 8, 32, 127])
def test_area_template_decision_matches_original_variance(amplitude):
    rng = np.random.default_rng(601)
    images = [rng.integers(128-amplitude, 129+amplitude, (128, 128, 3), dtype=np.uint8)]
    edge = np.full((128, 128, 3), 128-amplitude, dtype=np.uint8)
    edge[:, 64:, :] = 128+amplitude
    images.append(edge)
    for image in images:
        context = _MatchContext(candidate='query')
        query = {'asset_sha': 'query', 'arr': image}
        for width, height in [(2, 2), (3, 5), (7, 9), (16, 16), (32, 32), (64, 64)]:
            expected = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
            usable = bool(expected.reshape(-1, 3).std(axis=0).max() >= 3)
            actual, accepted = context.template(0, query, 'area', width, height, 32)
            assert accepted == usable
            if usable:
                np.testing.assert_array_equal(actual, expected)
            assert context.template(0, query, 'area', width, height, 32)[1] == usable
