#include <HardwareSerial.h>
#include "ArduinoJson.h"
#include <cmath>

#define PPM_LEFT 4
#define PPM_RIGHT 5
#define CH_LEFT 0
#define CH_RIGHT 1

#define VOLTAGE_PIN 13
#define VOLTAGE_MULT 15.7

void set_ppm(int ch, int us)
{
    us = constrain(us, 1000, 2000);
    int duty = (us * 16383UL) / 20000;
    ledcWrite(ch, duty);
}

void set_engine(int thr, int yaw)
{
    int diff = yaw - 1500;

    int left = constrain(thr + diff, 1000, 2000);
    int right = constrain(thr - diff, 1000, 2000);

    set_ppm(CH_LEFT, left);
    set_ppm(CH_RIGHT, right);
}

void handle_cmd()
{

    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.length() == 0)
        return;

    JsonDocument data;
    DeserializationError err = deserializeJson(data, cmd);

    if (err != DeserializationError::Ok)
    {
        Serial.print("Deserialization failed: ");
        Serial.println(err.f_str());
        return;
    }

    int thr = data["thr"] | 1500;
    int yaw = data["yaw"] | 1500;

    set_engine(thr, yaw);
}

float read_battery_voltage()
{
    float vout = (analogReadMilliVolts(VOLTAGE_PIN) / 1000.0) * VOLTAGE_MULT;
    return constrain(vout, 0.0f, 50.0f);
}

void handle_telemetry()
{
    JsonDocument telem;
    telem["voltage"] = read_battery_voltage();

    Serial.print("TELEM:");
    serializeJson(telem, Serial);
    Serial.println();
}

void setup()
{
    Serial.begin(115200);

    ledcSetup(CH_LEFT, 50, 14);
    ledcSetup(CH_RIGHT, 50, 14);

    ledcAttachPin(PPM_LEFT, CH_LEFT);
    ledcAttachPin(PPM_RIGHT, CH_RIGHT);

    set_engine(1500, 1500);

    Serial.println("ESP32 are ready...");
}

void loop()
{
    handle_telemetry();
    handle_cmd();
}