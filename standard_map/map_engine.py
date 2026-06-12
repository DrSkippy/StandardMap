import numpy as np

TWO_PI = 2.0 * np.pi


class MapEngine:
    def __init__(
        self,
        K: float = 0.97,
        seed_mode: str = "grid",
        nx_seeds: int = 20,
        ny_seeds: int = 20,
    ) -> None:
        self._K = K
        self._seed_mode = seed_mode
        self._nx = nx_seeds
        self._ny = ny_seeds
        self._x = np.zeros(nx_seeds * ny_seeds)
        self._y = np.zeros(nx_seeds * ny_seeds)

    def reseed(self, x_range: tuple, y_range: tuple) -> None:
        if self._seed_mode == "grid":
            self._x, self._y = self._seed_grid(x_range, y_range)
        elif self._seed_mode == "quasi_random":
            self._x, self._y = self._seed_quasi_random(x_range, y_range)
        elif self._seed_mode == "legacy":
            self._x, self._y = self._seed_legacy(x_range, y_range)

    def _seed_grid(self, x_range, y_range):
        xs = np.linspace(x_range[0], x_range[1], self._nx, endpoint=False)
        ys = np.linspace(y_range[0], y_range[1], self._ny, endpoint=False)
        xg, yg = np.meshgrid(xs, ys)
        return xg.ravel().copy(), yg.ravel().copy()

    def _seed_quasi_random(self, x_range, y_range):
        from scipy.stats.qmc import Halton
        sampler = Halton(d=2, scramble=True)
        pts = sampler.random(self._nx * self._ny)
        x = pts[:, 0] * (x_range[1] - x_range[0]) + x_range[0]
        y = pts[:, 1] * (y_range[1] - y_range[0]) + y_range[0]
        return x.copy(), y.copy()

    def _seed_legacy(self, x_range, y_range):
        # Replicates original Processing: fixed x at midpoint, linear y sweep
        N = 85
        x_mid = (x_range[0] + x_range[1]) / 2.0
        x = np.full(N, x_mid)
        y = x_range[0] + np.arange(1, N + 1) * (y_range[1] - y_range[0]) / float(N + 1)
        return x.copy(), y.copy()

    def step(self, n_iter: int = 40) -> tuple:
        """
        Advance all trajectories n_iter steps.
        Returns (xs, ys) each of shape (n_iter, N) — positions BEFORE each update,
        matching the original's draw-then-advance order.
        """
        N = self._x.size
        xs_out = np.empty((n_iter, N))
        ys_out = np.empty((n_iter, N))
        for i in range(n_iter):
            xs_out[i] = self._x
            ys_out[i] = self._y
            y_new = (self._y + self._K * np.sin(self._x)) % TWO_PI
            y_new[y_new >= TWO_PI] = 0.0          # guard rare fp edge-case
            x_new = (self._x + y_new) % TWO_PI
            x_new[x_new >= TWO_PI] = 0.0
            self._x = x_new
            self._y = y_new
        return xs_out, ys_out

    @property
    def x(self) -> np.ndarray:
        return self._x

    @property
    def y(self) -> np.ndarray:
        return self._y

    @property
    def n_trajectories(self) -> int:
        return self._x.size

    @property
    def K(self) -> float:
        return self._K

    @K.setter
    def K(self, value: float) -> None:
        self._K = value
