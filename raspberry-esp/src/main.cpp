#include <HardwareSerial.h>
#include "ArduinoJson.h"

#define PPM_LEFT 4
#define PPM_RIGHT 5
#define CH_LEFT 0
#define CH_RIGHT 1

void SetPPM(int ch, int us)
{
    int duty = (us * 16383UL) / 20000;
    ledcWrite(ch, duty);
}

void set_engine(int thr, int yaw)
{

    int left = thr;
    int right = thr;
    int diff = yaw - 1500;

    left += diff;
    right -= diff;
    left = constrain(left, 1000, 2000);
    right = constrain(right, 1000, 2000);

    SetPPM(CH_LEFT, left);
    SetPPM(CH_RIGHT, right);
}

void setup()
{
    Serial.begin(115200);

    ledcSetup(CH_LEFT, 50, 14);
    ledcSetup(CH_RIGHT, 50, 14);

    ledcAttachPin(PPM_LEFT, CH_LEFT);
    ledcAttachPin(PPM_RIGHT, CH_RIGHT);

    set_engine(1500, 1500);

    Serial.println("ESP32 ready...");
}

void loop()
{

    if (Serial.available())
    {
        String json = Serial.readStringUntil('\n');
        json.trim();

        if (json.length() == 0)
        {
            Serial.print("No data received");
            return;
        }

        JsonDocument data;
        DeserializationError err = deserializeJson(data, json);

        if (err != DeserializationError::Ok)
        {
            Serial.print("Deserialization failed: ");
            Serial.println(err.f_str());
            return;
        }

        int thr = data["thr"];
        int yaw = data["yaw"];

        set_engine(thr, yaw);
    }
}