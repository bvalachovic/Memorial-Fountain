#!/usr/bin/env python3
"""
VFD driver — production hardware using MCP4725 DAC → 0-10V VFD analog input.

Wiring (reference by wire color — confirm against actual VFD install):
  Pi pin 1  (3.3V)  → MCP4725 VCC
  Pi pin 3  SDA     → MCP4725 SDA  (White)
  Pi pin 5  SCL     → MCP4725 SCL  (Black)
  Pi pin 6  GND     → MCP4725 GND
  MCP4725 OUT       → VFD 0-10V analog input (via op-amp level shifter for 10V)

Speed control: 12-bit DAC value (0–4095) mapped to configured
  MIN_FREQUENCY_PERCENT–MAX_FREQUENCY_PERCENT of VFD output frequency.
"""

import time
import logging
import board
import busio
import adafruit_mcp4725
import RPi.GPIO as GPIO


class VFDDriver:

    def __init__(self, min_speed=30, max_speed=100, smoothing=0.2):
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.smoothing = smoothing
        self.current_output = 0
        self.target_output = 0

        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.dac = adafruit_mcp4725.MCP4725(i2c, address=0x60)
            logging.info("VFD driver ready (MCP4725 DAC at 0x60)")
        except Exception as e:
            logging.error(f"VFD: failed to initialize MCP4725: {e}")
            self.dac = None

    def _write_dac(self, value):
        """Write to DAC with retry on transient I2C errors (errno 5 / EIO)."""
        if self.dac is None:
            return
        for attempt in range(3):
            try:
                self.dac.raw_value = int(value)
                return
            except OSError as e:
                if attempt < 2:
                    logging.warning(f"VFD: DAC write failed (attempt {attempt+1}/3): {e} — retrying")
                    time.sleep(0.01)
                else:
                    logging.error(f"VFD: DAC write failed after 3 attempts: {e}")
            except Exception as e:
                logging.error(f"VFD: DAC write unexpected error: {e}")
                return

    def set_intensity(self, percent):
        """Map 0–100 intensity to DAC value within configured speed range."""
        if self.dac is None:
            return
        speed_range = self.max_speed - self.min_speed
        actual = self.min_speed + (percent / 100.0 * speed_range)
        actual = max(self.min_speed, min(self.max_speed, actual))
        self.target_output = int((actual / 100.0) * 4095)

    def update_smooth(self):
        """Exponential smoothing toward target — call from main loop."""
        if self.dac is None:
            return
        if self.current_output != self.target_output:
            diff = self.target_output - self.current_output
            self.current_output += diff * self.smoothing
            if abs(self.target_output - self.current_output) < 5:
                self.current_output = self.target_output
            self._write_dac(self.current_output)

    def ramp_to_zero(self):
        """Safely ramp DAC output down to zero."""
        logging.info("VFD: ramping to zero...")
        for i in range(100, -1, -5):
            speed_range = self.max_speed - self.min_speed
            actual = self.min_speed + (i / 100.0 * speed_range)
            self._write_dac(int((actual / 100.0) * 4095))
            time.sleep(0.1)
        self.current_output = 0
        self.target_output = 0
        logging.info("VFD: at zero")

    def cleanup(self):
        GPIO.cleanup()
