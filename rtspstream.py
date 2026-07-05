import subprocess
import threading
import time
from typing import Optional
import pygame
import imageio_ffmpeg
import numpy as np

RTSP_CREDENTIALS = "admin:Admin1234"
CAM_SUBTYPE = 1

WIDTH, HEIGHT = 640, 480
FRAME_SIZE = WIDTH * HEIGHT * 3  # 3 bytes per pixel (RGB)
FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


class CameraStream:
    def __init__(self, cam_ip: str, localport: int):
        self.latest_frame = None
        self.running = True

        self.rtsp_url = f"rtsp://{RTSP_CREDENTIALS}@127.0.0.1:{localport}/cam/realmonitor?channel=1&subtype={CAM_SUBTYPE}"

        self.tunnel = subprocess.Popen(
            [
                "ssh",
                "-N",
                "-L",
                f"{localport}:{cam_ip}:554",
                "raspberry-drone@100.117.181.95",
            ]
        )
        time.sleep(1)

        # FFmpeg flags specifically optimized to eliminate network & decoding lag
        self.command = [
            FFMPEG_BIN,
            "-rtsp_transport",
            "tcp",  # Drop UDP to avoid packet corruption artifacts
            "-fflags",
            "nobuffer",  # Disable internal stream buffering
            "-flags",
            "low_delay",  # Force low delay optimizations
            "-strict",
            "experimental",
            "-i",
            self.rtsp_url,
            "-f",
            "image2pipe",  # Output raw image data stream
            "-pix_fmt",
            "rgb24",  # Raw RGB24 matches Pygame surface natively
            "-vcodec",
            "rawvideo",
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-",  # Output to stdout
        ]

        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._grab, daemon=True)
        self.thread.start()

    def _grab(self):
        while self.running:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Suppress logs to maximize performance
                bufsize=FRAME_SIZE,
            )

            while self.running:
                # Read exactly one raw frame directly out of the memory pipe
                raw_frame = process.stdout.read(FRAME_SIZE)
                if len(raw_frame) != FRAME_SIZE:
                    break  # Reconnect if stream breaks
                self.latest_frame = raw_frame

            process.terminate()
            time.sleep(1)  # Wait before reconnecting

    def read(self) -> Optional[np.ndarray]:
        with self.lock:
            raw = self.latest_frame
        if raw is None:
            return None
        return np.frombuffer(raw, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))

    def stop(self):
        if self.tunnel is not None:
            self.tunnel.terminate()
        if self.thread.is_alive():
            self.thread.join(timeout=2)


def render_stream(frame: np.ndarray, surface: pygame.Surface):
    surface.fill((0, 0, 0))
    screen_w, screen_h = surface.get_size()
    frame_h, frame_w = frame.shape[:2]

    scale = min(screen_w / frame_w, screen_h / frame_h)
    new_w, new_h = int(frame_w * scale), int(frame_h * scale)

    x = (screen_w - new_w) // 2
    y = (screen_h - new_h) // 2

    frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
    frame_surface = pygame.transform.smoothscale(frame_surface, (new_w, new_h))
    surface.blit(frame_surface, (x, y))
