"""Project trajectory batches into window pixels and clip to the window."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .viewport import CoordTransform, FloatArray, IntArray


@dataclass(frozen=True)
class ProjectedPoints:
    """Visible points of a batch, flattened in iteration-major order.

    Attributes:
        cols: Pixel column of each visible point.
        rows: Pixel row of each visible point.
        trajectory_index: Which trajectory each point belongs to, so callers
            can look up per-trajectory colors with ``colors[trajectory_index]``.
    """

    cols: IntArray
    rows: IntArray
    trajectory_index: npt.NDArray[np.intp]


def project_and_clip(xs: FloatArray, ys: FloatArray, transform: CoordTransform) -> ProjectedPoints:
    """Convert a ``(n_iter, N)`` batch to pixels, keeping only on-screen points.

    Args:
        xs: Data x-coordinates, shape ``(n_iter, N)``.
        ys: Data y-coordinates, shape ``(n_iter, N)``.
        transform: The current data -> pixel transform.

    Returns:
        The visible points with their trajectory indices.
    """
    n_iter, n_traj = xs.shape
    dim = transform.dim
    px_col, px_row = transform.data_to_pixel(xs, ys)
    visible = (px_col >= 0) & (px_col < dim) & (px_row >= 0) & (px_row < dim)
    # each trajectory keeps its color across all iterations: index by column
    trajectory_index = np.broadcast_to(np.arange(n_traj), (n_iter, n_traj))
    return ProjectedPoints(px_col[visible], px_row[visible], trajectory_index[visible])
