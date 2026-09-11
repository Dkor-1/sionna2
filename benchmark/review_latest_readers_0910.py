"""Rebuild a bounded audit of current readers from stored data, using one CPU.

Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_latest_readers_0910.py
No ray solver is imported; production readers, ledgers and presentation files stay untouched.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['OPENBLAS_NUM_THREADS'] = '1'
if hasattr(os, 'sched_setaffinity'):
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
import ast
import glob
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SHD = ROOT/'outputs/elev_sweep_shards'
OUT = ROOT/'outputs/latest_readers_review_0910.json'
MEMO = ROOT/'docs/LATEST_READERS_REVIEW_0910.md'
NB = MEMO.with_suffix('.ipynb')
PLOT = ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py'
HASHES, CACHE = {}, {}


def digest(p):
    p = Path(p)
    if not p.is_absolute(): p = ROOT/p
    key = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    if key not in HASHES:
        with p.open('rb') as f: HASHES[key] = hashlib.file_digest(f, 'sha256').hexdigest()
    return p


def read(p): return digest(p).read_text()
def js(p): return json.loads(read(p))


def source(p, needle):
    lines = read(p).splitlines()
    i = next((i for i,s in enumerate(lines,1) if needle in s), None)
    return dict(path=str(p), line=i, quote=lines[i-1].strip() if i else needle,
                found=i is not None)


def functions(p, names, ns):
    nodes = [n for n in ast.parse(read(p)).body
             if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(nodes) == len(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
    return ns


def load(files):
    paths = tuple(sorted(SHD/Path(f).name for f in files))
    if paths in CACHE: return CACHE[paths]
    assert paths
    ii, ee, pp, dd, rr, metas, trs = [],[],[],[],[],[],[]
    for p in paths:
        digest(p)
        with np.load(p,allow_pickle=False) as z:
            i=z['idx']; ii.append(i); ee.append(z['E']); metas.append(z['meta'].tolist())
            pp.append(z['npaths'] if 'npaths' in z else np.full(i.shape,-1))
            dd.append(z['n_dup'] if 'n_dup' in z else np.full(i.shape,-1))
            rr.append(z['nret'] if 'nret' in z else np.full(i.shape,-1))
            trs.append(z['n_trunc'].tolist() if 'n_trunc' in z else None)
    ii=np.concatenate(ii); order=np.argsort(ii); N=int(metas[0][3])
    assert all(int(m[3])==N and m[4]==metas[0][4] and m[0]==metas[0][0] for m in metas)
    assert np.array_equal(ii[order],np.arange(N)), [p.name for p in paths]
    assert np.isfinite(np.concatenate(ee)).all()
    out=dict(E=np.concatenate(ee)[order], idx=ii[order], n=N, prf=metas[0][4], el=metas[0][0],
             P=np.concatenate(pp)[order], D=np.concatenate(dd)[order], R=np.concatenate(rr)[order],
             trunc=trs, files=[p.name for p in paths])
    CACHE[paths]=out
    return out


def by_stem(stem,el): return load(list(SHD.glob(f'{stem}_el{el:+g}_*.npz')))


def flag(F,O):
    assert F['prf']==O['prf'] and np.array_equal(F['idx'],O['idx'])
    d=O['E']-F['E']; c=complex(np.median(d.real),np.median(d.imag))
    return abs(d-c)>.5*abs(c)


def overlap(a,b):
    I=int((a&b).sum()); U=int((a|b).sum())
    return dict(n_base=int(a.sum()),n_other=int(b.sum()),intersection=I,union=U,
                jaccard=I/U if U else None,lost=np.flatnonzero(a&~b).tolist(),
                added=np.flatnonzero(~a&b).tolist(),symmetric_difference=int((a!=b).sum()))


def body_check():
    ledger=js('outputs/read_bodyladder_0910.json'); masks={}; data={}
    for row in ledger['rows']:
        label=row['cell']; spp=4_000_000_000; tail=''
        if label.startswith('동체'):
            bs=float(label.split('×')[1]);tail=f'_bs{bs:g}' if bs!=1 else ''
        else: spp=int(float(label.split()[1]))
        stem=f'sionna_p{spp}_swR0D0E0F1_r15_n8192'
        suffix=tail+'_mfixbatteryi5_blperairframe_d2'
        F=by_stem(stem+suffix,-60); O=by_stem(stem+'_envoutdoor01_ground'+suffix,-60)
        masks[label]=flag(F,O);data[label]=dict(files_free=F['files'],files_scene=O['files'])
    base=masks['동체 ×1'];base_pairs={}
    for row in ledger['rows']:
        label=row['cell'];p=overlap(base,masks[label]);base_pairs[label]=p
        assert p['n_other']==row['n_events'] and p['intersection']==row['kept_of_base']
        assert round(p['jaccard'],4)==row['jaccard']
    direct={}
    for label in ('동체 ×0.4','동체 ×0.5','동체 ×0.6','동체 ×0.8'):
        direct[label]={grid:overlap(masks[label],masks[grid]) for grid in ('격자 3.8e9','격자 4.2e9')}
    return dict(condition=dict(drone='matrice4e',scene='outdoor01_ground',el_deg=-60,range_m=15,
                n_poses=int(base.size),prf_hz=F['prf'],depth=2,arm='R0D0E0F1',dev=.5),
                baseline_event_indices=np.flatnonzero(base).tolist(),pairs_to_base=base_pairs,
                direct_body_vs_budget=direct,files=data)


def canyon_check():
    ledger=js('outputs/read_canyonnull_0910.json')
    hampel=functions(PLOT,['hampel_mask'],dict(np=np))['hampel_mask']
    masks={};actual={};rates={};diagnostics=[]
    for el,group in ledger['by_el'].items():
        masks[el]={};actual[el]={}
        for label,row in group['cells'].items():
            O=load(row['files_scene'])
            F=load([f.replace('_envsionna-simple_street_canyon','') for f in row['files_scene']])
            masks[el][label]=hampel(abs(O['E']),51,5.)
            f=flag(F,O)
            assert int(f.sum())==row['n_static_changed']
            published=ledger['deck_rule_hampel'][el][label]
            assert int(masks[el][label].sum())==published['n_mask']
            for role,c in [('scene',O),('free',F)]:
                diagnostics.append(dict(el_deg=float(el),cell=label,role=role,files=c['files'],
                    n_trunc_by_shard=c['trunc'],n_dup_unknown=int((c['D']<0).sum()),
                    nret_unknown=int((c['R']<0).sum()),max_nret=int(c['R'].max()),
                    published_trunc_outdoor=row['trunc_outdoor'] if role=='scene' else None))
            actual[el][label]=dict(n_events=int(f.sum()),n_hampel=int(masks[el][label].sum()),
                files_scene=O['files'],files_free=F['files'])
        base=masks[el]['기준선 (4e9)']; rates[el]={}
        for label,m in masks[el].items():
            p=overlap(base,m);n=base.size
            assert round(p['jaccard'],4)==ledger['deck_rule_hampel'][el][label]['jaccard']
            p.update(lost_pct_of_baseline=100*len(p['lost'])/p['n_base'],
                     symmetric_difference_pct_of_union=100*p['symmetric_difference']/p['union'],
                     symmetric_difference_pct_of_all=100*p['symmetric_difference']/n,n_poses=n)
            rates[el][label]=p
    tr=[t for d in diagnostics for t in d['n_trunc_by_shard'] if t is not None]
    return dict(condition=ledger['_meta'],hampel=dict(win=51,k=5.),cells=actual,pairs=rates,
                diagnostics=diagnostics,n_published_cells=sum(map(len,actual.values())),
                recorded_near_cap_events=sum(t[0] for t in tr),missing_diagnostic_shards=sum(
                    t is None for d in diagnostics for t in d['n_trunc_by_shard']),
                max_returned_paths=max(d['max_nret'] for d in diagnostics),
                scope='Published file lists only; later queue results are not added.')


def atlas_check():
    j=js('outputs/md_atlas_index.json'); m=j['_meta'];sys.path.insert(0,str(ROOT/'src'))
    digest('src/drones.py');digest('src/articulated_fast.py')
    from drones import DRONES
    ns=dict(np=np,math=math,DRONES=DRONES,DRONE_DEFAULT=m['drone_default'],C_LIGHT=2.998e8,
            FC=m['fc_hz'],PRF=m['prf_hz'],RHY_HW=8.)
    # ⛔2026-09-11 — arm_rates 가 prop_scale_tag 를 부르게 바뀌어(R30 보정) 추출 목록에 없으면
    #   NameError 로 죽는다. 없던 시절에도 돌게 기본값을 함께 넣는다.
    ns.setdefault('re', re); ns.setdefault('prop_scale_tag', lambda _a: 1.0)
    functions('benchmark/build_md_atlas.py',
              ['airframe_tag','prop_scale_tag','arm_rates','f_tip_at',
               'comb_contrast_db','rhythm_share'],ns)
    # ⭐⭐**배율이 이미 들어갔는지 먼저 잰다.** 안 재고 ft*ps 를 하면 보정된 코드에서 **두 번**
    #   곱한다(R30 뒤의 실제 위험). 기준 기체·배율 없는 팔의 f_tip0 과 견줘 판정한다.
    _probe = 'ours_r15_n8192_ps2_mfixbatteryi5_blperairframe'
    _base_tip = ns['arm_rates']('ours_r15_n8192_mfixbatteryi5_blperairframe')['f_tip0_hz']
    _ps_applied = abs(ns['arm_rates'](_probe)['f_tip0_hz'] - 2.0*_base_tip) < 1e-6
    digest('outputs/elevation_sweep_md.npz'); rows=[]; arms=[]
    with np.load(ROOT/'outputs/elevation_sweep_md.npz',allow_pickle=False) as z:
        for topic,t in j['topics'].items():
            for arm,a in t['arms'].items():
                match=re.search(r'_ps([0-9.]+)',arm)
                if not match or float(match[1])==1: continue
                ps=float(match[1]);arms.append(arm);rates=ns['arm_rates'](arm);ff=rates['f_flash_hz']
                for el,c in a['cells'].items():
                    ft=ns['f_tip_at'](rates,float(el))
                    # ⭐보정 뒤에는 ft 가 이미 배율을 담고 있다 — 다시 곱하지 않는다.
                    correct=ft if _ps_applied else ft*ps
                    assert round(ft,1)==c['f_tip_hz'], (arm,el,ft,c['f_tip_hz'])
                    row=dict(topic=topic,arm=arm,el_deg=float(el),prop_scale=ps,
                             current_tip_hz=ft,scaled_tip_hz=correct,
                             published_tip_hz=c['f_tip_hz'],f_flash_hz=ff,
                             complete=not c['incomplete'],n_poses=c['n_poses'])
                    if not any(c[k] for k in ['incomplete','no_return','no_motion']):
                        E=z[f'{arm}/el{float(el):+.0f}'];assert np.isfinite(E).all()
                        old=ns['comb_contrast_db'](E,ff,ft);new=ns['comb_contrast_db'](E,ff,correct)
                        if old is not None:
                            assert abs(old-c['outlier']['base']['comb_db'])<.0001
                        row.update(comb_db_current=old,comb_db_scaled=new,
                                   rhythm_current=list(ns['rhythm_share'](E,ff,ft)),
                                   rhythm_scaled=list(ns['rhythm_share'](E,ff,correct)))
                    rows.append(row)
    sample=next(r for r in rows if r['arm']=='ours_r15_n8192_ps0.7_fs0.7_mfixbatteryi5_blperairframe' and r['el_deg']==0)
    return dict(fc_hz=m['fc_hz'],prf_hz=m['prf_hz'],n_tagged_arms=len(arms),n_tagged_cells=len(rows),
                n_eligible_cells=sum('comb_db_current' in r for r in rows),sample=sample,cells=rows,
                prop_scale_applied=_ps_applied,
                mode=('regression' if _ps_applied else 'pre_fix_audit'),
                mode_note_ko=(
                    '⭐regression — build_md_atlas.arm_rates 가 _ps 를 이미 곱한다(R30 보정 반영). '
                    'current 와 scaled 가 같은 값이고, 이 칸은 «보정이 살아 있나» 를 지키는 '
                    '회귀 검사다. ⛔여기서 ft 에 배율을 다시 곱하면 두 번 적용된다.'
                    if _ps_applied else
                    'pre_fix_audit — arm_rates 가 아직 _ps 를 안 곱한다. current 는 발간값이고 '
                    'scaled 는 배율을 반영했을 때의 값이다(정정 전 상태를 재현한다).'),
                scope='Current atlas kinematic reference band, same saved E and same metric functions; '
                      'not a hard physical support bound or a new ray simulation. Incomplete cells stay excluded.')


def adversarial_check():
    # ⛔2026-09-11 — _trunc_of 는 CAP 을 쓰던 자리가 있었다. 새 판은 샤드의 상한을 읽지만
    #   옛 판도 돌게 규약값을 함께 준다.
    ns=functions('benchmark/read_canyonnull_0910.py',['_trunc_of','load'],
                 dict(np=np,glob=glob,os=os,CAP=2_000_000))
    ms=functions('benchmark/read_0918B_0909.py',['db','measure'],dict(np=np,DEV=.5,CAP=2_000_000))
    ds=functions('benchmark/read_dropladder_0910.py',['_copies_txt','cell'],dict(np=np,glob=glob,os=os,
        RNG=15,NPOSE=8192,MESH='mfixbatteryi5_blperairframe',DEPTH=2,EL=0))
    with tempfile.TemporaryDirectory(prefix='sionna-reader-audit-') as tmp:
        ns['SHD']=ds['SHD']=tmp;N=8192
        for shard in range(2):
            idx=np.arange(shard,N,2);badidx=np.arange(0,N,2)
            p=np.full(len(idx),10);p[0]=2_000_000 if shard==0 else 10
            for name,ii in [('free',idx),('duplicate_scene',badidx)]:
                np.savez(Path(tmp)/f'{name}_el-60_{shard:02d}.npz',idx=ii,E=np.full(len(ii),1.+0j),
                         npaths=p,n_dup=np.zeros(len(ii),int),nret=p,
                         n_trunc=np.array([1 if shard==0 else 0,2_000_000]))
            name=f'sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2_el+0_{shard:02d}.npz'
            kw=dict(idx=idx,E=np.ones(len(idx),complex),npaths=np.full(len(idx),10))
            if shard==0: kw['n_dup']=np.full(len(idx),2)
            np.savez(Path(tmp)/name,**kw)
        F,nf=ns['load']('free',-60);O,no=ns['load']('duplicate_scene',-60)
        r=ms['measure'](F,O)
        # ⚠옛 관문(길이·샤드 수만) — 이것이 결함을 낳던 경로다
        accepted=nf>=2 and no>=2 and F['E'].size==O['E'].size and r is not None
        # ⭐⭐2026-09-11 — **고친 관문**도 함께 잰다. 위 것만 재면 고친 뒤에도 «결함이 남았다» 로
        #   찍힌다(고친 자리는 부르는 쪽의 idx_ok 게이트인데 반례가 그것을 안 봤다).
        gated=bool(accepted and F.get('idx_ok') and O.get('idx_ok'))
        c=ds['cell']('R0D0E0F1',4_000_000_000);D=c['D'];unknown=int((D<0).sum())
        # ⛔⛔2026-09-11 — 전에는 여기서 **정답식을 제 손으로 다시 짰다**(`have&(D<2)`).
        #   그러면 생산 코드가 옛 오류로 되돌아가도 이 검사는 «고쳐졌다» 로 찍힌다
        #   (검토자가 메모리에서 되돌려 실증했다: 오집계 0 → 4,096 인데 판정은 그대로).
        #   ⇒ **생산 main() 을 그대로 돌려** 그 결과를 읽는다. 검사는 답을 알면 안 된다.
        short_fixed, prod_ran = None, False
        try:
            import importlib, json as _json, io, contextlib
            _rd = importlib.import_module('read_dropladder_0910')
            importlib.reload(_rd)
            _rd.SHD = tmp                      # 합성 창고를 보게 한다
            _rd.OUT = os.path.join(tmp, '_probe_dropladder.json')
            with contextlib.redirect_stdout(io.StringIO()):
                _rd.main()
            _pj = _json.load(open(_rd.OUT, encoding='utf-8'))
            _row = next((r for r in _pj.get('rows', [])
                         if r['arm']=='R0D0E0F1' and r['spp']==4_000_000_000), None)
            short_fixed = _row['n_short'] if _row else None
            prod_ran = True
            prod_skipped = _pj.get('_meta', {}).get('skipped', [])
        except Exception as _e:                                   # noqa: BLE001
            prod_err = f"{type(_e).__name__}: {_e}"; prod_skipped = []
        result=dict(kind='Synthetic fixtures passed to AST-extracted current functions; not observed data corruption.',
                    n_declared=N,n_scene_unique_indices=N//2,
                    equal_length_duplicate_index_accepted=bool(accepted),
                    accepted_through_fixed_gate=gated,
                    load_reports_idx_ok=dict(free=F.get('idx_ok'),scene=O.get('idx_ok')),
                    synthetic_recorded_near_cap_events=1,returned_trunc=r['trunc_outdoor'],
                    returned_at_path_cap=r['at_path_cap'],
                    recomputed_poses_near_cap=r.get('n_poses_near_cap_now'),
                    shards_without_cap_diag=r.get('n_shards_without_cap_diag'),
                    mixed_dup_unknown=unknown,mixed_dup_counted_short=int((D<2).sum()),
                    # ⭐생산 main() 이 실제로 실은 수. ⛔검토 코드가 다시 계산한 값이 아니다.
                    mixed_dup_counted_short_fixed=short_fixed,
                    production_main_ran=prod_ran,
                    production_skipped=prod_skipped,
                    production_probe_note_ko=(
                        "n_short 는 read_dropladder_0910.main() 을 합성 창고에 대고 실제로 "
                        "돌려 원장에서 읽은 값이다. ⛔검토 코드가 정답을 다시 계산하면 생산 "
                        "코드의 회귀를 못 잡는다(2026-09-11 검토자 실증)."),
                    mixed_dup_is_skipped=bool((D<0).all()))
    # ⛔⛔2026-09-11 — 여기 있던 assert 넷은 «결함이 **있다**» 를 단정했다. 2026-09-10/11 에
    #   그 넷을 고쳤으므로 단정이 그대로면 이 빌더가 죽는다(실제로 죽었다).
    #   ⇒ 단정을 **상태 기록**으로 바꾼다. 고쳐졌으면 고쳐졌다고 적고, 되살아나면 그것도 적는다.
    #   ⛔«고쳐졌다» 를 여기서 «검증됐다» 로 읽지 않는다 — 합성 입력 네 가지에 대한 관찰이다.
    # ⭐판정은 **고친 자리**를 본다. 옛 경로의 값은 위 raw 필드에 그대로 남겨 둔다.
    result['defects_still_present']=dict(
        # 중복 인덱스 칸이 고친 관문을 그대로 통과하는가
        equal_length_duplicate_index_accepted=bool(result['accepted_through_fixed_gate']),
        # 상한 진단이 버려지는가 — 이제 measure 가 다시 센 수를 들고 온다
        trunc_diagnostic_dropped=bool(result['recomputed_poses_near_cap'] is None
                                      and result['returned_trunc']==[]),
        # 드문 자세의 상한 근접을 못 잡는가
        median_only_cap_flag=bool((result['recomputed_poses_near_cap'] or 0) <
                                  result['synthetic_recorded_near_cap_events']),
        # 미계측(−1)을 «줄<3» 으로 세는가
        # ⛔생산 main() 이 안 돌았으면 «고쳐졌다» 로 찍지 않는다 — 모르는 것은 모른다고 둔다
        unknown_dup_counted_as_short=(None if not result['production_main_ran'] else
                                      bool(result['mixed_dup_counted_short_fixed']==unknown
                                           and unknown > 0)))
    _d=result['defects_still_present']
    result['n_defects_still_present']=sum(1 for v in _d.values() if v is True)
    result['n_unknown']=sum(1 for v in _d.values() if v is None)
    result['status_ko']=(
        ('아직 남은 것: '+', '.join(k for k,v in _d.items() if v is True)) if result['n_defects_still_present']
        else (f"네 결함이 합성 입력에서 안 재현된다 (⚠못 잰 것 {result['n_unknown']} 개 — "
              "생산 main() 을 못 돌렸다)") if result['n_unknown']
        else '네 결함이 모두 고쳐졌다 — 생산 main() 을 합성 창고에 대고 돌려 확인했다')
    return result


def drop_check():
    j=js('outputs/read_dropladder_0910.json');rows=[]
    for row in j['rows']:
        c=load(row['files']); short=c['D']<2; dip=abs(c['E'])/np.median(abs(c['E']))<.9
        assert int(short.sum())==row['n_short'] and int(dip.sum())==row['n_dip']
        rows.append(dict(arm=row['arm'],spp=row['spp'],n=c['n'],unknown_dup=int((c['D']<0).sum()),
                         n_short=int(short.sum()),n_dip=int(dip.sum()),files=c['files']))
    return dict(rows=rows,n_rows=len(rows),unknown_dup=sum(r['unknown_dup'] for r in rows))


def findings(c):
    fs=[]
    # ⛔⛔2026-09-11 — 전에는 제목·본문이 «결함이 있다» 로 고정이라, 고쳐진 뒤에도 보고서가
    #   옛 결함을 그대로 재발행했다(검토자 지적: mode=regression 인데 제목은 «반영되지 않았다»).
    #   ⇒ 측정된 현재 상태(`fixed`)를 받아 **제목·본문·수정 제안에 모두** 싣는다.
    #   ⛔fixed=None 은 «못 쟀다» 다 — «고쳐졌다» 로 쓰지 않는다.
    def add(title,status,issue,evidence,replacement,followup,refs,fixed=None,fixed_note=''):
        if fixed is True:
            title = '[고쳐짐] ' + title
            status = f"{status} · ⭐현재 코드에서는 재현되지 않는다"
            issue = ('⭐**이 지적은 고쳐졌다**(2026-09-11 측정). ' + (fixed_note + ' ' if fixed_note else '')
                     + '아래는 지적 당시의 문면이고 기록으로 남긴다 — 그대로 인용하면 틀린다.\n\n' + issue)
            followup = '⭐수정이 이미 들어갔다. 되살아나지 않는지 회귀 검사로만 지킨다. (옛 제안: ' + followup + ')'
        elif fixed is False:
            title = '[남음] ' + title
            status = f"{status} · ⛔현재 코드에서도 재현된다"
        fs.append(dict(title=title,status=status,issue=issue,evidence=evidence,
                       replacement=replacement,followup=followup,
                       fixed=fixed,fixed_note_ko=fixed_note or None,
                       sources=[source(p,n) for p,n in refs]))
    a=c['atlas'];s=a['sample']
    add('별도 분석기에서 고친 프로펠러 대역이 발간 아틀라스에는 반영되지 않았다','현재 발간값의 수치 영향 확인',
        'comb_snr의 배율 보정을 고쳐도 build_md_atlas.arm_rates는 기본 기체 지름을 사용한다. 아틀라스를 다시 굽는 작업만으로 이 계산식은 바뀌지 않는다.',
        f"현재 아틀라스의 비단위 _ps 태그 {a['n_tagged_arms']}개 팔·{a['n_tagged_cells']}개 칸을 확인했다. "
        f"완전성 등 기존 자격 조건을 통과한 {a['n_eligible_cells']}개 칸만 지표를 재계산했다. "
        f"예: {s['arm']}, el {s['el_deg']:g}°, {a['fc_hz']/1e9:g} GHz, {s['n_poses']}표본에서 "
        f"운동학적 기준 대역 끝은 {s['current_tip_hz']:.4f} → {s['scaled_tip_hz']:.4f} Hz, "
        f"같은 신호의 빗살 대비는 {s['comb_db_current']:.6f} → {s['comb_db_scaled']:.6f} dB다. "
        '원신호 변화·솔버 오차 크기를 측정한 것이 아니다. 프레임 배율은 회전 반경 배율을 대신하지 않는다. 이 기준선을 물리 스펙트럼의 엄밀한 지지집합 경계로 해석하지 않는다.'
        + (f" ⭐2026-09-11 재측정: build_md_atlas.arm_rates 가 _ps 를 곱한다(mode={a['mode']}) — "
           f"발간 색인도 {s['published_tip_hz']:g} Hz 로 다시 구워졌고 current 와 scaled 가 같다."
           if a.get('prop_scale_applied') else ''),
        '프로펠러 배율을 반영한 운동학적 기준 대역에서 지표를 다시 계산하고, 해당 지도·대역 그래프·목차·영향 진단을 함께 재생성해야 한다.',
        '공통 arm 조건 해석 함수로 지름·회전수·주파수·앙각을 정하고, 변경된 기준을 사용하는 발간 경로를 확인한다.',
        fixed=bool(a.get('prop_scale_applied')),
        fixed_note='철회 기록 R30 · build_md_atlas.py 의 prop_scale_tag() 로 고쳤고 아틀라스를 다시 구웠다.',
        refs=[('benchmark/build_md_atlas.py','ftip0 = 2.0'),('benchmark/comb_snr.py','* (blade_of(arm) / F0) * _ps)'),
         ('src/articulated_fast.py','prop_scale 에만 비례한다')])
    b=c['body'];p=b['pairs_to_base'];direct=b['direct_body_vs_budget']['동체 ×0.4']
    add('기준 사건이 같은 수만큼 남았다는 것이 같은 집합이라는 뜻은 아니다','원본 사건 인덱스로 확인',
        '새 작업 설계는 동체 축소와 예산 변경이 같은 수를 남긴다는 이유로 구별되지 않는다고 쓴다. 이 요약값만 같고 사건의 정체와 새 사건 수는 다르다.',
        f"조건은 {b['condition']}이다. 동체 ×0.4의 기준 사건 탈락 인덱스는 {p['동체 ×0.4']['lost']}, "
        f"격자 3.8e9는 {p['격자 3.8e9']['lost']}, 4.2e9는 {p['격자 4.2e9']['lost']}다. "
        f"세 조건은 기준 사건 {p['동체 ×1']['n_base']}개 중 각각 {p['동체 ×0.4']['intersection']}개를 남겼다. "
        f"동체 ×0.4와 두 예산 조건의 전체 사건 대칭차는 각각 {direct['격자 3.8e9']['symmetric_difference']}개, "
        f"{direct['격자 4.2e9']['symmetric_difference']}개다. 인덱스는 0부터 시작한다. "
        '이는 사건 집합의 불일치이며, 물리 기전 차이나 통계적 유의성의 증명은 아니다.',
        '동체 축소와 예산 변경에서 기준 사건 잔존 개수는 같았지만, 잃은 사건과 새로 생긴 사건의 목록은 달랐다. 원인 구분에는 추가 대조가 필요하다.',
        '잔존 개수와 함께 lost/added 인덱스, 직접 교집합, 각 사건의 연속 잔차 크기를 보존한다.',
        [('runners/make_jobs_0924.py','구별되지 않는다'),('benchmark/read_bodyladder_0910.py','"kept_of_base": inter')])
    add('민감도 참고값을 다른 기체의 판정 문턱으로 올리는 문장이 다시 남았다','최신 설계·재개 문서의 지시 충돌',
        '협곡 판독기는 예산 변경이 신뢰구간이 아니라고 명시하지만 재개 문서는 두 앙각의 값을 한 띠로 묶고 이제 기체 교체를 판정할 수 있다고 쓴다. 작업 생성기에도 널 띠 판정과 직접 비교 금지가 같은 블록에 공존한다.',
        '판독기의 조건별 표와 경고는 올바른 방향이다. 그러나 앙각을 합친 최솟값·최댓값은 같은 조건의 확률 분포가 아니다. '
        '서로 다른 회전수에서 같은 시간 인덱스의 겹침은 계산할 수 있지만, 같은 로터 자세에서의 형상 효과를 분리하는 지표가 되지는 않는다. '
        '기체 교체가 실제로 수행한 비교에서 이미 잘못 결론 났다고 주장하는 것이 아니라, 실행 후 판정 지시의 모순을 지적한다.',
        '예산 변경에서 관측한 사건 겹침은 앙각별 민감도 참고값으로 둔다. 기체 교체의 같은 시각 겹침은 회전 위상 차이를 포함하므로 형상 효과의 판정 문턱으로 쓰지 않는다.',
        '0923C의 폐기 조건과 재개 문서를 함께 정리한다. 시간 기준 질문인지 위상 기준 질문인지 먼저 정하고, 주기·허브·회전수·반복 조건을 명시한다.',
        [('benchmark/read_canyonnull_0910.py','두 점은 신뢰구간이 아니다'),
         ('work/sweep_0904/RESUME_0911.md','문턱이 훨씬 느슨하다'),
         ('runners/make_jobs_0923.py','죽는조건  협곡에서 mini5pro'),
         ('runners/make_jobs_0923.py','이 짝은 자세 집합을 직접 못 견준다')])
    rows=[v for k,v in c['canyon']['pairs']['-60'].items() if k.startswith('격자')]
    add('자카드의 보수를 기준 사건의 교체율로 풀어 쓰면 분모가 달라진다','현재 원장 설명의 분모 누락',
        '“자세 다섯 중 하나쯤이 다른 자세”는 자카드의 보수를 어떤 모집단의 비율로 설명했는지 빠져 있다. 합집합의 비공통 몫과 기준 집합에서 사라진 몫은 서로 다르다.',
        '거리 협곡·matrice4e·15 m·el −60°·깊이 2·R0D0E0F1·Hampel(win=51,k=5.0), '
        + ' '.join(f"예산 대조 {i+1}: 기준 {v['n_base']}개, 새 조건 {v['n_other']}개, 공통 {v['intersection']}개, "
          f"합집합 {v['union']}개다. 기준 탈락은 {len(v['lost'])}/{v['n_base']}={v['lost_pct_of_baseline']:.3f}%, "
          f"합집합 비공통은 {v['symmetric_difference']}/{v['union']}={v['symmetric_difference_pct_of_union']:.3f}%, "
          f"전체 표본 중 판정이 바뀐 몫은 {v['symmetric_difference_pct_of_all']:.3f}%다."
          for i,v in enumerate(rows)) + ' 예산 대조 순서는 3.8e9, 4.2e9이며 기준은 4e9다.',
        '두 집합의 합집합에서 공통이 아닌 몫을 자카드의 보수로 보고한다. 기준 사건의 탈락률과 전체 표본의 판정 변화율은 분모를 별도로 적는다.',
        '겹침 설명에 기준 개수·교집합·합집합·추가·탈락을 함께 표시한다.',
        [('benchmark/read_canyonnull_0910.py','즉 자세 다섯 중 하나쯤이 다른 자세다')])
    d=c['canyon'];x=c['adversarial']
    add('협곡 판독기가 상한 근접 진단을 빈 배열로 바꿔 내보낸다','정보 유실은 현재 코드, 경고 누락은 합성 입력으로 재현',
        '새 load는 n_trunc를 읽지 않고 trunc=[]를 반환한다. 이어 호출한 measure의 at_path_cap는 npaths의 중앙값으로 계산되므로 드문 자세의 상한 근접을 감지하는 대체 장치도 아니다.',
        f"발간된 협곡 {d['n_published_cells']}개 조건의 장면·자유공간 샤드를 직접 읽었으며, 저장된 상한 근접 사건 합계는 "
        f"{d['recorded_near_cap_events']}개, 해당 진단이 없는 샤드는 {d['missing_diagnostic_shards']}개였다. "
        f"읽은 반환 경로 수의 최댓값은 {d['max_returned_paths']}개였다. 따라서 이 발간값에서 실제 잘림을 발견한 것은 아니다. "
        f"합성 입력에 상한 근접 {x['synthetic_recorded_near_cap_events']}건을 넣으면 현재 함수는 "
        f"trunc={x['returned_trunc']}, at_path_cap={x['returned_at_path_cap']}를 반환했다. "
        'n_trunc 자체도 반환 수의 상한 근접 휴리스틱이며 후보 잘림의 직접 계측은 아니다. 영 경고는 무잘림 증명이 아니다.',
        '저장된 상한 근접 진단을 읽어 보고하며, 진단 미수집과 경고 없음은 구분한다. 반환 수 기반 휴리스틱의 한정은 유지한다.',
        '샤드별 n_trunc와 실제 cap을 보존하고 nret 진단을 전파한다. npaths 중앙값은 median_npaths_near_cap처럼 뜻에 맞게 이름 붙인다.',
        fixed=(None if x['defects_still_present']['trunc_diagnostic_dropped'] is None
               else not (x['defects_still_present']['trunc_diagnostic_dropped']
                         or x['defects_still_present']['median_only_cap_flag'])),
        fixed_note=('read_canyonnull_0910._trunc_of() 와 read_0918B_0909.load() 가 저장된 nret·상한으로 '
                    '지금 문턱(0.99)을 다시 적용해 싣고, ⭐2026-09-11 에 **주 원장 병합**'
                    '(elevation_sweep_md.py)도 같은 식으로 고쳤다 — n_trunc 는 재계산, '
                    'n_trunc_stored 는 샤드에 적힌 값. 중앙값 판정은 median_npaths_near_cap 으로 이름을 고쳤다.'),
        refs=[('benchmark/read_canyonnull_0910.py','_trunc_of(z, os.path.basename(f))'),
         ('benchmark/read_0918B_0909.py','r["median_npaths_near_cap"]'),
         ('benchmark/elevation_sweep_md.py','n_tr_stored += int(_nt[0])')])
    drop=c['drop']
    add('샤드 개수·배열 길이만으로 입력의 완전성과 계측 여부를 판정한다','현재 자료 정상 확인, 잠재 결함은 합성 입력으로 재현',
        '협곡 판독기는 idx를 정렬한 뒤 버려서 중복·누락·장면과 자유공간의 같은 시각 대응을 검사하지 않는다. 낙차 판독기는 n_dup가 일부만 없는 경우 결측값을 복제 부족으로 세게 된다.',
        f"합성 자료에서 총 {x['n_declared']}행이지만 고유 인덱스 {x['n_scene_unique_indices']}개인 장면을 "
        f"현 함수가 수락했다(accepted={x['equal_length_duplicate_index_accepted']}). "
        f"다른 합성 자료에서는 n_dup 미기록 {x['mixed_dup_unknown']}행을 short {x['mixed_dup_counted_short']}건으로 셌다. "
        f"반면 이번 원본 샤드 검사는 인덱스 완전성·유일성·유한 전계·대조 표집률을 통과했고, "
        f"발간 낙차 판독 {drop['n_rows']}개 조건의 n_dup 미기록 수는 {drop['unknown_dup']}였다. "
        '합성 실패를 현재 실험 데이터 오염으로 소급하지 않는다.',
        '예상 표본의 인덱스가 빠짐없이 한 번씩 있고 대조 쌍의 시간축이 같은 칸만 판독한다. 중복 계측이 없는 표본은 미계측으로 분리한다.',
        'idx==arange(N), 메타데이터 일치, 유한값을 검증한다. valid_dup와 short를 분리하고 양쪽 비교에 사용한 파일 목록을 저장한다.',
        [('benchmark/read_canyonnull_0910.py','o = np.argsort'),
         ('benchmark/read_canyonnull_0910.py','ns < 2 or nf < 2'),
         ('benchmark/read_dropladder_0910.py','if (D < 0).all():'),
         ('benchmark/read_dropladder_0910.py','short = have & (D < 2)')],
        fixed=(None if x['defects_still_present']['unknown_dup_counted_as_short'] is None
               else not (x['defects_still_present']['equal_length_duplicate_index_accepted']
                         or x['defects_still_present']['unknown_dup_counted_as_short'])),
        fixed_note=('협곡·낙차 판독기가 idx 온전성·선언 표본수·표집률·비유한 전계(복소 배열에 직접 '
                    'isfinite)를 함께 싣고, ⭐2026-09-11 에 **비교 쌍의 시간축**까지 본다. 낙차 쪽은 '
                    '계측된 자세만 «줄<3» 으로 세고 전부 미계측이면 사유를 남긴다. '
                    '판정은 검토 코드가 아니라 **생산 main() 을 돌려** 확인한다.'))
    return fs


def render(o):
    c=o['checks'];j=str(OUT.relative_to(ROOT));a=c['atlas'];s=a['sample']
    lines=['# 시오나 최신 판독기 재검토','',
        '현재 소스와 발간 원장에 사용된 저장 자료를 다시 대조했다. 새로운 솔버 실행이나 실기 계측을 수행한 보고서가 아니다.', '',
        '**상태:** 수정 제안이다. 기존 실험 코드·원장·작업 큐·발표 자료는 변경하지 않았다.', '',
        '[주피터 보고서](LATEST_READERS_REVIEW_0910.ipynb) · [재계산 원장](../outputs/latest_readers_review_0910.json) · '
        '[생성기](../benchmark/review_latest_readers_0910.py)', '',
        '```bash','cd /workspace/sionna',
        "CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_latest_readers_0910.py",'```','',
        f"원본 샤드 {c['n_unique_shards']}개를 읽어 idx 완전성·유일성·유한 전계·대조 표집률을 확인했다. "
        '이는 저장 이전의 경로 누락이나 물리적 정확성까지 검증한 뜻은 아니다. 읽은 파일과 SHA-256은 재계산 원장에 보존했다.', '',
        '발간 원장의 파일 목록을 기준으로 삼은 협곡·낙차 자료와, 정확한 이름으로 검색한 동체 자료를 사용했다. '
        '현재 큐에 추가로 완성되는 조건은 협곡 판독에 섞지 않았다. 합성 반례는 실제 관측과 별도 기록했다.', '']
    for i,f in enumerate(o['findings'],1):
        lines += [f"## {i}. {f['title']}",'','**확인 수준:** '+f['status'],'','**문제:** '+f['issue'],'',
                  '**근거와 한정:** '+f['evidence'],'','**권장 표현:** '+f['replacement'],'',
                  '**수정 작업:** '+f['followup'],'',f"**재계산 근거:** `{j}` → `findings[{i-1}]` 및 `checks`.",'', '**원문 위치:**','']
        for ref in f['sources']:
            p=Path(ref['path']);target=str(p) if p.is_absolute() else '../'+str(p)
            lines += [f"- [{p.name}:{ref['line']}]({target}"+(f"#L{ref['line']}" if ref['line'] else '')+")"+
                      ('' if ref['found'] else ' — 현재 파일에서 해당 문구를 찾지 못함'), '> '+ref['quote'],'']
    lines += ['## 보완 메모: 추가 원인으로 확정하지 않은 사항','',
        '아래 사항은 정의·설계의 보완점이며 위의 실증 지적 건수에 더하지 않았다.', '',
        '- `n_dup = 전체 행 수 − 고유 키 수`는 중복된 행의 총수다. 그것에 하나를 더한 값이 한 경로의 복제 배수가 되려면 반복되는 키 집단의 구조를 알아야 한다. '
        '서로 다른 중복 집단으로 같은 총수가 나올 수 있으므로, 기존 경로 덤프가 확인한 한 집단의 복제 배수와 전체 자세의 집계값을 구분한다. '
        '현재 낙차 사다리의 복제 배수가 틀렸다고 단정하지 않는다. `copies_median`에는 이 조건을 명시하거나 키별 multiplicity를 직접 기록한다.', '',
        '- `문턱 없는 셈`이라는 표현이 새 동체 판독기에 남아 있다. DEV 비율을 사용하는 사건 분류이므로 '
        '“복소 잔차의 상대 편차 문턱을 적용한 사건 수”라고 적는 편이 정확하다. 원장이 문턱을 자유 파라미터라고 적은 한정은 유지한다.', '',
        '- 새 동체 작업 설계가 제한된 배율 점의 사건 개수로 “계단/비탈”을 판정한다. 문턱을 적용한 정수 사건 개수는 '
        '연속적인 잔차 변화에도 계단 모양이 된다. 개수의 급변을 곧 물리 응답의 불연속으로 부르지 말고, 경계 부근 각 사건의 연속 잔차와 더 촘촘한 배율 대조로 구분한다.', '',
        '위 세 항목의 원문 위치도 원장의 `supplementary_sources`에 저장했다.', '',
        '## 이미 고쳐진 항목의 취급','',
        '- 현재 `--det` 코드는 전체 합산용 정렬 배열과 중복 제거용 원래 인덱스를 분리한다. 이전 인덱스 오류를 이번 미수정 지적에 다시 넣지 않았다. '
        '이번 확인 범위는 현재 코드의 인덱스 대응이며 GPU 재실행 검증과는 구분한다.',
        '- 기본 환경의 재질 선택은 드론을 넣기 전에 저장한 환경 객체 이름을 사용하도록 바뀌었다. 이전 선택 범위 문제를 재지적하지 않았다. '
        '공유 재질의 모든 부수 효과까지 새로 검증한 뜻은 아니다.',
        '- 로터 씨앗 근거 부재라는 옛 지적을 반복하지 않았다. 이번 검토의 새 문제는 위 여섯 항목에 한정한다.', '',
        '## 수정 순서','',
        '발간 숫자에 영향이 확인된 아틀라스의 대역 정의를 먼저 고치고 관련 산출물을 다시 굽는다. '
        '다음으로 판독기의 입력 검증·진단 전달을 고친다. 문서에서는 잔존 개수·집합·비율의 분모를 구분하고, '
        '실행 결과에 적용할 판정 규칙을 최신 재개 문서와 작업 생성기에 일치시킨다. '
        '확률적 불확실성이나 기체 형상 효과의 주장은 그 목적에 맞는 별도 대조 이후에 판단한다.', '']
    MEMO.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='최신 판독기 검토',title='발간 지표와 사건 비교의 추가 수정점',
        did='현재 판독기와 발간 원장의 저장 신호를 대조해 수정할 부분을 기록했다.',
        results=[f"추가 지적 {len(o['findings'])}건의 근거와 수정안을 기록했다 ⟨{j} : findings⟩.",
                 f"원본 샤드 {c['n_unique_shards']}개의 입력 조건을 검산했다 ⟨{j} : checks.n_unique_shards⟩.",
                 f"아틀라스의 비단위 프로펠러 배율 조건 {a['n_tagged_cells']}개 칸을 확인했다 ⟨{j} : checks.atlas.n_tagged_cells⟩."],
        method=[('관측 검산','원장에 연결된 원본 배열과 현재 분석 함수를 CPU에서 대조'),
                ('잠재 결함 검산','실제 데이터와 분리된 합성 샤드를 현재 판독 함수에 입력')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_latest_readers_0910.py"],
                   out=[j],runtime='CPU 한 코어, 저장 자료 판독'))]
    for i,f in enumerate(o['findings']):
        blocks.append(md(f"## {i+1}. {f['title']}",'',f['replacement'],'',
            f"[원문·재계산·조건·한정](LATEST_READERS_REVIEW_0910.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([
        ('아틀라스 대역과 관련 산출물을 정정한다','같은 신호에서 발생한 지표 정의의 차이','LATEST_READERS_REVIEW_0910.md'),
        ('판독기 검증과 문서 판정 규칙을 정리한다','진단 누락과 집합·분모 해석의 혼동','LATEST_READERS_REVIEW_0910.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    digest(__file__)
    c=dict(body=body_check(),canyon=canyon_check(),atlas=atlas_check(),
           adversarial=adversarial_check(),drop=drop_check())
    c['n_unique_shards']=sum(k.startswith('outputs/elev_sweep_shards/') for k in HASHES)
    fs=findings(c)
    supplemental=[source('benchmark/elevation_sweep_md.py','n_dup[j] = int'),
        source('benchmark/read_dropladder_0910.py','copies_median='),
        source('benchmark/read_bodyladder_0910.py','문턱 없는 셈:'),
        source('runners/make_jobs_0924.py','면 ×2 는 **계단**'),
        source('benchmark/elevation_sweep_md.py','_td = _t[_sel]'),
        source('benchmark/elevation_sweep_md.py','_envnames = set(_scene_obj_names)')]
    out=dict(_meta=dict(generator='benchmark/review_latest_readers_0910.py',source_sha256=HASHES,
        scope='Current source and stored data audit; synthetic counterexamples are separately labelled. No GPU runs.'),
        checks=c,findings=fs,supplementary_sources=supplemental)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    render(out)
    print(json.dumps(dict(findings=len(fs),unique_shards=c['n_unique_shards'],atlas_cells=c['atlas']['n_tagged_cells'],
                         canyon_cells=c['canyon']['n_published_cells']),ensure_ascii=False))


if __name__=='__main__': main()
