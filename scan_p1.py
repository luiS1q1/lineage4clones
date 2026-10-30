import lzma, struct

xz_path = r"C:\Users\luism\Downloads\dArkOS4Clone-20261008.img.xz"
with lzma.open(xz_path, "rb") as f:
    f.seek(32768 * 512)
    p1 = f.read(524288 * 512)

bytes_per_sec = struct.unpack("<H", p1[11:13])[0]
sec_per_clus = p1[13]
reserved_sec = struct.unpack("<H", p1[14:16])[0]
num_fats = p1[16]
sec_per_fat = struct.unpack("<I", p1[36:40])[0]
root_cluster = struct.unpack("<I", p1[44:48])[0]

fat_start = reserved_sec * bytes_per_sec
data_start = (reserved_sec + num_fats * sec_per_fat) * bytes_per_sec
clus_size = sec_per_clus * bytes_per_sec

def get_fat_entry(clus):
    offset = fat_start + clus * 4
    return struct.unpack("<I", p1[offset:offset+4])[0] & 0x0fffffff

def read_cluster_chain(start_clus):
    chain = []
    curr = start_clus
    while curr < 0x0ffffff8 and curr >= 2:
        chain.append(curr)
        curr = get_fat_entry(curr)
    return chain

root_chain = read_cluster_chain(root_cluster)
print("Root cluster chain length:", len(root_chain))

for clus in root_chain:
    c_offset = data_start + (clus - 2) * clus_size
    dir_data = p1[c_offset:c_offset + clus_size]
    for i in range(0, len(dir_data), 32):
        e = dir_data[i:i+32]
        if e[0] == 0:
            continue
        if e[0] == 0xe5:
            continue
        name = e[0:11].decode("latin1", errors="ignore")
        attr = e[11]
        size = struct.unpack("<I", e[28:32])[0]
        c = (struct.unpack("<H", e[20:22])[0] << 16) | struct.unpack("<H", e[26:28])[0]
        print(f"attr=0x{attr:02x} {size:10} clus={c}: {repr(name)}")
