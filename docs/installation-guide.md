# Anleitung: LineageOS 18.1 (Andr36oid) auf Clone R36S (Type 2 Panel 1 mit Verstärker)

Diese Anleitung erklärt, wie du LineageOS 18.1 (Android 11) auf deinem R36S-Clone (Board **Clone Type 2 Panel 1 mit Verstärker**, z. B. V12 / G80CA) installierst.

---

## 1. Benötigte Dateien

1. **LineageOS Basis-Image:**
   * Download: [lineage-18.1-20250902-2052-r36s-android.img.zip](https://github.com/andr36oid/releases/releases/download/20250902/lineage-18.1-20250902-2052-r36s-android.img.zip)
   * Entpacke die ZIP-Datei, um die Datei `lineage-18.1-20250902-2052-r36s-android.img` zu erhalten.

2. **Boot-Dateien für deinen Clone (im Ordner `boot-files/` dieses Repositories):**
   * [`Image`](../boot-files/Image): Gepatchter Kernel v1.1 von K4uanGP mit Unterstützung für das Analog-Stick-Multiplexing (`amux-channel-mapping`).
   * [`rk3326-r36s-android.dtb`](../boot-files/rk3326-r36s-android.dtb): Device Tree Blob angepasst für Clone Type 2 Panel 1 mit aktiviertem Audio-Verstärker (`spk-ctl-gpios` auf GPIO3_PA7).
   * [`rg351v-kernel.dtb`](../boot-files/rg351v-kernel.dtb): Bootloader-DTB für Clones.

---

## 2. SD-Karte vorbereiten & flashen

1. **Flashen:**
   * Stecke deine microSD-Karte (mind. 16 GB, Markenkarte empfohlen) in den PC.
   * Flashe die entpackte `.img`-Datei mit **Rufus**, **BalenaEtcher** oder **Win32DiskImager**.

2. **BOOT-Partition öffnen:**
   * Nach dem Flash-Vorgang erkennt Windows die erste Partition der SD-Karte als Laufwerk namens **`BOOT`** (FAT32).
   * *Wichtig:* Falls Windows Meldungen anzeigt wie *"Laufwerk muss formatiert werden"*, klicke immer auf **Abbrechen**!

3. **Dateien auf der SD-Karte austauschen:**
   * Öffne das Laufwerk `BOOT` im Windows-Explorer.
   * Kopiere die drei Dateien aus dem Ordner [`boot-files/`](../boot-files/):
     - `Image`
     - `rk3326-r36s-android.dtb`
     - `rg351v-kernel.dtb`
   * Bestätige das Überschreiben der bestehenden Dateien.

4. **Sicher auswerfen:**
   * Werfe die SD-Karte in Windows sauber aus ("Sicher entfernen").

---

## 3. Erster Start auf dem R36S

1. Stecke die microSD-Karte in den **Slot 1 (TF1 / OS)** deines Handhelds.
2. Schalte das Gerät ein.
3. **Geduld beim ersten Boot:**
   * Der Bildschirm sollte jetzt angehen (kein Black Screen mehr).
   * Der erste Start von Android 11 dauert in der Regel **2 bis 3 Minuten**, da die Dateisysteme eingerichtet und Android-Dienste initialisiert werden.
