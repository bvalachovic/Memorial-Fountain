#!/usr/bin/env python3
"""
Minimal pump hardware test — bypasses all fountain controller logic.

Usage:
  python3 pump_test.py           # pump on until Ctrl+C
  python3 pump_test.py --cycle   # 10s on / 10s off loop

Wiring this tests:
  MCP4725 VCC  Gray   Pi pin 1
  MCP4725 SDA  White  Pi pin 3
  MCP4725 SCL  Black  Pi pin 5
  MCP4725 GND  Purple Pi pin 6
  MCP4725 OUT  Blue   L298N ENA  (latched max — enables L298N)
  L298N IN1    Red    Pi pin 12 GPIO 18  (set HIGH = full power)
  L298N IN2    Brown  Pi pin 14 GND      (hardwired, fixed direction)
  L298N OUT1/2        Pump +/-
"""

import sys
import time
import logging
import RPi.GPIO as GPIO
import board
import busio
import adafruit_mcp4725

IN1_PIN = 18
ON_SECONDS = 10
OFF_SECONDS = 10

logging.basicConfig(level=logging.INFO, format='%(asctime)s  %(message)s')


def init_hardware():
    logging.info("Step 1: Initializing MCP4725 over I2C...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        dac = adafruit_mcp4725.MCP4725(i2c, address=0x60)
        dac.raw_value = 4095
        logging.info("  MCP4725 found at 0x60 — ENA latched HIGH (Blue wire -> L298N ENA)")
    except Exception as e:
        logging.error(f"  MCP4725 failed: {e}")
        logging.error("  Stopping — ENA pin is not driven. Pump will not run.")
        sys.exit(1)

    logging.info("Step 2: Configuring GPIO 18 as output (Red wire -> L298N IN1)...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(IN1_PIN, GPIO.OUT)
    GPIO.output(IN1_PIN, GPIO.LOW)
    logging.info("  GPIO 18 ready.")

    return dac


def pump_on():
    GPIO.output(IN1_PIN, GPIO.HIGH)
    logging.info("  Pump ON  (IN1 HIGH — full power)")


def pump_off():
    GPIO.output(IN1_PIN, GPIO.LOW)
    logging.info("  Pump OFF (IN1 LOW)")


def shutdown(dac):
    pump_off()
    dac.raw_value = 0
    GPIO.cleanup()
    logging.info("Stopped. GPIO cleaned up.")


def main():
    cycle_mode = '--cycle' in sys.argv

    dac = init_hardware()

    try:
        if cycle_mode:
            logging.info(f"Cycle mode: {ON_SECONDS}s on / {OFF_SECONDS}s off. Ctrl+C to stop.")
            while True:
                pump_on()
                time.sleep(ON_SECONDS)
                pump_off()
                time.sleep(OFF_SECONDS)
        else:
            pump_on()
            logging.info("  Press Ctrl+C to stop.")
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        logging.info("\nCtrl+C received.")
    finally:
        shutdown(dac)


if __name__ == '__main__':
    main()
