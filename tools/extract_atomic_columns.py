#!/usr/bin/env python3
"""Extract subpixel atomic-column coordinates from a ptychographic TIFF.

The implementation deliberately depends only on NumPy and tifffile/Pillow.  It
is an offline analysis tool: none of its dependencies are used by the
self-contained browser game.

The detector is designed for bright atomic columns on a slowly varying dark
background.  It uses a difference-of-Gaussians band-pass, non-maximum
suppression, and a local two-dimensional quadratic fit for subpixel centers.
Every retained peak is measured again on the original image so the exported
intensity and elliptical second moments remain tied to the reconstruction.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw


def robust_scale(image: np.ndarray) -> tuple[np.ndarray, float, float]:
    lo, hi = np.percentile(image[np.isfinite(image)], (0.5, 99.8))
    if hi <= lo:
        raise ValueError("image has no usable intensity range")
    return np.clip((image - lo) / (hi - lo), 0.0, 1.0), float(lo), float(hi)


def gaussian_blur_fft(image: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur with reflected padding and no SciPy dependency."""
    if sigma <= 0:
        return image.astype(np.float64, copy=True)
    pad = max(4, int(math.ceil(4 * sigma)))
    padded = np.pad(image, pad, mode="reflect")
    fy = np.fft.fftfreq(padded.shape[0])[:, None]
    fx = np.fft.rfftfreq(padded.shape[1])[None, :]
    transfer = np.exp(-2.0 * math.pi**2 * sigma**2 * (fx * fx + fy * fy))
    blurred = np.fft.irfft2(np.fft.rfft2(padded) * transfer, s=padded.shape)
    return blurred[pad:-pad, pad:-pad]


def estimate_spacing(image: np.ndarray) -> float:
    """Estimate the nearest-column spacing from the first autocorrelation ring."""
    work = image - gaussian_blur_fft(image, max(image.shape) / 18.0)
    win = np.outer(np.hanning(work.shape[0]), np.hanning(work.shape[1]))
    spectrum = np.fft.fft2(work * win)
    ac = np.fft.fftshift(np.fft.ifft2(np.abs(spectrum) ** 2).real)
    ac /= max(float(ac.max()), np.finfo(float).eps)

    yy, xx = np.indices(ac.shape)
    cy, cx = (np.array(ac.shape) - 1) / 2.0
    rr = np.hypot(xx - cx, yy - cy)
    max_r = min(image.shape) // 5
    bins = np.arange(max_r + 1)
    sums = np.bincount(np.minimum(rr.astype(int), max_r).ravel(), ac.ravel(), minlength=max_r + 1)
    counts = np.bincount(np.minimum(rr.astype(int), max_r).ravel(), minlength=max_r + 1)
    radial = sums / np.maximum(counts, 1)
    radial = np.convolve(radial, np.ones(3) / 3.0, mode="same")

    # The origin's broad peak typically ends by 4 px.  The first meaningful
    # rise after that is the nearest-neighbour lattice vector.
    candidates = [
        r for r in range(5, max_r - 1)
        if radial[r] > radial[r - 1] and radial[r] >= radial[r + 1]
    ]
    if not candidates:
        return 12.0
    floor = float(np.median(radial[max(5, max_r // 3) : max_r]))
    strong = [r for r in candidates if radial[r] > floor + 0.025]
    return float((strong or candidates)[0])


def shifted_maximum(image: np.ndarray, radius: int) -> np.ndarray:
    """Maximum filter implemented as shifted NumPy views."""
    padded = np.pad(image, radius, mode="edge")
    result = np.full_like(image, -np.inf)
    h, w = image.shape
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            np.maximum(result, padded[dy : dy + h, dx : dx + w], out=result)
    return result


def quadratic_center(
    image: np.ndarray, y: int, x: int, radius: int = 2
) -> tuple[float, float, float, float] | None:
    """Return (x, y, residual_rms, position_uncertainty_px)."""
    if y < radius or x < radius or y + radius >= image.shape[0] or x + radius >= image.shape[1]:
        return None
    patch = image[y - radius : y + radius + 1, x - radius : x + radius + 1]
    gy, gx = np.mgrid[-radius : radius + 1, -radius : radius + 1]
    design = np.column_stack(
        [np.ones(patch.size), gx.ravel(), gy.ravel(), gx.ravel() ** 2,
         gx.ravel() * gy.ravel(), gy.ravel() ** 2]
    )
    coef, *_ = np.linalg.lstsq(design, patch.ravel(), rcond=None)
    _, bx, by, qxx, qxy, qyy = coef
    hessian = np.array([[2 * qxx, qxy], [qxy, 2 * qyy]])
    if np.any(np.linalg.eigvalsh(hessian) >= -1e-10):
        return None
    try:
        offset = -np.linalg.solve(hessian, np.array([bx, by]))
    except np.linalg.LinAlgError:
        return None
    if np.any(np.abs(offset) > 1.35):
        return None
    residual = patch.ravel() - design @ coef
    residual_rms = float(np.sqrt(np.mean(residual**2)))

    # Propagate the least-squares coefficient covariance through the vertex
    # calculation.  This is a local statistical precision estimate, not an
    # absolute calibration of scan distortion or specimen drift.
    dof = max(1, patch.size - design.shape[1])
    coef_cov = (float(residual @ residual) / dof) * np.linalg.pinv(design.T @ design)
    jacobian = np.zeros((2, len(coef)))
    for k in range(len(coef)):
        step = max(1e-8, abs(float(coef[k])) * 1e-5)
        shifted = coef.copy()
        shifted[k] += step
        _, sbx, sby, sqxx, sqxy, sqyy = shifted
        shifted_hessian = np.array([[2 * sqxx, sqxy], [sqxy, 2 * sqyy]])
        try:
            shifted_offset = -np.linalg.solve(shifted_hessian, np.array([sbx, sby]))
        except np.linalg.LinAlgError:
            shifted_offset = offset
        jacobian[:, k] = (shifted_offset - offset) / step
    position_cov = jacobian @ coef_cov @ jacobian.T
    uncertainty = float(math.sqrt(max(0.0, np.trace(position_cov) / 2.0)))
    return x + float(offset[0]), y + float(offset[1]), residual_rms, uncertainty


def sample_bilinear(image: np.ndarray, x: float, y: float) -> float:
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    x1, y1 = min(x0 + 1, image.shape[1] - 1), min(y0 + 1, image.shape[0] - 1)
    dx, dy = x - x0, y - y0
    return float(
        image[y0, x0] * (1 - dx) * (1 - dy)
        + image[y0, x1] * dx * (1 - dy)
        + image[y1, x0] * (1 - dx) * dy
        + image[y1, x1] * dx * dy
    )


def measure_peak(image: np.ndarray, x: float, y: float, radius: int) -> dict[str, float]:
    x0, y0 = int(round(x)), int(round(y))
    r = max(3, radius)
    ya, yb = max(0, y0 - r), min(image.shape[0], y0 + r + 1)
    xa, xb = max(0, x0 - r), min(image.shape[1], x0 + r + 1)
    patch = image[ya:yb, xa:xb]
    border = np.concatenate([patch[0], patch[-1], patch[1:-1, 0], patch[1:-1, -1]])
    background = float(np.median(border))
    weights = np.maximum(patch - background, 0.0)
    yy, xx = np.mgrid[ya:yb, xa:xb]
    total = float(weights.sum())
    if total <= np.finfo(float).eps:
        return {"peak": sample_bilinear(image, x, y), "integrated": 0.0,
                "sigma_major": 0.0, "sigma_minor": 0.0, "angle_deg": 0.0,
                "background": background}
    dx, dy = xx - x, yy - y
    covariance = np.array([
        [np.sum(weights * dx * dx), np.sum(weights * dx * dy)],
        [np.sum(weights * dx * dy), np.sum(weights * dy * dy)],
    ]) / total
    values, vectors = np.linalg.eigh(covariance)
    values = np.maximum(values, 0.0)
    major = vectors[:, 1]
    return {
        "peak": sample_bilinear(image, x, y),
        "integrated": total,
        "sigma_major": float(math.sqrt(values[1])),
        "sigma_minor": float(math.sqrt(values[0])),
        "angle_deg": float(math.degrees(math.atan2(major[1], major[0]))),
        "background": background,
    }


def one_dimensional_kmeans(values: np.ndarray, classes: int = 3) -> tuple[np.ndarray, np.ndarray]:
    classes = max(1, min(classes, len(values)))
    centers = np.quantile(values, np.linspace(0.15, 0.85, classes))
    labels = np.zeros(len(values), dtype=int)
    for _ in range(100):
        new_labels = np.argmin(np.abs(values[:, None] - centers[None, :]), axis=1)
        new_centers = np.array([
            values[new_labels == k].mean() if np.any(new_labels == k) else centers[k]
            for k in range(classes)
        ])
        if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers):
            break
        labels, centers = new_labels, new_centers
    order = np.argsort(centers)
    remap = np.empty_like(order)
    remap[order] = np.arange(classes)
    return remap[labels], centers[order]


def detect_columns(image: np.ndarray, spacing: float, threshold_sigma: float) -> tuple[list[dict], np.ndarray]:
    feature_sigma = max(0.7, spacing * 0.075)
    background_sigma = max(3.0, spacing * 0.48)
    bandpass = gaussian_blur_fft(image, feature_sigma) - gaussian_blur_fft(image, background_sigma)
    median = float(np.median(bandpass))
    mad = float(np.median(np.abs(bandpass - median))) * 1.4826
    threshold = median + threshold_sigma * max(mad, np.finfo(float).eps)
    nms_radius = max(2, int(round(spacing * 0.28)))
    maxima = shifted_maximum(bandpass, nms_radius)
    ys, xs = np.nonzero((bandpass >= maxima - 1e-12) & (bandpass > threshold))
    order = np.argsort(bandpass[ys, xs])[::-1]

    accepted: list[dict] = []
    minimum_separation2 = (spacing * 0.42) ** 2
    for idx in order:
        x0, y0 = int(xs[idx]), int(ys[idx])
        fit = quadratic_center(bandpass, y0, x0)
        if fit is None:
            continue
        x, y, fit_rms, uncertainty = fit
        if any((x - p["x_px"]) ** 2 + (y - p["y_px"]) ** 2 < minimum_separation2 for p in accepted):
            continue
        measurement = measure_peak(image, x, y, max(3, int(round(spacing * 0.22))))
        accepted.append({
            "x_px": x, "y_px": y, "response": float(bandpass[y0, x0]),
            "fit_residual_rms": fit_rms,
            "localization_uncertainty_px": uncertainty,
            **measurement,
        })

    accepted.sort(key=lambda p: (p["y_px"], p["x_px"]))
    if accepted:
        integrated = np.array([p["integrated"] for p in accepted])
        labels, centers = one_dimensional_kmeans(np.log1p(integrated), classes=3)
        for peak, label in zip(accepted, labels):
            peak["intensity_class"] = int(label)
        for peak in accepted:
            peak["class_center_log_integrated"] = float(centers[peak["intensity_class"]])
    return accepted, bandpass


def synthesize(shape: tuple[int, int], peaks: list[dict], residual: np.ndarray, seed: int) -> np.ndarray:
    """Build a statistically matched realization at the measured coordinates."""
    rng = np.random.default_rng(seed)
    yy, xx = np.indices(shape)
    result = np.zeros(shape, dtype=np.float64)
    if not peaks:
        return result
    backgrounds = np.array([p["background"] for p in peaks])
    result.fill(float(np.median(backgrounds)))
    for p in peaks:
        # The fitted moments include a little neighboring signal; conservative
        # bounds keep the reconstruction from becoming artificially diffuse.
        sx = float(np.clip(p["sigma_minor"], 0.65, 2.8))
        sy = float(np.clip(p["sigma_major"], sx, 3.6))
        theta = math.radians(p["angle_deg"])
        ct, st = math.cos(theta), math.sin(theta)
        dx, dy = xx - p["x_px"], yy - p["y_px"]
        u, v = ct * dx + st * dy, -st * dx + ct * dy
        amplitude = max(p["peak"] - p["background"], 0.0)
        result += amplitude * np.exp(-0.5 * ((u / sy) ** 2 + (v / sx) ** 2))

    # Preserve the measured low-frequency background, then add a new noise
    # realization with the same residual power spectrum.  Geometry therefore
    # remains measured while the output is a genuinely new acquisition-like
    # realization rather than a copy of the source pixels.
    low = gaussian_blur_fft(residual, 10.0)
    high = residual - low
    randomized_phase = np.exp(1j * rng.uniform(-math.pi, math.pi, np.fft.rfft2(high).shape))
    noise = np.fft.irfft2(np.abs(np.fft.rfft2(high)) * randomized_phase, s=shape)
    if noise.std() > 0:
        noise *= high.std() / noise.std()
    return result + low + noise


def draw_overlay(image: np.ndarray, peaks: list[dict], output: Path) -> None:
    scaled, _, _ = robust_scale(image)
    rgb = np.repeat((scaled * 255).astype(np.uint8)[..., None], 3, axis=2)
    canvas = Image.fromarray(rgb)
    draw = ImageDraw.Draw(canvas)
    colors = [(74, 222, 128), (250, 204, 21), (248, 113, 113)]
    for i, p in enumerate(peaks):
        x, y = p["x_px"], p["y_px"]
        color = colors[p.get("intensity_class", 0) % len(colors)]
        draw.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), outline=color, width=1)
        if i % 25 == 0:
            draw.text((x + 3, y + 2), str(i), fill=color)
    canvas.save(output)


def save_preview(image: np.ndarray, output: Path) -> None:
    scaled, _, _ = robust_scale(image)
    Image.fromarray((scaled * 255).astype(np.uint8)).save(output)


def parse_crop(value: str | None, shape: tuple[int, int]) -> tuple[float, float, float, float]:
    if value is None:
        return 0.0, 0.0, float(shape[1]), float(shape[0])
    try:
        x0, y0, x1, y1 = (float(item) for item in value.split(","))
    except (TypeError, ValueError) as exc:
        raise ValueError("--game-crop must be x0,y0,x1,y1 in source pixels") from exc
    if not (0 <= x0 < x1 <= shape[1] and 0 <= y0 < y1 <= shape[0]):
        raise ValueError(f"game crop {(x0, y0, x1, y1)} falls outside image shape {shape}")
    return x0, y0, x1, y1


def write_outputs(source: Path, output_dir: Path, image: np.ndarray, peaks: list[dict],
                  bandpass: np.ndarray, spacing: float, seed: int,
                  game_crop: tuple[float, float, float, float], source_dtype: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "x_px", "y_px", "peak", "integrated", "background", "response",
        "fit_residual_rms", "localization_uncertainty_px", "sigma_major", "sigma_minor",
        "angle_deg", "intensity_class",
    ]
    with (output_dir / "atomic_columns.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for i, peak in enumerate(peaks):
            writer.writerow({key: i if key == "id" else peak[key] for key in fieldnames})

    peak_values = np.array([p["peak"] - p["background"] for p in peaks]) if peaks else np.array([1.0])
    p05, p995 = np.percentile(peak_values, (5, 99.5))
    packed = []
    for p in peaks:
        intensity = float(np.clip((p["peak"] - p["background"] - p05) / max(p995 - p05, 1e-12), 0, 1))
        packed.append(f'{p["x_px"] / spacing:.3f},{p["y_px"] / spacing:.3f},{p["intensity_class"]},{intensity:.3f}')
    (output_dir / "atomic_columns.js.txt").write_text("\n".join(packed) + "\n")

    x0, y0, x1, y1 = game_crop
    game_peaks = [p for p in peaks if x0 <= p["x_px"] < x1 and y0 <= p["y_px"] < y1]
    game_packed = []
    for p in game_peaks:
        intensity = float(np.clip((p["peak"] - p["background"] - p05) / max(p995 - p05, 1e-12), 0, 1))
        game_packed.append(
            f'{(p["x_px"] - x0) / spacing:.3f},{(p["y_px"] - y0) / spacing:.3f},'
            f'{p["intensity_class"]},{intensity:.3f}'
        )
    (output_dir / "game_columns.js.txt").write_text("\n".join(game_packed) + "\n")

    metadata = {
        # Keep generated metadata portable and avoid leaking a workstation's
        # absolute directory when analysis outputs are shared or committed.
        "source": source.name,
        "shape": list(image.shape),
        "source_dtype": source_dtype,
        "analysis_dtype": str(image.dtype),
        "estimated_nearest_neighbor_spacing_px": spacing,
        "column_count": len(peaks),
        "coordinate_convention": "origin at upper-left; x right; y down; subpixel pixel coordinates",
        "intensity_classes": "0=dim, 1=medium, 2=bright; unsupervised, not chemical labels",
        "game_crop_px": list(game_crop),
        "game_column_count": len(game_peaks),
        "seed_for_new_realization": seed,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    draw_overlay(image, peaks, output_dir / "coordinate_overlay.png")
    save_preview(bandpass, output_dir / "bandpass.png")

    model = synthesize(image.shape, peaks, np.zeros_like(image), seed)
    residual = image - model
    generated = synthesize(image.shape, peaks, residual, seed)
    generated = np.clip(generated, float(image.min()), float(image.max()))
    tifffile.imwrite(output_dir / "reconstructed_sample.tif", generated.astype(np.float32))
    save_preview(generated, output_dir / "reconstructed_sample.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="16-bit or floating-point reconstruction TIFF")
    parser.add_argument("--output-dir", type=Path, default=Path("output/atomic-columns"))
    parser.add_argument("--spacing", type=float, help="nearest-neighbour spacing in pixels; default: estimate")
    parser.add_argument("--threshold-sigma", type=float, default=3.2,
                        help="peak threshold in robust band-pass standard deviations (default: 3.2)")
    parser.add_argument("--seed", type=int, default=7751, help="noise-realization seed")
    parser.add_argument(
        "--game-crop", default=None,
        help="optional x0,y0,x1,y1 crop for game_columns.js.txt; full image by default",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = tifffile.imread(args.input)
    if raw.ndim != 2:
        raise ValueError(f"expected one 2D image, got shape {raw.shape}")
    image = np.asarray(raw, dtype=np.float64)
    normalized, _, _ = robust_scale(image)
    spacing = float(args.spacing or estimate_spacing(normalized))
    if not 4.0 <= spacing <= min(image.shape) / 3:
        raise ValueError(f"implausible spacing estimate {spacing:.2f} px; pass --spacing explicitly")
    peaks, bandpass = detect_columns(normalized, spacing, args.threshold_sigma)
    if len(peaks) < 10:
        raise RuntimeError(
            f"only {len(peaks)} columns detected; lower --threshold-sigma or pass --spacing"
        )
    game_crop = parse_crop(args.game_crop, image.shape)
    write_outputs(
        args.input, args.output_dir, normalized, peaks, bandpass, spacing, args.seed,
        game_crop, str(raw.dtype),
    )
    print(f"Detected {len(peaks)} columns at estimated spacing {spacing:.2f} px")
    print(f"Wrote coordinate table, QA overlay, and reconstructed sample to {args.output_dir}")


if __name__ == "__main__":
    main()
