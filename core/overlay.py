"""
Visual Overlay - Advanced sci-fi molecular sphere for voice assistant.
Features: Soft glow particles, smooth animations.
"""

import tkinter as tk
import math
import colorsys
import threading
import queue
import time


# --- Constants ---
WINDOW_W, WINDOW_H = 600, 700
SPHERE_CENTER_X, SPHERE_CENTER_Y = 300, 250
NUM_PARTICLES = 120
BASE_RADIUS = 140
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))
FOV = 600
LINK_DISTANCE = 45
ROTATION_SPEED = 0.3       # radians/sec (slower, more elegant)
TILT_SPEED = 0.2
HUE_SPEED = 5              # degrees/sec (slower color shift)
WAVEFORM_Y = 450
WAVEFORM_LINES = 4         # 4 pink lines
WAVEFORM_WIDTH = 300       # Width of waveform area
DIALOG_Y = 520
DIALOG_W = 480
DIALOG_H = 90
DIALOG_PAD = 16
FADE_IN_MS = 400
AUTO_HIDE_SEC = 10

# Sci-fi color palette (soft cyan/purple)
CORE_HUE = 190    # Soft cyan
GLOW_HUE = 270    # Purple


def _hsl_to_hex(h, s, l):
    """HSL (h: 0-360, s: 0-1, l: 0-1) to #rrggbb."""
    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def _soft_glow_color(hue, intensity):
    """Generate a soft glow color with reduced harshness."""
    # Lower saturation, higher lightness for softness
    return _hsl_to_hex(hue, 0.5 + intensity * 0.3, 0.4 + intensity * 0.3)


class Particle:
    __slots__ = ('theta', 'phi', 'wobble_phase', 'wobble_speed',
                 'wobble_amount', 'screen_x', 'screen_y', 'screen_z',
                 'screen_size', 'depth', 'glow_phase')

    def __init__(self, theta, phi, index):
        self.theta = theta
        self.phi = phi
        self.wobble_phase = theta * 2.5
        self.wobble_speed = 0.5 + (phi % 1.0) * 0.4
        self.wobble_amount = 2.0 + (theta % 1.0) * 2.5
        self.screen_x = 0
        self.screen_y = 0
        self.screen_z = 0
        self.screen_size = 2.5
        self.depth = 0
        self.glow_phase = index * 0.1  # Individual glow timing


class AssistantOverlay:
    """Advanced sci-fi overlay with soft glow particles."""

    def __init__(self):
        self._root = None
        self._canvas = None
        self._particles = []
        self._state = 'hidden'       # hidden, idle, speaking, listening, user_said
        self._target_state = 'hidden'
        self._rotation_y = 0.0
        self._rotation_x = 0.3
        self._hue_offset = 0.0
        self._amplitude = 0.0        # current RMS amplitude (0-1)
        self._smooth_amp = 0.0       # smoothed amplitude
        self._dialog_text = ''
        self._user_text = ''
        self._sphere_radius = BASE_RADIUS
        self._target_radius = BASE_RADIUS
        self._fade_alpha = 0.0       # 0-1, for fade in/out
        self._last_interaction = 0
        self._amp_queue = queue.Queue(maxsize=30)
        self._state_lock = threading.Lock()
        self._running = False
        self._links = []             # precomputed link pairs
        self._thread = None
        self._time = 0

    def start(self):
        """Start the overlay in a separate thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """Tkinter main loop (runs in its own thread)."""
        self._root = tk.Tk()
        self._root.withdraw()  # start hidden

        # Transparent color key
        self._trans_color = '#010101'
        self._root.overrideredirect(True)
        self._root.attributes('-topmost', True)
        self._root.attributes('-transparentcolor', self._trans_color)
        self._root.configure(bg=self._trans_color)

        # Position: center of screen
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        x = (sw - WINDOW_W) // 2
        y = (sh - WINDOW_H) // 2 - 50
        self._root.geometry(f'{WINDOW_W}x{WINDOW_H}+{x}+{y}')

        # Canvas
        self._canvas = tk.Canvas(
            self._root, width=WINDOW_W, height=WINDOW_H,
            bg=self._trans_color, highlightthickness=0
        )
        self._canvas.pack()

        # Precompute particles
        self._init_particles()
        self._precompute_links()

        # Start animation loop
        self._last_time = time.time()
        self._animate()

        self._root.mainloop()

    def _init_particles(self):
        """Create particles distributed on a sphere using golden angle."""
        self._particles = []
        for i in range(NUM_PARTICLES):
            theta = GOLDEN_ANGLE * i
            phi = math.acos(1 - 2 * (i + 0.5) / NUM_PARTICLES)
            self._particles.append(Particle(theta, phi, i))

    def _precompute_links(self):
        """Precompute which particle pairs should be linked."""
        self._links = []
        for i in range(NUM_PARTICLES):
            for j in range(i + 1, NUM_PARTICLES):
                p1, p2 = self._particles[i], self._particles[j]
                dx = math.cos(p1.theta) * math.sin(p1.phi) - math.cos(p2.theta) * math.sin(p2.phi)
                dy = math.sin(p1.theta) * math.sin(p1.phi) - math.sin(p2.theta) * math.sin(p2.phi)
                dz = math.cos(p1.phi) - math.cos(p2.phi)
                dist_3d = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist_3d < 0.5:
                    self._links.append((i, j))

    def _animate(self):
        """Main animation loop at ~30fps."""
        if not self._running:
            return

        now = time.time()
        dt = min(now - self._last_time, 0.05)
        self._last_time = now
        self._time += dt

        # Drain amplitude queue
        while not self._amp_queue.empty():
            try:
                self._amplitude = self._amp_queue.get_nowait()
            except queue.Empty:
                break

        # Smooth amplitude with easing
        target_amp = self._amplitude
        self._smooth_amp += (target_amp - self._smooth_amp) * min(1.0, dt * 10)

        # Update state
        with self._state_lock:
            state = self._state

        # Auto-hide after inactivity
        if state in ('idle', 'listening', 'speaking', 'user_said') and self._last_interaction > 0:
            if now - self._last_interaction > AUTO_HIDE_SEC:
                self._set_state('hidden')
                state = 'hidden'

        # Fade
        if state == 'hidden':
            self._fade_alpha = max(0, self._fade_alpha - dt * 2.5)
        else:
            self._fade_alpha = min(1, self._fade_alpha + dt * 3)

        if self._fade_alpha <= 0.01:
            self._root.withdraw()
            self._root.after(33, self._animate)
            return
        else:
            try:
                self._root.deiconify()
            except Exception:
                pass

        # Update sphere
        if state == 'listening':
            self._target_radius = BASE_RADIUS + self._smooth_amp * 35
        else:
            self._target_radius = BASE_RADIUS

        self._sphere_radius += (self._target_radius - self._sphere_radius) * min(1, dt * 5)
        self._rotation_y += ROTATION_SPEED * dt
        self._hue_offset += HUE_SPEED * dt
        if self._hue_offset > 360:
            self._hue_offset -= 360

        # Draw
        self._canvas.delete('all')

        if state != 'hidden':
            self._draw_sphere_glow()
            self._update_particles()
            self._draw_links()
            self._draw_particles()

            # Show waveform when listening or speaking
            if state in ('listening', 'speaking'):
                self._draw_waveform_lines()

            if state == 'speaking':
                self._draw_dialog(self._dialog_text, is_user=False)
            elif state == 'user_said':
                self._draw_dialog(self._user_text, is_user=True)

        self._root.after(33, self._animate)  # ~30fps

    def _update_particles(self):
        """Update particle 3D positions and project to 2D."""
        tilt_x = self._rotation_x + math.sin(self._time * TILT_SPEED) * 0.12

        for p in self._particles:
            # Wobble
            wobble = math.sin(self._time * p.wobble_speed + p.wobble_phase) * p.wobble_amount
            r = self._sphere_radius + wobble

            # Spherical to Cartesian
            x = r * math.cos(p.theta) * math.sin(p.phi)
            y = r * math.sin(p.theta) * math.sin(p.phi)
            z = r * math.cos(p.phi)

            # Rotate Y
            cos_y = math.cos(self._rotation_y)
            sin_y = math.sin(self._rotation_y)
            x2 = x * cos_y - z * sin_y
            z2 = x * sin_y + z * cos_y

            # Rotate X
            cos_x = math.cos(tilt_x)
            sin_x = math.sin(tilt_x)
            y2 = y * cos_x - z2 * sin_x
            z3 = y * sin_x + z2 * cos_x

            # Project
            scale = FOV / (FOV + z3 + 250)
            p.screen_x = SPHERE_CENTER_X + x2 * scale
            p.screen_y = SPHERE_CENTER_Y + y2 * scale - 20  # Shift up slightly
            p.screen_z = z3
            p.screen_size = max(2.0, 3.5 * scale)
            p.depth = z3

        # Sort by depth (far first)
        self._particles.sort(key=lambda p: p.depth)

    def _draw_particles(self):
        """Draw particles with soft glow effect."""
        for p in self._particles:
            x, y = p.screen_x, p.screen_y
            sz = p.screen_size * (0.85 + self._smooth_amp * 0.4)

            # Depth-based brightness (softer range)
            depth_factor = 0.5 + 0.5 * (p.depth + self._sphere_radius) / (2 * self._sphere_radius)

            # Soft cyan/purple hue based on position
            base_hue = CORE_HUE + math.sin(p.theta * 0.5) * 30
            hue = (base_hue + self._hue_offset * 0.3) % 360

            # Individual glow pulsing
            glow_pulse = 0.7 + 0.3 * math.sin(self._time * 1.5 + p.glow_phase)

            # Soft glow colors (low saturation, medium lightness)
            core_color = _hsl_to_hex(hue, 0.6 * depth_factor, 0.65 * glow_pulse)
            glow_color = _hsl_to_hex(hue, 0.4 * depth_factor, 0.35 * glow_pulse)
            outer_glow = _hsl_to_hex(hue, 0.3, 0.15 * depth_factor)

            # Outer soft glow (large, very dim)
            glow_r = sz * 4
            self._canvas.create_oval(
                x - glow_r, y - glow_r, x + glow_r, y + glow_r,
                fill='', outline=outer_glow, width=2
            )

            # Mid glow
            mid_r = sz * 2.2
            self._canvas.create_oval(
                x - mid_r, y - mid_r, x + mid_r, y + mid_r,
                fill='', outline=glow_color, width=1
            )

            # Core (soft, not harsh white)
            self._canvas.create_oval(
                x - sz, y - sz, x + sz, y + sz,
                fill=core_color, outline=''
            )

            # Soft center highlight (not pure white)
            hs = sz * 0.4
            highlight = _hsl_to_hex(hue, 0.3, 0.8)
            self._canvas.create_oval(
                x - hs, y - hs, x + hs, y + hs,
                fill=highlight, outline=''
            )

    def _draw_links(self):
        """Draw soft glowing lines between nearby particles."""
        for i, j in self._links:
            p1 = self._particles[i] if i < len(self._particles) else None
            p2 = self._particles[j] if j < len(self._particles) else None
            if not p1 or not p2:
                continue

            if p1.depth < -30 or p2.depth < -30:
                continue

            dx = p1.screen_x - p2.screen_x
            dy = p1.screen_y - p2.screen_y
            dist = math.sqrt(dx*dx + dy*dy)

            max_dist = LINK_DISTANCE * (self._sphere_radius / BASE_RADIUS) * 1.2
            if dist < max_dist:
                alpha = (1 - dist / max_dist) * 0.15 * self._fade_alpha
                if alpha > 0.01:
                    hue = (CORE_HUE + 60 + self._hue_offset * 0.2) % 360
                    lightness = 0.3 + 0.2 * alpha
                    color = _hsl_to_hex(hue, 0.4, lightness)
                    self._canvas.create_line(
                        p1.screen_x, p1.screen_y,
                        p2.screen_x, p2.screen_y,
                        fill=color, width=1
                    )

    def _draw_sphere_glow(self):
        """Draw soft ambient glow around the sphere (no hard circle)."""
        cx, cy = SPHERE_CENTER_X, SPHERE_CENTER_Y - 20
        r = self._sphere_radius

        # Soft radial glow only (no circle outline)
        for i in range(3):
            glow_r = r * (1.3 + i * 0.4)
            alpha = 0.08 - i * 0.02
            hue = (CORE_HUE + i * 20 + self._hue_offset * 0.2) % 360
            color = _hsl_to_hex(hue, 0.3, alpha)
            self._canvas.create_oval(
                cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r,
                fill='', outline=color, width=2
            )

    def _draw_waveform_lines(self):
        """Draw 4 pink lines that are straight when silent, wavey when sound."""
        cx = WINDOW_W // 2
        amp = self._smooth_amp

        # 4 parallel pink lines
        line_configs = [
            {'offset_y': 0, 'phase': 0, 'hue': 330, 'alpha': 0.7},
            {'offset_y': 6, 'phase': 0.5, 'hue': 340, 'alpha': 0.55},
            {'offset_y': 12, 'phase': 1.0, 'hue': 320, 'alpha': 0.4},
            {'offset_y': 18, 'phase': 1.5, 'hue': 350, 'alpha': 0.3},
        ]

        points = 50

        for cfg in line_configs:
            base_y = WAVEFORM_Y + cfg['offset_y']
            coords = []

            for i in range(points):
                x = cx - WAVEFORM_WIDTH // 2 + (i / points) * WAVEFORM_WIDTH

                # Only wave when amplitude > threshold
                if amp > 0.02:
                    t = self._time * 3 + cfg['phase']
                    pos = i / points
                    wave = math.sin(pos * math.pi * 4 + t) * amp * 35
                else:
                    wave = 0  # Straight line when silent

                y = base_y + wave
                coords.extend([x, y])

            if len(coords) >= 4:
                color = _hsl_to_hex(cfg['hue'], 0.55, 0.5)
                self._canvas.create_line(coords, fill=color, width=2, smooth=True)

                # Soft glow
                glow_color = _hsl_to_hex(cfg['hue'], 0.35, 0.25)
                self._canvas.create_line(coords, fill=glow_color, width=4, smooth=True)

    def _draw_dialog(self, text, is_user=False):
        """Draw dialog box with soft sci-fi styling."""
        if not text:
            return

        cx = WINDOW_W // 2
        x1 = cx - DIALOG_W // 2
        y1 = DIALOG_Y
        x2 = cx + DIALOG_W // 2
        y2 = DIALOG_Y + DIALOG_H

        # Background with slight transparency effect
        bg_color = '#0d1525' if not is_user else '#15200d'
        border_hue = (CORE_HUE + 40) % 360 if not is_user else 120
        border_color = _hsl_to_hex(border_hue, 0.5, 0.35)

        # Rounded rectangle
        r = 14
        self._canvas.create_polygon(
            x1+r, y1, x2-r, y1, x2, y1+r, x2, y2-r,
            x2-r, y2, x1+r, y2, x1, y2-r, x1, y1+r,
            fill=bg_color, outline=border_color, width=1
        )

        # Inner glow line
        inner_color = _hsl_to_hex(border_hue, 0.3, 0.2)
        self._canvas.create_polygon(
            x1+r+2, y1+2, x2-r-2, y1+2, x2-2, y1+r+2, x2-2, y2-r-2,
            x2-r-2, y2-2, x1+r+2, y2-2, x1+2, y2-r-2, x1+2, y1+r+2,
            fill='', outline=inner_color, width=1
        )

        # Text
        display = text[:120] + ('...' if len(text) > 120 else '')
        text_color = '#d0e0f0' if not is_user else '#d0f0d0'
        self._canvas.create_text(
            cx, y1 + DIALOG_H // 2,
            text=display, fill=text_color,
            font=('Microsoft YaHei', 11),
            width=DIALOG_W - DIALOG_PAD * 2,
            justify='center'
        )

        # Label
        label = 'SANS' if not is_user else 'YOU'
        label_color = _hsl_to_hex(border_hue, 0.7, 0.6)
        self._canvas.create_text(
            x1 + DIALOG_PAD + 8, y1 + 10,
            text=label, fill=label_color,
            font=('Consolas', 9, 'bold'),
            anchor='nw'
        )

    def _set_state(self, state):
        """Thread-safe state change."""
        with self._state_lock:
            self._state = state
        self._last_interaction = time.time()

    # --- Public API ---

    def update_amplitude(self, rms):
        """Called from STT thread with audio RMS level (0-1)."""
        try:
            self._amp_queue.put_nowait(rms)
        except queue.Full:
            try:
                self._amp_queue.get_nowait()
                self._amp_queue.put_nowait(rms)
            except queue.Empty:
                pass

    def show_sphere(self):
        """Show idle sphere (after wake word)."""
        self._set_state('idle')
        self._last_interaction = time.time()

    def show_speaking(self, text):
        """Show sphere + dialog with Sans's response."""
        self._dialog_text = text
        self._set_state('speaking')
        self._last_interaction = time.time()

    def show_listening(self):
        """Show sphere (user is speaking)."""
        self._set_state('listening')

    def show_user_text(self, text):
        """Show sphere + dialog with user's speech."""
        self._user_text = text
        self._set_state('user_said')
        self._last_interaction = time.time()

    def hide(self):
        """Hide the overlay."""
        self._set_state('hidden')

    def stop(self):
        """Stop the overlay."""
        self._running = False
        if self._root:
            try:
                self._root.quit()
            except Exception:
                pass
