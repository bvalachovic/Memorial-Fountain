#!/usr/bin/env python3
"""
L298N H-bridge driver — prototype test rig with aquarium pump.

Wiring (reference by wire color):
  Pi pin 1  Gray   → MCP4725 VCC  (3.3V supply for DAC)
  Pi pin 3  White  → MCP4725 SDA  (I2C data)
  Pi pin 5  Black  → MCP4725 SCL  (I2C clock)
  Pi pin 6  Purple → MCP4725 GND
  MCP4725 OUT Blue → L298N ENA    (set to max; permanently enables L298N)
  Pi pin 12 Red    → L298N IN1    (GPIO 18, software PWM for speed)
  Pi pin 14 Brown  → L298N IN2    (hardwired to GND — fixed direction)
  L298N OUT1       → Pump Red (+)
  L298N OUT2       → Pump Black (-)

Speed control: PWM duty cycle on IN1 (0–100%).
  IN2 is always LOW (GND), so the pump always runs the same direction.
  MCP4725 keeps ENA at max (~3.3V) so the L298N is always enabled.
  Do NOT feed intermediate DAC voltages to ENA — that causes linear-mode
  heat dissipation on the L298N transistors.
"""

import time
import logging
import RPi.GPIO as GPIO
import board
import busio
import adafruit_mcp4725

IN1_PIN = 18     # GPIO 18 = Pi physical pin 12 (Red) — software PWM
PWM_FREQ = 1000  # Hz — suitable for small DC motor/pump


class L298NDriver:

    def __init__(self, min_speed=30, max_speed=100, smoothing=0.2):
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.smoothing = smoothing
        self.current_duty = 0.0
        self.target_duty = 0.0

        # Set MCP4725 ENA to maximum so L298N stays fully enabled.
        # This avoids transistors sitting in linear mode (which causes heat).
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            dac = adafruit_mcp4725.MCP4725(i2c, address=0x60)
            dac.raw_value = 4095
            logging.info("L298N: MCP4725 ENA latched high (Blue wire)")
        except Exception as e:
            logging.warning(f"L298N: MCP4725 unavailable, ENA may be floating: {e}")

        # IN1 as software PWM (Red wire, physical pin 12)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IN1_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(IN1_PIN, PWM_FREQ)
        self.pwm.start(0)

        logging.info("L298N driver ready")
        logging.info("  IN1 Red   pin 12 GPIO 18 → software PWM (speed)")
        logging.info("  IN2 Brown pin 14 GND     → fixed direction")
        logging.info("  ENA Blue  MCP4725 OUT    → latched HIGH")

    def set_intensity(self, percent):
        """Map 0–100 intensity to configured min/max duty cycle range."""
        speed_range = self.max_speed - self.min_speed
        duty = self.min_speed + (percent / 100.0 * speed_range)
        duty = max(0, min(self.max_speed, duty))
        self.target_duty = duty

    def update_smooth(self):
        """Exponential smoothing toward target — call from main loop."""
        if abs(self.current_duty - self.target_duty) > 0.5:
            diff = self.target_duty - self.current_duty
            self.current_duty += diff * self.smoothing
            if abs(self.target_duty - self.current_duty) < 0.5:
                self.current_duty = self.target_duty
            self.pwm.ChangeDutyCycle(self.current_duty)

    def ramp_to_zero(self):
        """Gradually reduce speed to zero."""
        logging.info("L298N: ramping down...")
        while self.current_duty > 1:
            self.current_duty = max(0, self.current_duty - 5)
            self.pwm.ChangeDutyCycle(self.current_duty)
            time.sleep(0.05)
        self.current_duty = 0.0
        self.target_duty = 0.0
        self.pwm.ChangeDutyCycle(0)
        logging.info("L298N: stopped")

    def cleanup(self):
        if self.pwm:
            self.pwm.stop()
        GPIO.cleanup()
