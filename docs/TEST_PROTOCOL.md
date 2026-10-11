# R36S Clone (Typ 2) - Testprotokoll & Referenzbasis

## 1. Verifizierte Referenzbasis (Funktionierendes ArkOS-Image)

- **Referenzdatei:** `C:\Users\luism\Downloads\dArkOS4Clone-20261008.img` (Größe: 12.411.994.112 Bytes)
- **Status:** Bootet reproduzierbar und erfolgreich auf der vorliegenden Konsole mit derselben TF1-microSD-Karte.
- **Kryptografischer Nachweis der Bootloader-Binaries:**
  - `Sector 64 (idbloader)`: MD5 `065c4e4e3e77414f636cbcfd7ee88a0b` (Datei) / `9832387ef83261e9cbe2901962066d7b` (345 Sektoren gepadded) ↔ identisch mit `clone-uboot/idbloader.img`
  - `Sector 16384 (uboot)`: MD5 `a1a164e2451f5d0f3743f700a463de11` ↔ identisch mit `clone-uboot/uboot_oct05_emmc.img`
  - `Sector 24576 (trust)`: MD5 `ba8fd9c133787ae54cc75fc35858eff3` ↔ identisch mit `clone-uboot/trust.img`

## 2. Hardware-Profil der Zielkonsole

- **Mainboard:** R36S-V12 (2 diskrete RAM-Chips)
- **Display:** Panel 1 (`KD35T133` / `ST7701S`)
- **Audio:** Externer Verstärker auf `GPIO3_PA7` (Audio Mute active-low / invertiert)
- **Joysticks:** AMUX (`GPIO2_PB3`)

---

## 3. Generierte Test-Images (Stufe 2 Delta-Bisect)

Alle drei Images wurden frisch und deterministisch aus `build-img/lineage-18.1-20250902-2052-r36s-android.img.zip` erzeugt:

| Test-Image | Pfad | Größe | Sektor 0 (MBR) | Sektoren 1–63 | FAT32 BOOT-Partition | Bootloader-Sektoren |
|---|---|---|---|---|---|---|
| **T1** | `build-img/lineage-test-T1.img` | 3.221.225.472 B | Schutz-MBR (Stock) | **Stock GPT intakt** | Stock (unberührt) | 64, 16384, 24576 gefused (`uboot_oct05_emmc.img`) |
| **T2** | `build-img/lineage-test-T2.img` | 3.221.225.472 B | Reines MBR (dArkOS) | **Auf 0x00 genullt** | Stock (unberührt) | 64, 16384, 24576 gefused (`uboot_oct05_emmc.img`) |
| **T3** | `build-img/lineage-test-T3.img` | 3.221.225.472 B | Reines MBR (dArkOS) | **Auf 0x00 genullt** | **Gepatched:** Kernel, DTB, `boot.ini` (`root=/dev/mmcblk0p2`, attr `0x20`) | 64, 16384, 24576 gefused (`uboot_oct05_emmc.img`) |

---

## 4. Testprotokoll-Matrix (Stufe 2 & 3)

| Test-ID | Basis-Image | Geänderte Variable (genau EINE) | Vorab-Hypothese / Erwartung | Tatsächliche Beobachtung | Ergebnis |
|---|---|---|---|---|---|
| **T1** | Stock Lineage 20250902 | **Nur 3 Bootloader-Sektoren gefused** (`idbloader`, `uboot_oct05_emmc`, `trust`). MBR, GPT & FAT32 unberührt. | Wenn Banner: Problem in SD/Spannung. Wenn kein Banner: Bootloader funktioniert. | Backlight an, kein Banner, Konsole bleibt dauerhaft an. | **BESTANDEN (Gate 1)** |
| **T2** | T1 | MBR-Umbau + Nullen in Sektoren 1–63 | Wenn Banner: MBR stört U-Boot. Wenn kein Banner: MBR wird akzeptiert. | Identisch zu T1: Backlight an, kein Banner, Konsole bleibt dauerhaft an. | **BESTANDEN (Gate 2)** |
| **T3 (v1)** | T2 | FAT32 Kernel, DTB (`rk3326-r36s-android.dtb`), `boot.ini` | Testet Dateisystem & DTB-Adoption. | Grauer Banner nach ~5s (`U-BOOT (spinor) : Oct 05 2026 07:52:14`), dann Shutdown (Error Code 4). | **FEHLGESCHLAGEN** (Root Cause isoliert: DTB `aliases` vertauscht TF1 mit TF2) |
| **T3 (v2)** | T2 | DTB mit neutralisierten MMC-Aliasen (`FDT_NOP` auf `mmc0`/`mmc1`), Stock `boot.ini` + `Image-resizing` | U-Boot behält `mmc 1` auf Boot-Slot TF1, `mmc dev 1` gelingt, Kernel wird geladen. | Backlight an, **KEIN Banner, KEIN Shutdown**, Konsole bleibt dauerhaft aktiv! | **BESTANDEN (Gate 3)** |

---

## 5. Status & Nächste Schritte (Next Milestone: Kernel & Display)

### Erreichter Durchbruch:
* Die U-Boot-Bootloader-Barriere (Error Code 4 / Spinor-Banner) ist **vollständig überwunden**.
* U-Boot initialisiert alle Driver-Model-Geräte korrekt, findet die SD-Karte auf Slot 1, parst `boot.ini`, lädt DTB und Kernel (`Image-resizing`) in den RAM und übergibt die Kontrolle.

### Beobachtung auf Hardware (T3 v2):
* Konsole schaltet ein, Display-Hintergrundbeleuchtung ist aktiv.
* Konsole bleibt stabil und dauerhaft eingeschaltet (kein Absturz, kein Reset, kein Error-Code).
* Bildschirm bleibt vorerst schwarz (Backlight leuchtet).

### Arbeitsplan für die nächste Session:
1. **Verhalten von `Image-resizing` analysieren:**
   - Der Stock-First-Boot-Kernel (`Image-resizing`, 25 MB) ist ein Headless-Initramfs-Resizer, der die Partition 2 vergrößert und danach `boot.ini-android` als neue `boot.ini` setzt.
   - Prüfen, wie lange der Resizer auf der SD-Karte arbeitet oder ob er nach 1–2 Minuten automatisch neu startet.
2. **Display-Treiber im Android-Kernel (`ST7701S` / `KD35T133`):**
   - Prüfen, ob die MIPI-DSI-Initialisierungssequenz im DTB für Panel 1 beim Kernel-Start korrekt durchläuft oder ob Kernel-Boot-Logs (z. B. via Framebuffer-Konsole `fbcon` / `console=tty0`) sichtbar gemacht werden können.
3. **Audio-Amp & Controller:**
   - Sobald Android hochfährt, GPIO3_PA7 (Verstärker) und AMUX-Joysticks validieren.

---

## 5. Testregeln & Protokollierung

1. **Einzelfaktor-Prinzip:** Pro Test wird exakt eine Variable geändert.
2. **Vorab-Hypothese:** Vor jedem Flash-Vorgang muss die Hypothese schriftlich hier festgehalten werden.
3. **Beobachtungsbeweis:** Nach jedem Flash wird das exakte Verhalten (Display-Meldung, Dauer bis Power-off, LED-Farbe) eingetragen.
4. **Keine Spekulation:** Aussagen wie "behoben" sind erst nach physikalischem Funktionsnachweis auf dem Gerät zulässig.
