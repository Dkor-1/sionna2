# -*- coding: utf-8 -*-
"""왜 phy off 는 −30·−60 에서 성공하고, phy on 은 전 각도에서 실패하나.

가설 A — 정면은 동체 정반사가 압도적이라 «가려짐 교차항» 이 날개를 삼킨다.
         각도를 틀면 정반사가 죽어 교차항도 같이 작아진다 ⇒ 잔차가 날개가 된다.
가설 B — 회절은 «날개 자신의 모서리» 에 리듬 없는 에코를 얹는다.
         동체와 무관하므로 각도를 틀어도 안 없어진다 ⇒ 전 각도 실패.

검증 지표
  A: 통짜 요동 / 프로펠러단독 요동  (1 에 가까우면 «흔들리는 것이 곧 날개»)
     그리고 통짜의 정지(DC) 레벨 — 동체 정반사의 세기 대리값
  B: 같은 «프로펠러만» 장면을 회절 끄고/켜고 비교 — 켜면 요동이 부풀어야 한다
산출: outputs/why_angle_matters_0825.json
"""
import sys, json
import numpy as np
sys.path.insert(0, "/workspace/sionna/benchmark"); sys.path.insert(0, "/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, PRF, FFL

ELS = [0.0, -30.0, -60.0, -90.0]
ac = lambda x: np.asarray(x) - np.asarray(x).mean()
acs = lambda x: float(np.abs(ac(x)).std())
dcs = lambda x: float(np.abs(np.asarray(x)).mean())
db  = lambda v: round(float(20*np.log10(v + 1e-300)), 2)

PAIRS = [("PathSolver phy off", "sionna_p4000000000_r15_n8192_d1",
                                "sionna_p4000000000_partsprop_r15_n8192_d1"),
         ("PathSolver phy on",  "sionna_p4000000000_phys_r15_n8192_d1",
                                "sionna_p4000000000_phys_partsprop_r15_n8192_d1"),
         ("SBR + PO (ours)",    "ours_r15_n8192", "ours_free_r15_n8192")]

out = {"_meta": {"작성": "2026-08-25", "가설A": "정면 동체 정반사가 교차항을 키운다",
                 "가설B": "회절이 날개 자신에 리듬 없는 에코를 얹는다"}, "A": {}, "B": {}}

print("=== 가설 A · 흔들리는 것이 «곧 날개» 인가 ===")
print("   통짜요동/프로펠러요동 이 1 에 가까울수록 «흔들림 = 날개» → 필터가 성공한다\n")
h=f"{'앙각':>6} {'엔진':20}{'통짜 AC':>10}{'프로펠 AC':>11}{'비(배)':>12}{'통짜 DC':>10}"
print(h); print("-"*len(h))
for el in ELS:
    for nm, aw, ap in PAIRS:
        W,_ = load(aw, el); P,_ = load(ap, el)
        if W is None or P is None: continue
        r = acs(W)/acs(P) if acs(P) > 0 else float("inf")
        out["A"][f"{el:+.0f}|{nm}"] = dict(whole_ac_db=db(acs(W)), prop_ac_db=db(acs(P)),
                                           ratio=round(r,2), whole_dc_db=db(dcs(W)))
        print(f"{el:+6.0f} {nm:20}{db(acs(W)):10.2f}{db(acs(P)):11.2f}{r:12.1f}{db(dcs(W)):10.2f}")
    print()

print("=== 가설 B · 회절이 «날개 자신» 을 흐리는가 (동체 없는 장면) ===")
print("   같은 프로펠러만 장면을 회절 끄고/켜고 비교한다\n")
h2=f"{'앙각':>6}{'회절 끔 AC':>12}{'회절 켬 AC':>12}{'켜서 늘어난 양':>14}{'리듬 대비 끔':>13}{'켬':>9}"
print(h2); print("-"*len(h2))
FT0 = 1101.6/np.cos(np.radians(-30.0))
def comb_db(E, el):
    x=ac(E); n=x.size
    Pw=np.abs(np.fft.fft(x*np.hanning(n)))**2; fr=np.fft.fftfreq(n,1.0/PRF)
    ft=FT0*np.cos(np.radians(el)); m=np.abs(fr)>=ft
    if not m.any() or Pw[m].sum()<=0: return None
    k=np.round(np.abs(fr)/FFL); on=m&(np.abs(np.abs(fr)-k*FFL)<=8.0)
    if not on.any() or not (m&~on).any(): return None
    return round(float(10*np.log10(Pw[on].mean()/Pw[m&~on].mean())),2)
for el in ELS:
    Po,_ = load("sionna_p4000000000_partsprop_r15_n8192_d1", el)
    Pn,_ = load("sionna_p4000000000_phys_partsprop_r15_n8192_d1", el)
    if Po is None or Pn is None: continue
    g = db(acs(Pn)) - db(acs(Po))
    co, cn = comb_db(Po, el), comb_db(Pn, el)
    out["B"][f"{el:+.0f}"] = dict(prop_off_ac_db=db(acs(Po)), prop_on_ac_db=db(acs(Pn)),
                                  gain_db=round(g,2), comb_db_off=co, comb_db_on=cn)
    print(f"{el:+6.0f}{db(acs(Po)):12.2f}{db(acs(Pn)):12.2f}{g:+14.2f}"
          f"{(co if co is not None else float('nan')):13.2f}{(cn if cn is not None else float('nan')):9.2f}")
json.dump(out, open("/workspace/sionna/outputs/why_angle_matters_0825.json","w",
                    encoding="utf-8"), ensure_ascii=False, indent=2)
print("\n→ outputs/why_angle_matters_0825.json")
