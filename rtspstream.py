import subprocess
import threading
import time
from typing import Optional
import pygame
import imageio_ffmpeg
import numpy as np
import json
from box import Box
import queue

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
RES = {1080: (0, 1920, 1080), 720: (0, 1280, 720), 480: (1, 640, 480)}

with open("config.json", "r", encoding="utf-8") as f:
    cfg = Box(json.load(f))


class CameraStream:
    def __init__(self, cam_ip: str, localport: int):
        self.local_port = localport
        self.cam_ip = cam_ip

        self.subtype, self.width, self.height = RES.get(cfg.res, (1, 640, 480))

        self.frame_size = self.width * self.height * 3
        self._rtsp_url = f"rtsp://{cfg.cam_cfg.credentials}@127.0.0.1:{localport}/cam/realmonitor?channel=1&subtype={self.subtype}"

        self.ffmpeg = None
        self.latest_frame = None

        self.running = False
        self._lock = threading.Lock()

        self.tunnel: Optional[subprocess.Popen] = None
        self.thread: Optional[threading.Thread] = None

    def _run_ffmpeg(self):
        cmd = [
            FFMPEG_BIN,
            "-rtsp_transport",
            "tcp",
            "-fflags",
            "nobuffer",  # Disable internal stream buffering
            "-flags",
            "low_delay",  # Force low delay optimizations
            "-strict",
            "experimental",
            "-i",
            self._rtsp_url,
            "-f",
            "image2pipe",
            "-rw_timeout",
            "2000000",
            "-probesize",
            "32",
            "-pix_fmt",
            "rgb24",  # Raw RGB24 matches Pygame surface natively
            "-vcodec",
            "rawvideo",
            "-s",
            f"{self.width}x{self.height}",
            "-reorder_queue_size",
            "0",
            "-",  # Output to stdout
        ]

        self.ffmpeg = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=self.frame_size,
        )

    def start(self):
        if not self.tunnel or self.tunnel.poll() is not None:
            self.running = False
            self.tunnel = subprocess.Popen(
                [
                    "ssh",
                    "-N",
                    "-L",
                    f"{self.local_port}:{self.cam_ip}:554",
                    f"{cfg.usr}@{cfg.host}",
                ]
            )

        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._grab, daemon=True)
        self.thread.start()

    def _read_frames(self, proc, q: "queue.Queue"):
        while self.running:
            raw_frame = proc.stdout.read(self.frame_size)
            if not raw_frame or len(raw_frame) != self.frame_size:
                try:
                    q.put_nowait(None)  # sentinel: stream ended
                except queue.Full:
                    pass
                return

            frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape(
                (self.height, self.width, 3)
            )

            try:
                q.put_nowait(frame)
            except queue.Full:
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                q.put_nowait(frame)

    def _grab(self):
        while self.running:
            self._run_ffmpeg()
            frame_queue: "queue.Queue" = queue.Queue(maxsize=1)
            reader = threading.Thread(
                target=self._read_frames, args=(self.ffmpeg, frame_queue)
            )
            reader.start()

            while self.running:
                try:
                    frame = frame_queue.get(timeout=cfg.cam_cfg.reconection_timeout)
                except queue.Empty:
                    break

                if frame is None:
                    break

                with self._lock:
                    self.latest_frame = frame

            with self._lock:
                self.latest_frame = None
            if self.ffmpeg:
                self.ffmpeg.terminate()
                self.ffmpeg.wait()

    def _read(self) -> Optional[np.ndarray]:
        with self._lock:
            return self.latest_frame

    def render_stream(self, surface: pygame.Surface):
        surface.fill((0, 0, 20))

        frame = self._read()
        if frame is not None:
            screen_w, screen_h = surface.get_size()
            frame_h, frame_w = frame.shape[:2]

            scale = min(screen_w / frame_w, screen_h / frame_h)
            new_w, new_h = int(frame_w * scale), int(frame_h * scale)

            x = (screen_w - new_w) // 2
            y = (screen_h - new_h) // 2

            frame_surface = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
            frame_surface = pygame.transform.smoothscale(frame_surface, (new_w, new_h))

            surface.blit(frame_surface, (x, y))

    def stop(self):
        self.running = False
        if hasattr(self, "tunnel") and self.tunnel is not None:
            self.tunnel.terminate()
        if hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join(timeout=3)
        if hasattr(self, "ffmpeg") and self.ffmpeg is not None:
            self.ffmpeg.terminate()
