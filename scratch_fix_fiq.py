with open('build_lineage_dtb.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update fiq-debugger and serial@ff160000
old_block = '''    # Neutralize UART2 and FIQ-Debugger conflict on GPIO2 pin 14 (BTN_THUMBR)
    # Matches ArkOS and factory firmware rf3536k3ka.dtb where serial@ff160000 is disabled
    try:
        serial2 = dt419.get_node("/serial@ff160000")
        set_prop_safe(serial2, fdt.PropStrings("status", "disabled"))
        print("    [-] Disabled /serial@ff160000 (freed GPIO2 pin 14 for joypad BTN_THUMBR)")
    except Exception as e:
        print("    [!] /serial@ff160000 not found:", e)

    try:
        fiq = dt419.get_node("/fiq-debugger")
        set_prop_safe(fiq, fdt.PropStrings("status", "disabled"))
        if fiq.get_property("pinctrl-0"):
            fiq.remove_property("pinctrl-0")
        print("    [-] Disabled /fiq-debugger and removed pinctrl (freed GPIO2 pin 14 for joypad BTN_THUMBR)")
    except Exception as e:
        print("    [!] /fiq-debugger not found:", e)'''

new_block = '''    # Reconfigure FIQ-Debugger to UART5 and disable serial@ff160000
    # Exactly matching factory firmware (rf3536k3ka.dtb) and ArkOS (arkos_clone_type2.dtb)
    # This keeps fiq-debugger active (preventing kernel panic) while freeing GPIO2 pin 14 for joypad!
    try:
        serial2 = dt419.get_node("/serial@ff160000")
        set_prop_safe(serial2, fdt.PropStrings("status", "disabled"))
        print("    [-] Disabled /serial@ff160000 (freed GPIO2 pin 14)")
    except Exception as e:
        print("    [!] /serial@ff160000 not found:", e)

    try:
        fiq = dt419.get_node("/fiq-debugger")
        set_prop_safe(fiq, fdt.PropStrings("status", "okay"))
        set_prop_safe(fiq, fdt.PropWords("rockchip,serial-id", 5)) # UART5 matching factory DTB
        set_prop_safe(fiq, fdt.PropWords("pinctrl-0", 77)) # uart5_xfer matching factory DTB
        print("    [+] Configured /fiq-debugger on UART5 (phandle 77, freed GPIO2 pin 14!)")
    except Exception as e:
        print("    [!] /fiq-debugger not found:", e)'''

assert old_block in content, "old_block not found in build_lineage_dtb.py"
content = content.replace(old_block, new_block, 1)

# Update assertion
content = content.replace(
    'assert dt_val.get_node("/fiq-debugger").get_property("status").value == "disabled"',
    'assert dt_val.get_node("/fiq-debugger").get_property("status").value == "okay"\\n    assert dt_val.get_node("/fiq-debugger").get_property("rockchip,serial-id").data == [5]'
)

with open('build_lineage_dtb.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated build_lineage_dtb.py successfully!")
