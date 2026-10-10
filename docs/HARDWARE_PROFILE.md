# Hardware Profile: R36S Clone (Type 2 Panel 1 With Amplifier)

## Device Overview
* **Device Model:** R36S Clone (often labeled R36S-V12 / Type 2 clone)
* **SoC:** Rockchip RK3326 (Quad-core ARM Cortex-A35 @ 1.25–1.5 GHz, Mali-G31 MP2 GPU)
* **RAM Configuration:** **2 RAM chips** (Dual-channel DDR3 layout)
  * *Important:* Standard R36S images expect a single RAM chip. Using standard single-RAM bootloader binaries (`idbloader.img`) causes DDR memory training failure (manifesting as a rapid red LED blinking at 2–3 Hz with no screen output).
* **Reference Firmware:** ArkOS4Clone (`lcdyk0517/arkos4clone`)
* **Stock DTB MD5:** `c9eb94f10298a567efe0506ca07bbf66` (107,106 bytes)
* **Identified Compatibility Profile:** `Clone R36s → Clone Type 2 Panel 1 With Amplifier`

---

## Screen & Display
* **Panel Model:** Panel 1 / Panel 8 (`KD35T133`)
* **Resolution:** 640 x 480 @ 60 Hz
* **Interface:** MIPI DSI
* **Init Sequence:** Starts with `39 00 04 b9 f1 12 83 ...`
* **DTB Node:** `display-timings` matched to Panel 1 timings from ArkOS4Clone and K4uanGP Android kernel.

---

## Audio Subsystem
* **Codec:** Rockchip RK817 Integrated Audio Codec
* **Speaker Amplifier:** External hardware amplifier circuit
* **Control Pin:** `GPIO3_PA7` (Active High)
  * Property: `spk-ctl-gpios = <&gpio3 7 GPIO_ACTIVE_HIGH>;`
  * Extra properties: `spk-mute-delay-ms = <50>;`, `use-ext-amplifier;`

---

## Joystick & Controller Multiplexer
* **Controller Type:** Open-source handheld game controller (ODROID-GO Advance compatible)
* **Analog Joysticks:** Hardware multiplexer (AMUX) connected to Rockchip SARADC
* **AMUX Control Pin:** `GPIO2_PB3`
* **Channel Mapping:** `<2 3 1 0>` (X/Y axis multiplexer mapping for Type 2 clones)
* **Supported Kernel:** K4uanGP kernel v1.1 (`android_kernel_gameconsole_r36s`)
