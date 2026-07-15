import paramiko
from typing import Optional
import threading
import json
import logging


class SSHConnector:
    def __init__(self):
        self.stdin = None
        self.ssh: Optional[paramiko.SSHClient] = None

    def connect(self, user: str, host: str):
        if not user or not host:
            logging.error("Invalid host and username provided")
            return False, "Invalid host and username provided"
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=host, username=user, timeout=10)
            logging.info(f"Connected to {user}@{host}")
            return True, ""
        except Exception as e:
            logging.exception(e)
            return False, str(e)

    def start_remote_controll(self):
        if not self.ssh:
            logging.error(
                "Failed to start remote controll, ssh connection does not set"
            )
            return False
        try:
            self.stdin, self.stdout, stderr = self.ssh.exec_command(
                "python vesc-control.py"
            )
            self._remote_output(self.stdout, stderr)

            logging.info("Remote controll started")
            return True
        except Exception as e:
            logging.exception(e)
            return False

    def send_command(self, cmd: dict):
        if self.stdin is None:
            logging.log("ssh_connector::send_command(): No input channel")
            return False
        try:
            self.stdin.write(f"{json.dumps(cmd)}\n")
            self.stdin.flush()
            return True
        except Exception as e:
            logging.exception(f"ssh_connector::send_command(): {str(e)}")
            return False

    def read_telemetry(self):
        data: str = self.stdout.readline().strip()
        if data.startswith("TELEM:"):
            return data[6:]

    def close(self):
        if self.ssh:
            self.ssh.close()

    def _remote_output(self, stdout, stderr):
        def _pump(stream, label):
            for line in iter(stream.readline, ""):
                if line:
                    if stream is stdout:
                        if line.startswith("TELEM:"):
                            continue
                        logging.info(f"[remote:{label}] {line.rstrip()}")
                    elif stream is stderr:
                        logging.error(f"[remote:{label}] {line.rstrip()}")

        threading.Thread(target=_pump, args=(stdout, "out"), daemon=True).start()
        threading.Thread(target=_pump, args=(stderr, "err"), daemon=True).start()
