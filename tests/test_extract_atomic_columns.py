import importlib.util
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = Path(__file__).parents[1] / "tools" / "extract_atomic_columns.py"
SPEC = importlib.util.spec_from_file_location("extract_atomic_columns", MODULE_PATH)
extractor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(extractor)


class AtomicColumnExtractionTest(unittest.TestCase):
    def test_subpixel_centers_on_synthetic_lattice(self):
        rng = np.random.default_rng(42)
        shape = (128, 144)
        yy, xx = np.indices(shape)
        truth = []
        image = np.full(shape, 0.08)
        for row in range(6):
            for col in range(7):
                x = 13.35 + col * 18.0 + row * 0.22
                y = 13.62 + row * 18.0 + col * 0.14
                truth.append((x, y))
                image += 0.75 * np.exp(-0.5 * (((xx - x) / 1.35) ** 2 + ((yy - y) / 1.65) ** 2))
        image += rng.normal(0.0, 0.008, shape)

        peaks, _ = extractor.detect_columns(image, spacing=18.0, threshold_sigma=3.2)
        measured = np.array([[p["x_px"], p["y_px"]] for p in peaks])
        expected = np.array(truth)
        errors = np.sqrt(((expected[:, None, :] - measured[None, :, :]) ** 2).sum(axis=2)).min(axis=1)

        self.assertEqual(len(peaks), len(truth))
        self.assertLess(float(np.median(errors)), 0.10)
        self.assertLess(float(np.max(errors)), 0.18)


if __name__ == "__main__":
    unittest.main()
