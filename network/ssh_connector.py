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
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(hostname=host, username=user, timeout=10)
            return True, f"Connected to {user}@{host}"
        except Exception as e:
            return False, str(e)

    def start_remote_controll(self):
        if not self.ssh:
            return False, "SSH does not connected"
        try:
            self.stdin, stdout, stderr = self.ssh.exec_command("python vesc-control.py")
            self._remote_output(stdout, stderr)
            exit_code = self.stdin.channel.recv_exit_status()
            # if exit_code != 0:
            #     return False, f"Failed to run remote controll, exit code: {exit_code}"

            return True, "Remote controll started"
        except Exception as e:
            return False, str(e)

    def send_command(self, cmd: dict):
        if self.stdin is None:
            logging.log("send_command(): No input channel")
            return False
        try:
            self.stdin.write(f"{json.dumps(cmd)}\n")
            self.stdin.flush()
            return True
        except Exception as e:
            logging.exception(f"send_command(): {str(e)}")
            return False

    def close(self):
        if self.ssh:
            self.ssh.close()

    def _remote_output(self, stdout, stderr):
        def _pump(stream, label):
            for line in iter(stream.readline, ""):
                if line:
                    if stream is stdout:
                        logging.info(f"[remote:{label}] {line.rstrip()}")
                    elif stream is stderr:
                        logging.error(f"[remote:{label}] {line.rstrip()}")

        threading.Thread(target=_pump, args=(stdout, "out"), daemon=True).start()
        threading.Thread(target=_pump, args=(stderr, "err"), daemon=True).start()
