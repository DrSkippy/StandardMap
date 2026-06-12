import numpy as np

TWO_PI = 2.0 * np.pi


class CoordTransform:
    DIM = 1600

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._data_x1 = 0.0
        self._data_x2 = TWO_PI
        self._data_y1 = 0.0
        self._data_y2 = TWO_PI
        self._scalex = self.DIM / TWO_PI
        self._scaley = self.DIM / TWO_PI
        self._xoff = 0
        self._yoff = 0

    @property
    def data_bounds(self) -> tuple:
        return (self._data_x1, self._data_x2, self._data_y1, self._data_y2)

    def data_to_pixel(self, xd: np.ndarray, yd: np.ndarray) -> tuple:
        """Vectorized data→pixel. Returns (px_col, px_row) as int32 arrays."""
        px_col = (xd * self._scalex + self._xoff).astype(np.int32)
        px_row = (yd * self._scaley + self._yoff).astype(np.int32)
        return px_col, px_row

    def pixel_to_data(self, px: int, py: int) -> tuple:
        xd = (px - self._xoff) / self._scalex
        yd = (py - self._yoff) / self._scaley
        return xd, yd

    def zoom_to_pixel_rect(self, px1: int, py1: int, px2: int, py2: int) -> None:
        """
        Direct translation of Processing's setScale(). Caller must normalize
        corners so px1 < px2 and py1 < py2 before calling.
        """
        new_dx1 = (px1 - self._xoff) / self._scalex
        new_dx2 = (px2 - self._xoff) / self._scalex
        new_dy1 = (py1 - self._yoff) / self._scaley
        new_dy2 = (py2 - self._yoff) / self._scaley

        self._scalex = self.DIM / abs(new_dx2 - new_dx1)
        self._scaley = self.DIM / abs(new_dy2 - new_dy1)

        self._xoff = int((-(new_dx1 + new_dx2) * self._scalex + self.DIM) / 2)
        self._yoff = int((-(new_dy1 + new_dy2) * self._scaley + self.DIM) / 2)

        self._data_x1, self._data_x2 = new_dx1, new_dx2
        self._data_y1, self._data_y2 = new_dy1, new_dy2
