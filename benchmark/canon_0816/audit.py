import os, json, collections, struct, zlib
D = "/workspace/sionna/outputs/figures/atlas"
files = sorted(os.listdir(D))
print("total files:", len(files))

def png_info(p):
    try:
        with open(p,'rb') as f:
            sig = f.read(8)
            if sig != b'\x89PNG\r\n\x1a\n': return ("NOT_PNG", None, None)
            f.read(4); ctype = f.read(4)
            if ctype != b'IHDR': return ("NO_IHDR", None, None)
            w,h = struct.unpack(">II", f.read(8))
            # check IEND at tail
            f.seek(-12, os.SEEK_END)
            tail = f.read(12)
            ok = tail[4:8] == b'IEND'
            return ("OK" if ok else "TRUNCATED", w, h)
    except Exception as e:
        return ("ERR:"+str(e), None, None)

bad=[]; zero=[]
themes = collections.defaultdict(lambda: {"map":set(),"band":set(),"other":[]})
dims = {}
for fn in files:
    p = os.path.join(D, fn)
    sz = os.path.getsize(p)
    if sz == 0: zero.append(fn); continue
    st, w, h = png_info(p)
    if st != "OK": bad.append((fn, st, sz))
    dims[fn] = (w,h,sz)
    stem = fn[:-4]
    parts = stem.split("__")
    theme = parts[0]
    if len(parts)==3 and parts[2] in ("map","band"):
        themes[theme][parts[2]].add(parts[1])
    else:
        themes[theme]["other"].append(fn)

print("\nZERO-BYTE:", zero or "none")
print("BROKEN/TRUNCATED:", bad or "none")

print("\n%-14s %5s %5s %6s %6s" % ("theme","maps","bands","other","pairOK"))
allarms = {}
for t in sorted(themes):
    m = themes[t]["map"]; b = themes[t]["band"]; o = themes[t]["other"]
    allarms[t] = sorted(m | b)
    print("%-14s %5d %5d %6d   %s" % (t, len(m), len(b), len(o), "yes" if m==b else "NO"))
    if m!=b:
        print("   map-only :", sorted(m-b))
        print("   band-only:", sorted(b-m))
print("\n--- summary/compare (non-arm) files per theme ---")
for t in sorted(themes):
    for o in sorted(themes[t]["other"]): print("  ", o)

# size outliers (suspiciously small -> maybe blank fig)
print("\n--- smallest 12 files (possible blank/empty plots) ---")
for fn,(w,h,sz) in sorted(dims.items(), key=lambda kv: kv[1][2])[:12]:
    print("  %-70s %5dx%-5d %8.1f KB" % (fn, w, h, sz/1024))
print("\n--- pixel dims histogram ---")
hist = collections.Counter((w,h) for w,h,_ in dims.values())
for k,v in hist.most_common(): print("  %sx%s : %d" % (k[0],k[1],v))
