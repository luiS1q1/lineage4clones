with open('build_lineage_dtb.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'assert dt_val.get_node("/fiq-debugger").get_property("status").value == "okay"' in line:
        new_lines.append('    assert dt_val.get_node("/fiq-debugger").get_property("status").value == "okay"\n')
        new_lines.append('    assert dt_val.get_node("/fiq-debugger").get_property("rockchip,serial-id").data == [5]\n')
    else:
        new_lines.append(line)

with open('build_lineage_dtb.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed line 566!")
