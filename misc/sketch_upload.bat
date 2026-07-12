@echo off
echo ==========================
echo ESP32 sketch uploading...
echo ==========================

set FIRMWARE_PATH=..\\.pio\\build\\esp32s3\\
set HOST=100.117.181.95
set USER=raspberry-drone

cd ..\\raspberry-esp
%userprofile%\.platformio\penv\Scripts\platformio.exe run -e esp32s3

scp -o StrictHostKeyChecking=no %FIRMWARE_PATH%firmware.bin %USER%@%HOST%:~/
scp -o StrictHostKeyChecking=no %FIRMWARE_PATH%bootloader.bin %USER%@%HOST%:~/
scp -o StrictHostKeyChecking=no %FIRMWARE_PATH%partitions.bin %USER%@%HOST%:~/
ssh -o StrictHostKeyChecking=no %USER%@%HOST% "esptool-venv/bin/esptool --chip esp32s3 --port /dev/ttyACM0 erase-flash"
ssh -o StrictHostKeyChecking=no %USER%@%HOST% "esptool-venv/bin/esptool --chip esp32s3 --port /dev/ttyACM0 --baud 921600 write-flash -z 0x0 bootloader.bin 0x8000 partitions.bin 0x10000 firmware.bin"
