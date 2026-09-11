"""Audit the current publication and readers without running solvers.

Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_current_state_0911.py
Writes only this review's JSON, Markdown and generated notebook. One CPU, no GPU.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast
import contextlib
from datetime import datetime,timezone
import glob
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import types
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SHD=ROOT/'outputs/elev_sweep_shards'
OUT=ROOT/'outputs/current_state_review_0911.json'
MD=ROOT/'docs/CURRENT_STATE_REVIEW_0911.md'
NB=MD.with_suffix('.ipynb')
HASHES={}
READ_FILES=set()


def path(p):
    p=Path(p)
    return p if p.is_absolute() else ROOT/p


def digest(p):
    p=path(p);key=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    if key not in HASHES:
        with p.open('rb') as f:HASHES[key]=hashlib.file_digest(f,'sha256').hexdigest()
    return p


def read(p):return digest(p).read_text()
def js(p):return json.loads(read(p))


def source(p,needle):
    lines=read(p).splitlines();i=next((i for i,s in enumerate(lines,1) if needle in s),None)
    return dict(path=str(p),line=i,quote=lines[i-1].strip() if i else needle,found=i is not None)


def funcs(p,names,ns):
    nodes=[n for n in ast.parse(read(p)).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(nodes)==len(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
    return ns


def stored(files):
    data=[]
    for name in files:
        p=digest(SHD/Path(name).name);READ_FILES.add(p.name)
        with np.load(p,allow_pickle=False) as z:
            data.append(dict(idx=z['idx'],E=z['E'],meta=z['meta'],
                             dup=z['n_dup'] if 'n_dup' in z else np.full(z['idx'].shape,-1)))
    idx=np.concatenate([d['idx'] for d in data]);o=np.argsort(idx)
    E=np.concatenate([d['E'] for d in data])[o];n=int(data[0]['meta'][3]);prf=float(data[0]['meta'][4])
    assert np.array_equal(idx[o],np.arange(n))
    assert np.isfinite(E).all()
    assert all(int(d['meta'][3])==n and float(d['meta'][4])==prf for d in data)
    return dict(E=E,n=n,prf=prf,dup=np.concatenate([d['dup'] for d in data])[o])


def published():
    cj=js('outputs/read_canyonnull_0910.json');dj=js('outputs/read_dropladder_0910.json')
    plot=ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py'
    hampel=funcs(plot,['hampel_mask'],dict(np=np))['hampel_mask']
    rows=[]
    for el,g in cj['by_el'].items():
        for label,r in g['cells'].items():
            O=stored(r['files_scene']);F=stored([f.replace('_envsionna-simple_street_canyon','') for f in r['files_scene']])
            assert O['n']==F['n'] and O['prf']==F['prf']
            d=O['E']-F['E'];center=complex(np.median(d.real),np.median(d.imag))
            n=int((abs(d-center)>.5*abs(center)).sum());h=int(hampel(abs(O['E']),51,5.).sum())
            assert n==r['n_static_changed'] and h==cj['deck_rule_hampel'][el][label]['n_mask']
            rows.append(dict(el_deg=float(el),cell=label,n=n,n_hampel=h,files=r['files_scene'],
                             path_cap=r['path_cap']))
    drop=[]
    for r in dj['rows']:
        c=stored(r['files']);have=c['dup']>=0
        ns=int((have&(c['dup']<2)).sum());nd=int((abs(c['E'])/np.median(abs(c['E']))<.9).sum())
        assert ns==r['n_short'] and nd==r['n_dip']
        drop.append(dict(arm=r['arm'],spp=r['spp'],n_short=ns,n_dip=nd,n_unknown=int((~have).sum()),files=r['files']))
    return dict(canyon=rows,drop=drop,n_canyon_cells=len(rows),n_drop_cells=len(drop),
                n_unique_shards=len(READ_FILES),all_index_finite_time_checks_pass=True)


def atlas():
    j=js('outputs/md_atlas_index.json');l=js('outputs/elevation_sweep_md.json')
    historical='50a4dbaa^:outputs/md_atlas_index.json'
    raw=subprocess.check_output(['git','show',historical],cwd=ROOT)
    old=json.loads(raw);HASHES['git:'+historical]=hashlib.sha256(raw).hexdigest()
    row={(r['engine'],float(r['el_deg'])):r for r in l['rows']}
    changed=[];unchanged=0;tipdiff=[];verified=0;sample=None
    sys.path.insert(0,str(ROOT/'src'));digest('src/drones.py')
    from drones import DRONES
    ns=dict(np=np,math=math,re=re,DRONES=DRONES,DRONE_DEFAULT=j['_meta']['drone_default'],
            C_LIGHT=2.998e8,FC=j['_meta']['fc_hz'],PRF=j['_meta']['prf_hz'],RHY_HW=8.)
    funcs('benchmark/build_md_atlas.py',['prop_scale_tag','airframe_tag','arm_rates','f_tip_at','rhythm_share','comb_contrast_db'],ns)
    digest('outputs/elevation_sweep_md.npz')
    with np.load(ROOT/'outputs/elevation_sweep_md.npz',allow_pickle=False) as z:
        for t,v in j['topics'].items():
            for arm,av in v['arms'].items():
                rates=ns['arm_rates'](arm)
                for el,c in av['cells'].items():
                    r=row[(arm,float(el))];oc=old['topics'][t]['arms'][arm]['cells'][el]
                    if c==oc:unchanged+=1
                    else:changed.append(dict(arm=arm,el_deg=float(el),fields=[k for k in c if c[k]!=oc.get(k)]))
                    if 'f_tip_hz' in r and abs(c['f_tip_hz']-r['f_tip_hz'])>max(.2,abs(r['f_tip_hz'])*.001):
                        tipdiff.append(dict(arm=arm,el_deg=float(el),atlas=c['f_tip_hz'],producer=r['f_tip_hz']))
                    if '_ps' not in arm or any(c[k] for k in ['incomplete','no_return','no_motion']):continue
                    E=z[f'{arm}/el{float(el):+.0f}'];ft=ns['f_tip_at'](rates,float(el));ff=rates['f_flash_hz']
                    rh=ns['rhythm_share'](E,ff,ft)[0];comb=ns['comb_contrast_db'](E,ff,ft)
                    assert abs(rh-c['outlier']['base']['rhythm_pct'])<.0001
                    if comb is not None:assert abs(comb-c['outlier']['base']['comb_db'])<.0001
                    verified+=1
                    if arm=='ours_r15_n8192_ps2_mfixbatteryi5_blperairframe' and float(el)==0:
                        sample=dict(arm=arm,el_deg=0,old_rhythm_pct=oc['rhythm_share_pct'],current_rhythm_pct=rh)
    assert not tipdiff and all('_ps' in r['arm'] for r in changed)
    return dict(changed_cells=len(changed),unchanged_cells=unchanged,changes=changed,
                n_recomputed_complete_ps_cells=verified,producer_tip_mismatches=tipdiff,
                agreement_tolerance='max(0.2 Hz, 0.1% of producer tip)',sample=sample,
                built_at=j['_meta']['built_at'])


def cap_census():
    l=js('outputs/elevation_sweep_md.json');keys={(r['engine'],float(r['el_deg'])) for r in l['rows']}
    ns=funcs('benchmark/read_canyonnull_0910.py',['_trunc_of'],dict(np=np))
    records=[];recent=[];cutoff=time.time()-120
    for p in sorted(SHD.glob('*.npz')):
        if p.stat().st_mtime>cutoff:recent.append(p.name);continue
        with zipfile.ZipFile(p) as z:
            if not {'n_trunc.npy','nret.npy'}<=set(z.namelist()):continue
        digest(p)
        with np.load(p,allow_pickle=False) as z:
            nt=z['n_trunc'].ravel()
            if nt.size<2:continue
            rec=ns['_trunc_of'](z,p.name)
        m=re.match(r'(.*)_el([+-]?[\d.]+)_\d+\.npz$',p.name)
        rec['in_published_main_ledger']=bool(m and (m[1],float(m[2])) in keys)
        records.append(rec)
    mismatch=[r for r in records if r['stored']!=r['recomputed']]
    # Execute the existing merge's diagnostic block verbatim, without analyse(), STFT or writes.
    tree=ast.parse(read('benchmark/elevation_sweep_md.py'))
    loops=[n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='el']
    nodes=None
    for loop in loops:
        start=next((i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Tuple) and [getattr(x,'id',None) for x in t.elts]==['n_tr','n_seen'] for t in n.targets)),None)
        if start is not None:
            stop=next(i for i in range(start,len(loop.body)) if isinstance(loop.body[i],ast.Assign)
                      and any(isinstance(t,ast.Name) and t.id=='miss' for t in loop.body[i].targets))
            nodes=loop.body[start:stop];break
    assert nodes is not None
    first=next(r for r in mismatch if r['stored']==0 and '_n256_' in r['file'])
    stem=first['file'].rsplit('_',1)[0];files=sorted(SHD.glob(stem+'_*.npz'))
    env=dict(np=np,os=os,fs=[str(p) for p in files],E=None,secs=0.,npa=[],cfg=None)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'current merge diagnostic block','exec'),env)
    pair=[r for r in records if r['file'] in [p.name for p in files]]
    return dict(n_shards=len(records),mismatches=mismatch,n_mismatches=len(mismatch),
                n_zero_to_warning=sum(r['stored']==0 and r['recomputed']>0 for r in mismatch),
                n_mismatches_in_main_ledger=sum(r['in_published_main_ledger'] for r in mismatch),
                diagnostic_records=records,recent_files_excluded=recent,
                merge_probe=dict(files=[p.name for p in files],merge_n_trunc=int(env['n_tr']),
                                 recomputed_n_trunc=sum(r['recomputed'] for r in pair),
                                 n_poses=int(env['n_seen']),cap=int(env['cap_seen'])))


def synthetic():
    ns=funcs('benchmark/read_canyonnull_0910.py',['load','_trunc_of','_deck_mask_table'],
             dict(np=np,glob=glob,os=os,sys=sys,DECK=''))
    results={}
    with tempfile.TemporaryDirectory(prefix='sionna-review-0911-') as td:
        ns['SHD']=td
        for sh in range(2):
            i=np.arange(sh,8192,2);E=np.ones(i.size,complex)
            np.savez(Path(td)/f'inconsistent_el-60_{sh:02d}.npz',idx=i,E=E,
                     meta=[-60,sh,2,16384 if sh==0 else 8192,19700 if sh==0 else 10000])
            np.savez(Path(td)/f'missingmeta_el-60_{sh:02d}.npz',idx=np.arange(sh,4096,2),E=np.ones(2048,complex))
            np.savez(Path(td)/f'duplicate_el-60_{sh:02d}.npz',idx=np.arange(0,8192,2),E=E,meta=[-60,sh,2,8192,19700])
            E=E.copy()
            if sh==0:E[0]=np.nan
            np.savez(Path(td)/f'nonfinite_el-60_{sh:02d}.npz',idx=i,E=E,meta=[-60,sh,2,8192,19700])
        for label in ['inconsistent','missingmeta','duplicate','nonfinite']:
            c,n=ns['load'](label,-60)
            results[label]={k:c[k] for k in ['idx_ok','n_rows','n_expected']}
            results[label]['n_shards']=n
        # Current Hampel implementation, injected only to avoid importing plotting side effects.
        plot=ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py'
        fake=types.ModuleType('bake_outdoor');fake.hampel_mask=funcs(plot,['hampel_mask'],dict(np=np))['hampel_mask']
        previous=sys.modules.get('bake_outdoor');sys.modules['bake_outdoor']=fake
        E=np.ones(8192);E[100]=3.;bad=dict(E=E,idx_ok=False);good=dict(E=E,idx_ok=True)
        def loader(name,el):return (bad,2) if name=='base' else (good,2)
        try:table=ns['_deck_mask_table'](loader,lambda spp,rep,env:'base' if rep==0 else 'other',[-60], [('candidate',4_000_000_000,1)])
        finally:
            if previous is None:sys.modules.pop('bake_outdoor',None)
            else:sys.modules['bake_outdoor']=previous
        results['invalid_baseline_table']=table
        # Run actual main(), substituting only the input cell and output destination.
        dn=funcs('benchmark/read_dropladder_0910.py',['main'],dict(np=np,os=os,json=json,EL=0,RNG=15,
            DEPTH=2,NPOSE=8192,ARMS=['fixture'],SPPS=[1],DIP=.9,ROOT=str(ROOT),MESH='fixture',OUT=str(Path(td)/'out.json')))
        c=dict(E=np.ones(8192,complex),D=np.tile([1,2],4096),P=np.ones(8192),idx_ok=True,n_shards=2,files=[])
        dn['cell']=lambda *args:c
        try:
            with contextlib.redirect_stdout(io.StringIO()):dn['main']()
            results['fractional_median']=dict(error=None)
        except Exception as e:
            results['fractional_median']=dict(error=type(e).__name__,message=str(e),
                n_dup_median=float(np.median(c['D'])),output_written=Path(dn['OUT']).exists())
        c['D']=np.r_[np.full(4096,2),np.full(4096,-1)]
        with contextlib.redirect_stdout(io.StringIO()):dn['main']()
        r=json.loads(Path(dn['OUT']).read_text())['rows'][0]
        results['partial_observation_equality']={k:r[k] for k in ['n_measured','n_unmeasured','n_short','n_dip','dip_equals_short']}
    results['scope']='Synthetic function inputs, not observed corruption of published data.'
    return results


def historical_review_probe():
    p=digest('benchmark/review_latest_readers_0910.py')
    spec=importlib.util.spec_from_file_location('old_review_0910',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    try:
        m.atlas_check()
        return dict(error=None)
    except Exception as e:return dict(error=type(e).__name__,message=str(e),scope='Only atlas_check(); no output files written.')


def findings(c):
    out=[]
    def add(title,grade,evidence,replacement,refs):
        out.append(dict(title=title,grade=grade,evidence=evidence,replacement=replacement,
                        sources=[source(p,n) for p,n in refs]))
    cap=c['cap'];pr=cap['merge_probe']
    add('상한 진단 보정이 협곡 판독기에만 적용되고 주 원장 병합에는 남았다','실제 재고로 재현 · 다음 병합의 경고 누락',
        f"저장 n_trunc와 nret가 함께 있는 {cap['n_shards']}개 샤드 중 {cap['n_mismatches']}개가 현재 문턱 재계산과 달랐고, "
        f"{cap['n_zero_to_warning']}개는 저장값이 영이었다. 이 중 현재 주 원장에 포함된 샤드는 {cap['n_mismatches_in_main_ledger']}개다. "
        f"완전한 예시 {pr['n_poses']}표본 묶음에서 현 병합기의 진단 블록을 그대로 실행하면 경고 {pr['merge_n_trunc']}개, "
        f"저장 상한 {pr['cap']}에 현재 문턱을 적용하면 {pr['recomputed_n_trunc']}개다. "
        '현재 아틀라스가 이 자료를 깨끗한 것으로 발간했다고 주장하는 것은 아니다. 다음 병합 때 옛 진단을 다시 쓰는 경로가 남아 있다는 뜻이다. '
        '경고는 반환 수 기반 상한 근접 진단이며 실제 후보 잘림의 직접 증거와 구분한다. 병합기의 상한 미기록 자료에 대한 기본값 대입도 새 판독기와 정책이 다르다.',
        '저장 진단·당시 상한·현재 문턱의 재계산을 병합기에도 함께 보존한다. 상한 미기록이나 실행 조건 혼합은 미확인으로 표시하고, 다른 샤드의 상한을 근거 없이 빌리지 않는다.',
        [('benchmark/elevation_sweep_md.py','n_tr += int(_nt[0])'),
         ('benchmark/elevation_sweep_md.py','_cap_for_old = cap_seen if cap_seen else _cap_default'),
         ('benchmark/read_canyonnull_0910.py','recomputed=int(np.count_nonzero')])
    x=c['synthetic']['fractional_median']
    add('비정수 중앙값을 처리한 새 분기가 화면 출력에서 종료된다','수정으로 추가된 실행 오류 · 합성 입력 재현',
        f"완전한 입력에서 n_dup 중앙값을 {x['n_dup_median']}로 만들면 copies_median이 None이 된다. "
        f"실제 main()은 {x['error']}: {x['message']}로 종료했고 원장 생성 여부는 {x['output_written']}였다. "
        '현재 발간된 낙차 조건에서는 이 오류가 나타났다고 확인한 것이 아니다. 비정수 처리 분기의 반환값과 출력 형식이 맞지 않는 문제다.',
        '숫자 저장과 표시 문자열을 분리한다. 정수가 아닌 중앙값도 그대로 보존하고, 복제 배수로 해석할 수 없는 경우에는 사유를 출력한다.',
        [('benchmark/read_dropladder_0910.py','_copies ='),('benchmark/read_dropladder_0910.py',"{r['copies_median']:>9}")])
    x=c['synthetic']
    add('입력 검증에 기준선·메타데이터·유한값의 빈틈이 남았다','수정 미완료 · 합성 입력 재현',
        f"중복 인덱스 반례는 새 검사에서 idx_ok={x['duplicate']['idx_ok']}로 거절되어 수정 효과가 있다. "
        f"그러나 샤드별 선언 표본 수와 PRF가 다른 입력은 idx_ok={x['inconsistent']['idx_ok']}로 통과한다. "
        f"메타데이터 없는 {x['missingmeta']['n_rows']}행 입력도 idx_ok={x['missingmeta']['idx_ok']}이며, "
        f"비유한 전계를 포함한 입력도 idx_ok={x['nonfinite']['idx_ok']}다. "
        'Hampel 표는 비교 대상의 idx_ok를 보지만 기준선의 idx_ok를 확인하기 전에 마스크를 만든다. '
        '기준선에 idx_ok=False를 전달해도 비교 대상 행이 출력되는 것을 실제 Hampel 함수로 재현했다. '
        '이들은 현재 원본이 오염되었다는 발견이 아니라 판독기의 검증 범위 문제다.',
        '기준선과 비교 대상에 같은 검증을 적용한다. 예상 표본 수는 실행 조건으로 확인하고, 각 샤드의 선언·시간축·전계 유한성을 함께 검사한다. 온전한 이전 실행을 최신 부분 실행으로 덮어 고르는 방식은 사용하지 않는다.',
        [('benchmark/read_canyonnull_0910.py','n_expected = int(_m[3])'),
         ('benchmark/read_canyonnull_0910.py','and (n_expected is None or idx.size == n_expected)'),
         ('benchmark/read_canyonnull_0910.py','if base is None:'),
         ('benchmark/read_dropladder_0910.py','and (n_expected is None or idx.size == n_expected)')])
    x=c['synthetic']['partial_observation_equality']
    add('부분 계측에서도 전체 사건 집합이 일치했다는 표지가 붙는다','해석 범위 누락 · 합성 입력 재현',
        f"n_dup 계측 {x['n_measured']}개·미계측 {x['n_unmeasured']}개인 입력에서 "
        f"n_short={x['n_short']}, n_dip={x['n_dip']}, dip_equals_short={x['dip_equals_short']}가 나온다. "
        '저장된 두 마스크의 동일성 자체는 맞다. 그러나 미계측 자세가 실제로 복제 부족이었는지는 알 수 없어 전체 자세의 관계를 확인한 뜻으로 쓰면 과하다. '
        '현재 발간된 낙차 조건은 중복 계측이 모두 있어 이 제한으로 기존 숫자를 철회할 이유는 확인하지 못했다.',
        '계측된 공통 모집단에서의 일치와 전체 모집단 판정 가능 여부를 별도 필드로 둔다. 미계측이 있으면 전체 일치는 미확인으로 표시하되 전체 진폭 낙차 수는 유지한다.',
        [('benchmark/read_dropladder_0910.py','short = have &'),
         ('benchmark/read_dropladder_0910.py','dip = (a / med) < DIP'),
         ('benchmark/read_dropladder_0910.py','dip_equals_short=bool')])
    h=c['historical_review']
    add('이전 검토의 재현 코드도 현재 소스 변경을 따라가지 못한다','검토 산출물 자체의 재현성 결함',
        f"제가 작성한 이전 검토 빌더의 atlas_check()를 현재 환경에서 호출하면 {h['error']}: {h['message']}가 발생했다. "
        '원인은 새 arm_rates가 호출하는 보조 함수가 AST 추출 목록에 빠진 것이다. 그 함수만 추가해도 해결은 끝나지 않는다. '
        '이전 검토는 보정 전 대역에 배율을 추가하는 계산이므로, 이미 보정된 현재 함수에 그대로 적용하면 이중 보정이 된다. '
        '기존 검토 결과는 당시 상태의 기록으로 유지하고, 현재 상태와 혼동해서 다시 생성하면 안 된다.',
        '역사 재현용 입력·소스 커밋과 현재 회귀 검사용 계산을 구분한다. 이번 보고서는 현재 보정된 대역을 그대로 사용하여 발간값을 재계산한다.',
        [('benchmark/review_latest_readers_0910.py',"['airframe_tag','arm_rates','f_tip_at','comb_contrast_db','rhythm_share']"),
         ('benchmark/review_latest_readers_0910.py',"correct=ft*ps"),
         ('benchmark/build_md_atlas.py','ps = prop_scale_tag(arm)')])
    add('수정된 해석과 예전 판정 문구가 작업 문서에 함께 남았다','남아 있는 문서 간 불일치',
        '0923C의 널 띠 판정과 최신 재개 문서의 해당 문구는 수정됐다. 하지만 make_jobs_0924.py에는 '
        '잔존 개수가 같아서 격자 변경과 구별되지 않는다는 문장이 남아 있다. jobs_0920.txt의 유사 판정은 '
        '재개 문서에서 사용 제한을 붙인 상태이며 원문만 읽으면 그 제한을 놓칠 수 있다. '
        '사건 목록의 차이와 통계적 효과의 구분 가능성은 다른 주장이다. 두 배율의 집합이 같다는 사실만으로 독립성을 판정하지 않는다.',
        '잔존 개수는 같고 사건 목록은 달랐다는 관찰로 통일한다. 이미 실행된 작업 줄은 보존하면서 결과 판독에 적용할 최신 규칙을 원문 가까이에 연결한다.',
        [('runners/make_jobs_0924.py','구별되지 않는다'),
         ('work/sweep_0904/RESUME_0911.md','같은 뿌리가 이미 구운'),
         ('runners/jobs_0920.txt','두 벌이 0.03 안에서 붙으면')])
    return out


def render(o):
    c=o['checks'];a=c['atlas'];p=c['published'];j=str(OUT.relative_to(ROOT))
    lines=['# 시오나 현재 상태 재점검 — 2026-09-11','',
        f"검토 기준 커밋: `{o['_meta']['head']}`. 실행 시각: {o['_meta']['checked_at_utc']}.",'',
        '현재 코드·발간 원장·기존 샤드의 읽기 전용 검토다. 운영 코드·기존 원장·작업 큐·발표 자료를 수정하거나 솔버를 실행하지 않았다.', '',
        '[주피터 보고서](CURRENT_STATE_REVIEW_0911.ipynb) · [재계산 원장](../outputs/current_state_review_0911.json) · '
        '[생성기](../benchmark/review_current_state_0911.py)', '',
        '```bash','cd /workspace/sionna',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_current_state_0911.py",'```','',
        '## 수정이 확인된 부분','',
        f"- 아틀라스 전체 {a['changed_cells']+a['unchanged_cells']}개 칸에서 변경 {a['changed_cells']}개는 모두 ps 조건이다. "
        f"나머지 {a['unchanged_cells']}개 칸의 JSON 객체는 수정 전과 같았다. 완전한 ps 조건 {a['n_recomputed_complete_ps_cells']}개는 "
        '현재 함수와 저장 신호로 리듬 몫·빗살 대비를 재계산해 발간값과 대조했다.',
        f"- 생산자 f_tip와 아틀라스 f_tip를 대조한 허용 오차 초과 불일치는 {len(a['producer_tip_mismatches'])}개였다. "
        f"허용 오차는 {a['agreement_tolerance']}다. 이는 운동학적 기준 대역의 일치 검사다.",
        f"- 협곡 {p['n_canyon_cells']}개 조건·낙차 {p['n_drop_cells']}개 조건의 발간 수를 원본 샤드 "
        f"{p['n_unique_shards']}개에서 재계산했다. 이 원본의 인덱스 완전성·유한값·대조 시간축 검사는 통과했다.",
        '- 협곡의 stored/recomputed 진단 분리, 낙차의 미계측값 제외, 자카드 분모 명시, 0923C의 널 띠 판정 제거를 확인했다.', '',
        '## 남은 수정점','']
    for i,f in enumerate(o['findings'],1):
        lines += [f"### {i}. {f['title']}",'','**확인 수준:** '+f['grade'],'','**근거와 범위:** '+f['evidence'],'',
                  '**권장 수정:** '+f['replacement'],'',f"근거 원장: `{j}` → `findings[{i-1}]` 및 `checks`.",'']
        for s in f['sources']:
            target=str(s['path']) if Path(s['path']).is_absolute() else '../'+s['path']
            lines += [f"- [{Path(s['path']).name}:{s['line']}]({target}#L{s['line']})",'```python',s['quote'],'```','']
    lines += ['## 우선순위와 한정','',
        '먼저 낙차 판독기의 출력 예외를 고치고, 기준선과 비교 대상의 입력 검증을 일치시킨다. '
        '주 원장을 다음에 병합하기 전에는 상한 진단의 세대 처리를 통일한다. 이어 부분 계측의 일치 표지와 작업 문서의 표현을 정리한다.', '',
        '이번 합성 입력의 실패를 현재 발간 데이터의 손상으로 소급하지 않는다. 원본 인덱스 검사를 통과했다고 저장 이전의 후보 누락이나 물리적 정확성까지 확인한 것도 아니다. '
        '덱 전체의 안전성은 이번 검토의 판정 대상에 포함하지 않았다. 과거 보완 메모의 계단/불연속 지적을 새 실증 문제로 재사용하지 않았다.', '',
        '이전 검토 기록은 당시 소스에 대한 자료다. 현재 상태는 이 보고서의 확인 시각·소스 해시·파일 목록으로 구분한다. '
        '큐가 추가 샤드를 생성하므로 재실행 시 재고 총수는 달라질 수 있다.', '']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='현재 상태 재점검',title='수정 확인과 판독기의 남은 경계 조건',
        did='발간 원장의 수정 반영을 확인하고 현재 판독기의 경계 조건을 재현했다.',
        results=[f"아틀라스 {a['changed_cells']+a['unchanged_cells']}개 칸의 변경 범위를 대조했다 ⟨{j} : checks.atlas⟩.",
                 f"상한 진단 샤드 {c['cap']['n_shards']}개를 재계산했다 ⟨{j} : checks.cap.n_shards⟩.",
                 f"추가 피드백 {len(o['findings'])}건에 확인 범위와 수정안을 남겼다 ⟨{j} : findings⟩."],
        method=[('발간값 확인','저장 원장과 원본 신호를 현재 분석 함수로 대조'),
                ('경계 조건 확인','실제 입력과 분리한 합성 자료로 현재 함수를 실행')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_current_state_0911.py"],
                   out=[j],runtime='CPU 한 코어, GPU 사용 없음'))]
    for i,f in enumerate(o['findings']):
        blocks.append(md(f"## {i+1}. {f['title']}",'',f['replacement'],'',
            f"[원문·조건·재현 결과](CURRENT_STATE_REVIEW_0911.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([
        ('출력 분기와 공통 입력 검증을 보완한다','경계 입력에서의 종료와 판정 누락','CURRENT_STATE_REVIEW_0911.md'),
        ('병합 진단과 최신 판독 규칙을 연결한다','구세대 진단의 재사용과 해석 혼선','CURRENT_STATE_REVIEW_0911.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    digest(__file__)
    c=dict(published=published(),atlas=atlas(),cap=cap_census(),synthetic=synthetic(),
           historical_review=historical_review_probe())
    fs=findings(c)
    out=dict(_meta=dict(generator='benchmark/review_current_state_0911.py',
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=HASHES,scope='Read-only source and stored-data audit; synthetic failures separately labelled.'),
        checks=c,findings=fs)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    render(out)
    print(json.dumps(dict(findings=len(fs),atlas_changed=c['atlas']['changed_cells'],
                         cap_shards=c['cap']['n_shards'],published_shards=c['published']['n_unique_shards'])))


if __name__=='__main__':main()
