# ESP32 Hardware Wiring Guide

## Visual PIN Layout

### ESP32 DevKit Pinout

```
┌─────────────────────────────────────────────┐
│          ESP32 Development Board            │
│           (ESP32-DEVKIT-V1)                 │
│                                             │
│  ┌───────────────┐   ┌───────────────┐    │
│  │  Left Side    │   │  Right Side   │    │
│  │               │   │               │    │
│  │ GND  D32      │   │ D12  D35      │    │
│  │ 3V3  D33      │   │ D13  D34      │    │
│  │ EN   D25      │   │ D14  D39      │    │
│  │ VP   D26  ◄──┼───┼─ Servo PIN!  │    │
│  │ VN   D27  ◄──┼───┼─ Conveyor PIN│    │
│  │ D34  D14      │   │ D4  (Flash)   │    │
│  │ D35  D12      │   │ D2  ◄────────┼─── Status LED
│  │ D36  D13      │   │ D15  GND     │    │
│  │ D39  D9(TX)   │   │ D8   5V      │    │
│  │ D34  D10      │   │ D23  3V3     │    │
│  │ 5V   D11      │   │ GND  GND     │    │
│  │ GND  D6       │   │ D1   D0      │    │
│  │ D23  D7       │   │ CLK  CMD     │    │
│  │ D22  D8       │   └───────────────┘    │
│  │ TX   D19      │                        │
│  │ RX   D18      │                        │
│  │ D21  D5       │                        │
│  │ GND  D17      │                        │
│  │ 3V3  D16      │                        │
│  │ D26  GND      │                        │
│  │ D25  GND      │                        │
│  │ D32  D37      │                        │
│  │ D33  D38      │                        │
│  │ D4   GND      │                        │
│  └───────────────┘                        │
└─────────────────────────────────────────────┘
```

## Component Connections

### 1️⃣ CONVEYOR MOTOR (GPIO27)

```
ESP32 GPIO27 ───────┐
                     │
                     ▼
            ┌────────────────┐
            │  Relay Module  │
            │  or Motor      │
            │  Driver        │
            └────────────────┘
                  │    │
            ┌─────┘    └─────┐
            │                │
      ┌─────▼─────┐    ┌─────▼─────┐
      │   +12V    │    │   Motor   │
      │   PSU     │    │  Positive │
      └───────────┘    └───────────┘

Ground Connections:
ESP32 GND ──────► Relay GND ──────► Motor GND
```

**Wiring Steps:**
1. Connect ESP32 GPIO27 → Relay Module "IN" pin
2. Connect ESP32 GND → Relay Module "GND"
3. Connect Relay Module "VCC" → 5V (from USB or external)
4. Connect Relay Module "COM" → +12V (motor supply)
5. Connect Relay Module "NO" (normally open) → Motor positive wire
6. Connect Motor negative → -12V (motor supply ground)

### 2️⃣ SERVO MOTOR (GPIO26)

```
       Signal
       (Yellow)
          │
          ▼
    ┌───────────────┐
    │  ESP32 GPIO26 │
    └───────────────┘
          │
          ▼
    ┌───────────────┐
    │   Servo MG990 │
    │   or SG90     │
    │               │
    │ Y: Signal ◄───┤ From GPIO26
    │ R: Power  ◄───┤ From 5V
    │ B: Ground ◄───┤ To GND
    └───────────────┘

Power Connections:
ESP32 5V ──────► Servo Red wire
ESP32 GND ──────► Servo Brown wire
```

**Wiring Steps:**
1. Connect Servo Yellow (Signal) → ESP32 GPIO26
2. Connect Servo Red (Power) → 5V (USB or external power)
3. Connect Servo Brown (Ground) → ESP32 GND
4. Make sure 5V and GND are common (all connected to ESP32)

### 3️⃣ STATUS LED (GPIO2, Optional)

```
ESP32 GPIO2 ──→ [270Ω Resistor] ──→ (+) LED (+)
                                        │
                                        │
                                       GND

Or with built-in LED:
ESP32 GPIO2 ──→ Built-in LED (if available)
```

**Wiring Steps:**
1. Connect ESP32 GPIO2 → LED Positive (long leg)
2. Connect LED Negative (short leg) → 220Ω-270Ω Resistor
3. Connect Resistor → ESP32 GND

**What LED shows:**
- Always ON = WiFi connected, system idle
- Blinking = Conveyor running, system active
- Always OFF = WiFi disconnected

## Complete System Diagram

```
                    ┌──────────────────┐
                    │   ESP32 DevKit   │
                    │                  │
        ┌──────────►│ GPIO27 Conveyor  │
        │   5V      │ GPIO26 Servo     │
        │   GND     │ GPIO2 Status LED │
        │           │                  │
        │           │ 3V3  5V  GND     │
        │           └───┬──┬───┬───────┘
        │               │  │   │
        │        ┌──────┘  │   │
        │        │    ┌────┘   │
        │        │    │   ┌────┘
        │        │    │   │
        │   ┌────▼────▼───▼────┐
        │   │  USB Power       │
        │   │  5V = Red        │
        │   │  GND = Black     │
        │   └──────────────────┘
        │
        └─── Optional: External 5V for servo

    ┌─────────────────────────────────────────────────┐
    │         Relay Module (5V triggered)             │
    │                                                 │
    │  GPIO27 ──► IN   GND ──► ESP32 GND            │
    │  5V ──────► VCC  NO ───► Motor Positive       │
    │            COM ─────────► +12V Power          │
    │                                                │
    └─────────────────────────────────────────────────┘
         (Switches 12V motor on/off)


    ┌──────────────────────────────────────────────────┐
    │     Servo Motor (MG995 or SG90)                 │
    │                                                  │
    │  GPIO26 ─────► Signal (Yellow wire)            │
    │  5V ──────────► Power (Red wire)               │
    │  GND ──────────► Ground (Brown wire)           │
    │                                                  │
    └──────────────────────────────────────────────────┘
         (Rotates 0°, 90°, 180°)


    ┌──────────────────────────────────────────────────┐
    │     Status LED (Optional)                        │
    │                                                  │
    │  GPIO2 ─► [270Ω] ─► LED(+) ─► else GND        │
    │                                                  │
    └──────────────────────────────────────────────────┘
         (Indicates system status)
```

## Pinout Reference (What You Need)

```
For Conveyor Control:
  GPIO27 ──────► Goes LOW or HIGH
  This pin controls the relay
  Relay switches 12V motor on/off

For Servo Control:
  GPIO26 ──────► PWM signal (50Hz)
  This pin sends servo control signal
  Servo moves to angle 0-180°

For Status LED (Optional):
  GPIO2 ──────► Indicates WiFi & system status
  Blink = active, Always on = ready, Off = disconnected

Power Supply:
  5V ──────► Powers servo, relay logic, and ESP32
  GND ──────► Common ground for all components
  12V ──────► Powers motor via relay
```

## Common Wiring Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Servo twitches but won't move | GPIO26 not connected | Check signal wire is soldered firmly |
| Conveyor always on | GPIO27 not working | Check relay module voltage, try different GPIO |
| Servo jitters | Ground not shared | Connect all GND pins together |
| LED doesn't blink | GPIO2 connection wrong | Check polarity (long leg to pin, short to GND via resistor) |
| Motor won't start | Relay not triggered | Test with multimeter on relay COM pin |

## Testing Each Component

### Test 1: Conveyor Relay
```cpp
// Add to ESP32 setup():
pinMode(27, OUTPUT);
digitalWrite(27, HIGH);  // Relay should click
delay(1000);
digitalWrite(27, LOW);   // Relay should click back
```
✓ Relay should click/clack when output changes

### Test 2: Servo
```cpp
// Add to ESP32 setup():
sortServo.attach(26, 500, 2400);
sortServo.write(0);     // Move to 0°
delay(1000);
sortServo.write(90);    // Move to 90°
delay(1000);
sortServo.write(180);   // Move to 180°
```
✓ Servo should rotate to each position

### Test 3: Status LED
```cpp
// Add to ESP32 setup():
pinMode(2, OUTPUT);
digitalWrite(2, HIGH);   // LED on
delay(500);
digitalWrite(2, LOW);    // LED off
delay(500);
// Repeat...
```
✓ LED should blink rapidly

## Power Supply Requirements

| Component | Voltage | Current | Notes |
|-----------|---------|---------|-------|
| ESP32 | 5V USB | ~500mA | Can be from computer |
| Servo Motor | 5V | ~1A peak | Needs stable 5V |
| Relay Module | 5V logic | ~100mA | Built-in protection |
| Motor (12V) | 12V | Varies | Separate PSU recommended |

**Recommended Setup:**
```
USB 5V (computer) ──→ ESP32 + Servo + Relay logic
12V PSU ──────────────► Motor via relay
(All GND connected)
```

## Safety Wiring Checklist

- [ ] All GND pins connected together (common ground)
- [ ] No bare wires touching (cover with tape if needed)
- [ ] Servo wires not near motor power lines
- [ ] Relay module properly secured (won't fall)
- [ ] Servo not strained at endpoints (0° and 180°)
- [ ] Motor has proper guards/enclosure
- [ ] All connections soldered or in headers (not taped)
- [ ] No shorts between 5V and GND
- [ ] No loose wires touching moving parts

## Tools Needed

- Soldering iron + solder (optional, for permanent connections)
- Multimeter (for testing connections)
- Jumper wires (22AWG recommended)
- Wire strippers
- Tape/shrink tubing (for insulation)

---

**Once wired, test each component independently before full system test!**

