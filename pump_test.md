# pump_test.py Instructions

Before running, double-check one thing that's likely the root cause of the L298N heat: make sure the 12V supply is connected to the L298N's VS pin (the motor power pin), not just the 5V logic supply from the Pi. If those are crossed or the VS is floating, the L298N will try to draw motor current through its logic supply and get hot without moving the pump.

Then:

## Always-on (simplest test)

python3 pump_test.py

## 10s on / 10s off loop

python3 pump_test.py --cycle
Watch the log output — if you see MCP4725 found at 0x60 — ENA latched HIGH followed by Pump ON and still nothing happens, the next step is a multimeter on the L298N OUT1/OUT2 pins while it's running to see what voltage is actually reaching the pump.

## The decision that hasn't been made yet

Nobody has chosen the production pump motor. That choice locks in the control hardware:

| Production Pump Choice | Control Hardware | VFD Required? |
| --- | --- | --- |
| **3-Phase AC Induction** | VFD (Variable Frequency Drive) | **TRUE** |
| **Large DC (24-48V)** | High-Power MOSFET / PWM Driver | **FALSE** |
| **Single-Phase AC** | TRIAC / Solid State Relay | **FALSE** (Different Logic) |

A large DC pump + high-power PWM controller would be simpler, cheaper, and use the same software paradigm as the prototype. The tradeoff is that 3-phase AC pumps dominate the large commercial fountain market, so DC options get limited above a certain flow rate.

## Pump Size

### Small decorative fountain (tabletop, birdbath, small garden accent)

- 50–400 GPH
- Usually 12V DC submersible — same class as your aquarium pump, just more flow
- 10–40W

### Medium backyard fountain or small pond (100–500 gallons)

- 500–2000 GPH
- Typically 120V AC submersible, single-phase
  50–200W
- This is the most common "backyard pond" pump you'd find at a home improvement store

### Serious koi pond or large water feature (500–2000+ gallons)

- 2000–6000 GPH
- 120V or 240V AC, sometimes external (not submersible)
- 200–600W

#### The relevance to your project:

For a memorial fountain with a visible, impressive jet — say 2–5 feet of height — you're likely looking at 1000–3000 GPH. That range falls squarely in the 120V AC single-phase territory for most off-the-shelf pumps.

The important point: *120V AC single-phase pumps don't need a VFD*. A VFD is an industrial tool for 3-phase motors. A single-phase AC pump runs off standard household current, and you'd control it differently (a TRIAC-based dimmer/controller, or just on/off with a relay).

Or: quality 24V DC pumps exist in the 1000–2500 GPH range (Jebao, Aquascape, Supreme make them). Those you could control with PWM — same paradigm as the prototype, just higher voltage and a beefier driver than the L298N.

So for production you really have three realistic paths:


| Pump Type            | Flow available  | Speed control method               |
| ---------------------- | ----------------- | ------------------------------------ |
| 12V DC               | Up to ~800 GPH  | PWM via L298N or MOSFET            |
| 24V DC               | Up to ~2500 GPH | PWM (Higher-power) MOSFET driver   |
| 120V AC single-phase | Up to ~4000 GPH | Relay (on/off) or TRIAC (variable) |
| 3-phase AC           | Unlimited       | VFD                                |

For most backyard ponds/fountains, a 24V DC pump hits the sweet spot — enough flow for a real display, same software control paradigm as the prototype, no VFD, no mains AC wiring complexity.

Your analysis is technically sound and provides a very logical roadmap for moving from a prototype to a production fountain. Your troubleshooting advice for the L298N is spot-on—miswiring the logic and motor supplies is the #1 cause of "thermal runaway" in those specific drivers.

Here are a few minor refinements to ensure your technical details and logic are ironclad:

---

## 1. Troubleshooting Logic

Your advice regarding the **VS (Pin 4)** vs. **VSS (Pin 9)** on the L298N is correct. However, keep in mind:

**The Jumper:** Most L298N boards have a "5V Enable" jumper. If the 12V supply is connected and the jumper is **on**, the L298N regulates its own 5V logic from the 12V rail. If the user is also feeding 5V from the Pi into the logic pin while that jumper is on, they can create a voltage conflict that generates heat.
**Grounding:** Ensure you mention that the Raspberry Pi GND **must** be tied to the L298N GND, or the control signals will have no reference and the pump won't trigger.

---

## 2. Speed Control Nuance (TRIAC vs. DC)

In your table, you mention using a **TRIAC** for single-phase AC pumps. While technically possible, there is a "gotcha" you should be aware of:

**Submersible AC Pumps:** Most small-to-medium AC submersible pumps use **Permanent Split Capacitor (PSC)** or **Synchronous Magnetic** motors. These do not always react well to TRIAC dimming (it can cause humming or overheating).
**The "Clean" Choice:** This reinforces your conclusion that **24V DC** is the "sweet spot." It allows for smooth 0–100% linear speed control via PWM without the electrical noise or stalling issues common when trying to "dim" an AC water pump.

---

## 4. Why the 24V DC Path Wins

You are correct that the software paradigm remains the same. To make this even "sounder," consider the safety aspect:

**Safety (UL/NEC):** 24V DC is considered "Low Voltage." In many jurisdictions, you can install 24V wiring without a licensed electrician or conduit, which is rarely the case for 120V/240V AC installations near water. This makes the 24V DC pump significantly more DIY/prototyper friendly.

---

## Final Verdict

The document is **logically sound**. It correctly identifies the hardware bottleneck (the L298N is for hobbyists, not for 2000 GPH pumps) and provides a clear path forward. The recommendation of a 24V DC pump is the most efficient choice for maintaining your current software stack while scaling up the physical water display.
