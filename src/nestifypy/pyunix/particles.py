"""
nestifypy.pyunix.particles
--------------------------
High-performance particle system with a fluent builder API.

Supports position/velocity variance, color gradients, alpha fade,
size change over lifetime, gravity, burst and continuous emission.

Usage:
    # One-shot burst (explosion)
    fx = ParticleSystem(x=200, y=300)
    fx.configure(
        count=80,
        lifetime=(0.4, 1.2),
        speed=(60, 200),
        angle=(-180, 180),
        start_color=Color.from_hex("#FF6600"),
        end_color=Color(80, 0, 0, 0),
        start_size=6,
        end_size=0,
        gravity=Vector2(0, 120),
    )
    fx.burst()

    # Continuous emitter (fire, smoke)
    smoke = ParticleSystem(x=100, y=400)
    smoke.configure(
        emit_rate=30,
        lifetime=(1.0, 2.0),
        speed=(10, 40),
        angle=(-100, -80),   # upward with variance
        start_color=Color(180, 180, 180, 200),
        end_color=Color(80, 80, 80, 0),
        start_size=4,
        end_size=12,
    )
    smoke.start()

    # In update:
    fx.update(dt)
    smoke.update(dt)

    # In draw:
    fx.draw(screen, Camera.offset)
    smoke.draw(screen, Camera.offset)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from nestifypy.pyunix.math import Color, Vector2

try:
    import pygame
    _HAS_PYGAME = True
except ImportError:
    _HAS_PYGAME = False


@dataclass
class _Particle:
    __slots__ = (
        "x", "y", "vx", "vy",
        "lifetime", "age",
        "start_color", "end_color",
        "start_size", "end_size",
        "active",
    )
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float
    age: float
    start_color: Color
    end_color: Color
    start_size: float
    end_size: float
    active: bool


class ParticleSystem:
    """
    Manages a pool of particles with birth/death/update/draw logic.

    Configure once with .configure(), then call .burst() or .start()/.stop()
    for continuous emission.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

        # ── Config ─────────────────────────
        self._count:       int               = 50
        self._emit_rate:   float             = 0.0        # particles/sec (0 = burst only)
        self._lifetime:    Tuple[float, float] = (0.5, 1.5)
        self._speed:       Tuple[float, float] = (50.0, 150.0)
        self._angle:       Tuple[float, float] = (-180.0, 180.0)
        self._start_color: Color             = Color.WHITE
        self._end_color:   Color             = Color(255, 255, 255, 0)
        self._start_size:  float             = 4.0
        self._end_size:    float             = 0.0
        self._gravity:     Vector2           = Vector2.zero()
        self._spread:      Tuple[float, float] = (0.0, 0.0)   # x/y spawn offset variance

        # ── State ──────────────────────────
        self._pool:       List[_Particle] = []
        self._active:     bool = False
        self._emit_accum: float = 0.0

    # ── Fluent Configuration ─────────────────

    def configure(
        self,
        count: int = 50,
        emit_rate: float = 0.0,
        lifetime: Tuple[float, float] = (0.5, 1.5),
        speed: Tuple[float, float] = (50.0, 150.0),
        angle: Tuple[float, float] = (-180.0, 180.0),
        start_color: Color = None,
        end_color: Color = None,
        start_size: float = 4.0,
        end_size: float = 0.0,
        gravity: Vector2 = None,
        spread: Tuple[float, float] = (0.0, 0.0),
    ) -> "ParticleSystem":
        """
        Configure emission parameters. Returns self for chaining.

        Args:
            count:        Max simultaneous particles (burst uses this as total count).
            emit_rate:    Particles emitted per second (0 = burst only).
            lifetime:     (min, max) lifetime in seconds per particle.
            speed:        (min, max) initial speed in pixels/second.
            angle:        (min, max) emission angle in degrees (0 = right).
            start_color:  Color at birth.
            end_color:    Color at death (alpha fades too).
            start_size:   Radius in pixels at birth.
            end_size:     Radius in pixels at death.
            gravity:      Per-frame acceleration Vector2 (e.g. Vector2(0, 120) for down).
            spread:       (x_var, y_var) spawn position variance in pixels.
        """
        self._count       = count
        self._emit_rate   = emit_rate
        self._lifetime    = lifetime
        self._speed       = speed
        self._angle       = angle
        self._start_color = start_color or Color.WHITE
        self._end_color   = end_color   or Color(255, 255, 255, 0)
        self._start_size  = start_size
        self._end_size    = end_size
        self._gravity     = gravity or Vector2.zero()
        self._spread      = spread
        return self

    # ── Emission ─────────────────────────────

    def burst(self, count: Optional[int] = None) -> None:
        """
        Immediately spawn `count` particles (defaults to configured count).
        """
        n = count if count is not None else self._count
        for _ in range(n):
            self._spawn()

    def start(self) -> None:
        """Begin continuous emission (emit_rate particles per second)."""
        self._active = True

    def stop(self) -> None:
        """Stop continuous emission (existing particles finish naturally)."""
        self._active = False

    def clear(self) -> None:
        """Destroy all active particles immediately."""
        self._pool.clear()
        self._emit_accum = 0.0

    @property
    def alive_count(self) -> int:
        return sum(1 for p in self._pool if p.active)

    @property
    def is_finished(self) -> bool:
        """True when emission is stopped and no particles remain alive."""
        return not self._active and self.alive_count == 0

    # ── Lifecycle ────────────────────────────

    def update(self, dt: float) -> None:
        """Advance all particles by `dt` seconds. Call every frame."""
        gx, gy = self._gravity.x, self._gravity.y

        # Update alive particles
        for p in self._pool:
            if not p.active:
                continue
            p.age += dt
            if p.age >= p.lifetime:
                p.active = False
                continue
            p.vx += gx * dt
            p.vy += gy * dt
            p.x  += p.vx * dt
            p.y  += p.vy * dt

        # Prune dead particles (keep pool lean)
        self._pool = [p for p in self._pool if p.active]

        # Continuous emission
        if self._active and self._emit_rate > 0:
            self._emit_accum += self._emit_rate * dt
            while self._emit_accum >= 1.0:
                if len(self._pool) < self._count:
                    self._spawn()
                self._emit_accum -= 1.0

    def draw(self, surface: Any, offset: Tuple[float, float] = (0.0, 0.0)) -> None:
        """Render all particles as filled circles on `surface`."""
        if not _HAS_PYGAME:
            return

        ox, oy = offset
        for p in self._pool:
            if not p.active:
                continue
            t = p.age / max(p.lifetime, 0.0001)
            color = p.start_color.lerp(p.end_color, t)
            size  = max(1, int(p.start_size + (p.end_size - p.start_size) * t))
            cx = int(p.x - ox)
            cy = int(p.y - oy)

            # Use alpha surface for semi-transparent circles
            if color.a < 255:
                circle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(circle_surf, color.to_rgba(), (size, size), size)
                surface.blit(circle_surf, (cx - size, cy - size))
            else:
                pygame.draw.circle(surface, color.to_rgb(), (cx, cy), size)

    # ── Internal ─────────────────────────────

    def _spawn(self) -> None:
        ang = math.radians(random.uniform(*self._angle))
        spd = random.uniform(*self._speed)
        sx  = self.x + random.uniform(-self._spread[0], self._spread[0])
        sy  = self.y + random.uniform(-self._spread[1], self._spread[1])
        lt  = random.uniform(*self._lifetime)
        self._pool.append(_Particle(
            x=sx, y=sy,
            vx=math.cos(ang) * spd,
            vy=math.sin(ang) * spd,
            lifetime=lt, age=0.0,
            start_color=self._start_color,
            end_color=self._end_color,
            start_size=self._start_size,
            end_size=self._end_size,
            active=True,
        ))
