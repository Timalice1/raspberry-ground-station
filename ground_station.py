import cv2
import subprocess
import pygame
import sys
import paramiko
import threading
import json
import time

DEADZONE = 0.08
AXIS_THR = 1
AXIS_YAW = 0

INVERT_THR = 1 
INVERT_YAW = 1

CAM_IP = "192.168.106.110"
PI_IP = "100.117.181.95"
PI_USER ="raspberry-drone"

RESOLUTION = (640, 480)

pygame.init()
screen = pygame.display.set_mode(RESOLUTION)
clock = pygame.time.Clock()

class CameraStream:
    def __init__(self, cam_ip, local_port):
        self.rtsp_url = f"rtsp://admin:Admin1234@127.0.0.1:{local_port}/cam/realmonitor?channel=1&subtype=1"
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.connected = False
        self.cam_ip = cam_ip
        
        self.tunnel = subprocess.Popen(["ssh", "-N", "-L", f"{local_port}:{cam_ip}:554", f"{PI_USER}@{PI_IP}"])
        if self.tunnel.poll() is not None:
            return

        self.connected = True       
        self.thread = threading.Thread(target=self._grab, daemon = True)
        self.thread.start()

    def _grab(self):

        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        if not self.cap.isOpened():
            self.tunnel.terminate()
            self.connected = False
            return

        failures = 0
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                failures = 0 
                with self.lock: 
                    self.frame = frame
            else:
                failures += 1
                if failures > 30:
                    print("stream lost")
                    self.connected = False
                    break

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None
    
    def stop(self):
        self.running = False
        self.thread.join()
        if hasattr(self, "cap"):
            self.cap.release()
        if hasattr(self, "tunel"):
            self.tunnel.terminate()

def setup_connection():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=PI_IP, username=PI_USER, timeout=10)
        print(f"Connected to {PI_USER}@{PI_IP} succesfully")
        return ssh
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

def render_stream(frame):
    frame = cv2.resize(frame, RESOLUTION)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
    screen.blit(surf, (0, 0))
    pygame.display.flip()

def map(value: float, in_min, in_max, out_min, out_max) -> int:
    return out_min + ((value - in_min) / (in_max - in_min)) * (out_max - out_min)

try:
    current_stream = 0
    streams = [
        CameraStream("192.168.106.109", 8554),
        CameraStream("192.168.106.10", 8555)
        # --> any additional camera streams add here
    ]

    ssh = setup_connection()
    stdin, stdout, stderr = ssh.exec_command("python vesc-control.py")

    if pygame.joystick.get_count() == 0:
        print("no joystick found")
        sys.exit(1)
    joystick = pygame.joystick.Joystick(0)

    while True:
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt
            
            if event.type == pygame.JOYBUTTONUP:
                if event.button == 0:
                    current_stream = current_stream + 1 if current_stream + 1 < len(streams) else 0

        #==========================
        if not streams[current_stream].connected:
            continue
        frame = streams[current_stream].read()
        if frame is None:
            continue
        render_stream(frame)
        #=========================

        #======================================================================================= 
        thr = joystick.get_axis(AXIS_THR) if abs(joystick.get_axis(AXIS_THR)) > DEADZONE else 0
        yaw = joystick.get_axis(AXIS_YAW) if abs(joystick.get_axis(AXIS_YAW)) > DEADZONE else 0
        

        data = {
            "thr": int(map(thr, -1, 1, 1000, 2000)),
            "yaw": int(map(yaw, -1, 1, 1000, 2000))
        }

        stdin.write(f"{json.dumps(data)}\n")
        stdin.flush()
        #=======================================================================================

        clock.tick(30)

finally:
    for stream in streams:
        stream.stop()
    ssh.close()
    pygame.quit()