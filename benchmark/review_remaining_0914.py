"""Read-only audit of current readers, publication chain and queue.
Run: /workspace/.venvs/py312/bin/python benchmark/review_remaining_0914.py
Uses one CPU. Production main functions publish only to temporary directories.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import collections,contextlib,copy,hashlib,io,json,math,runpy,shutil,subprocess,sys,tempfile,time,types
from pathlib import Path
from unittest.mock import patch
import numpy as np
import review_queue_followup_0914 as prev
old=prev.old;base=old.base;ROOT=old.ROOT
sys.path.insert(0,str(ROOT/'src'))
import reader_gate as gate
CACHE=ROOT/'work/remaining_review_0914_cache.json'
OUT=ROOT/'outputs/remaining_review_0914.json'
MD=ROOT/'docs/REMAINING_REVIEW_0914.md';NB=MD.with_suffix('.ipynb')
def save(c):
    c.setdefault('source_hashes',{}).update(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')
def read():return json.loads(CACHE.read_text())
def attempt(fn):
    try:return dict(error=None,result=fn())
    except BaseException as e:return dict(error=type(e).__name__,message=str(e))
def init():
    loader=old.loadmod
    with tempfile.TemporaryDirectory() as td:
        def isolated_loader(rel):
            m=loader(rel)
            if rel=='benchmark/read_scenephysics_0913.py':
                m.OUT=str(Path(td)/'scene.json');m.MD=str(Path(td)/'scene.md')
            return m
        with patch.object(prev,'CACHE',CACHE),patch.object(old,'loadmod',isolated_loader):prev.inputs();prev.corrected()
    c=read();c['_meta']['generator']='benchmark/review_remaining_0914.py';save(c)
def diffs(a,b,path=''):
    if type(a)!=type(b):return [dict(path=path,old=a,new=b)]
    if isinstance(a,dict):
        out=[]
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:out.append(dict(path=path+'/'+k,old=a.get(k),new=b.get(k)))
            else:out+=diffs(a[k],b[k],path+'/'+k)
        return out
    if isinstance(a,list):
        if len(a)!=len(b):return [dict(path=path,old_length=len(a),new_length=len(b))]
        return sum((diffs(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))),[])
    return [] if a==b else [dict(path=path,old=a,new=b)]
def real_readers():
    c=read();out={}
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation']
    esm=types.SimpleNamespace(SHD=str(ROOT/'outputs/elev_sweep_shards'),one_generation=choose)
    for name in ['read_wfsurvive_0912','read_scenephysics_0913','read_bandflat_0913','read_altitude_0914']:
        m=old.loadmod('benchmark/'+name+'.py');jsonattr='OUT_J' if hasattr(m,'OUT_J') else 'OUT';mdattr='OUT_MD' if hasattr(m,'OUT_MD') else 'MD'
        before=json.loads(Path(getattr(m,jsonattr)).read_text());start=time.monotonic();log=io.StringIO()
        with tempfile.TemporaryDirectory() as td,contextlib.ExitStack() as st:
            st.enter_context(patch.object(m,jsonattr,str(Path(td)/'out.json')));st.enter_context(patch.object(m,mdattr,str(Path(td)/'out.md')))
            if hasattr(m,'prod'):st.enter_context(patch.object(m,'prod',lambda:esm))
            with contextlib.redirect_stdout(log):result=attempt(m.main)
            p=Path(td)/'out.json';after=json.loads(p.read_text()) if p.exists() else None
            out[name]=dict(**result,seconds=round(time.monotonic()-start,2),published=after is not None,log_tail=log.getvalue()[-1500:])
            if after is not None:out[name].update(differences=diffs(before,after),collections={k:len(v) for k,v in after.items() if isinstance(v,list)})
        print('main',name,out[name]['error'],flush=True);c['checks']['actual_reader_mains']=out;save(c)
def altitude_cases():
    c=read();m=old.loadmod('benchmark/read_altitude_0914.py');L=base.js('outputs/elevation_sweep_md.json');A=base.js('outputs/read_altitude_0914.json');r=A['rows'][0];pairs={(r['engine'],r['el_deg']),(r['base_engine'],r['el_deg'])};mini={**L,'rows':[s for s in L['rows'] if (s['engine'],s['el_deg']) in pairs]}
    n=int(mini['rows'][0]['n_poses']);prf=float(mini['rows'][0]['prf_hz']);freq=float(mini['rows'][0]['f_flash_hz']);tone=np.exp(2j*np.pi*np.arange(n)/4)
    x=tone-tone.mean();rho=np.vdot(x[:-1],x[1:])/np.sqrt(np.vdot(x[:-1],x[:-1]).real*np.vdot(x[1:],x[1:]).real)
    c['checks']['lag1_counterexample']=dict(n=n,period_samples=4,production_real_lag=m.lag1_corr(tone),complex_corr_magnitude=float(abs(rho)),deterministic_recurrence_error=float(np.max(np.abs(tone[1:]-1j*tone[:-1]))))
    cases=[]
    for case in ['matched','base_actual_prf_differs','ledger_prf_differs','mixed_solver_builds','pair_solver_builds_differ']:
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);j=p/'ledger.json';j.write_text(json.dumps(mini));sh=p/'shards';sh.mkdir()
            for rr in mini['rows']:
                actual=prf
                if case=='base_actual_prf_differs' and rr['engine']==r['base_engine']:actual=10000.
                if case=='ledger_prf_differs':actual=10000.
                # Identical sample vectors isolate metadata handling from numerical signal changes.
                E=1+np.exp(2j*np.pi*(20*freq)*np.arange(n)/prf)
                for k in range(2):
                    idx=np.arange(k,n,2);build='test-old'
                    if case=='mixed_solver_builds' and k:build='test-new'
                    if case=='pair_solver_builds_differ' and rr['engine']==r['base_engine']:build='test-new'
                    np.savez(sh/f"{rr['engine']}_el{rr['el_deg']:+g}_{k:02d}.npz",idx=idx,E=E[idx],meta=[rr['el_deg'],k,2,n,actual,0],solver_build=np.array([build]))
            log=io.StringIO()
            with patch.object(m,'SHD',str(sh)),patch.object(m,'LED_J',str(j)),patch.object(m,'OUT',str(p/'out.json')),patch.object(m,'MD',str(p/'out.md')),contextlib.redirect_stdout(log):result=attempt(m.main)
            jj=json.loads((p/'out.json').read_text()) if (p/'out.json').exists() else {}
            row=jj.get('rows',[None])[0] if jj.get('rows') else None
            cases.append(dict(case=case,**result,accepted_rows=len(jj.get('rows',[])),skipped=jj.get('skipped'),published_row=row,base_actual_prf=10000. if case in ['base_actual_prf_differs','ledger_prf_differs'] else prf,correct_base_rhythm=m.rhythm_share_pct(E,10000. if case in ['base_actual_prf_differs','ledger_prf_differs'] else prf,freq,float(mini['rows'][0]['f_tip_hz']))))
    c['checks']['altitude_main_cases']=cases
    # Deterministic interleaving: cleaner starts after first publication replacement.
    with tempfile.TemporaryDirectory() as td:
        p=Path(td);a=p/'a.json';b=p/'b.md';a.write_text('{"v":"old"}');b.write_text('old');orig=gate.os.replace;gone=[];calls=[]
        def replace(src,dst):
            orig(src,dst);calls.append(str(dst))
            if len(calls)==1:gone.extend(gate.sweep_orphans([td]))
        with patch.object(gate.os,'replace',replace):res=attempt(lambda:gate.publish({str(a):{'v':'new'},str(b):'new'}))
        c['checks']['orphan_cleanup_interleaving']=dict(**res,removed_active_temps=len(gone),json_value=json.loads(a.read_text()),markdown_value=b.read_text(),replacements=len(calls))
    save(c);print('altitude and publication cases saved',flush=True)

def warehouse():
    c=read();records=[];builds=collections.Counter();bad=[];changing=[];expected=[];start=time.monotonic()
    paths=sorted((ROOT/'outputs/elev_sweep_shards').glob('*.npz'))
    for pos,p in enumerate(paths):
        s=p.stat();err=[];b='unrecorded';nr=0
        try:
            with np.load(p,allow_pickle=False) as z:a={k:z[k] for k in z.files}
            # Reading every member checks ZIP decompression/CRC, including auxiliary arrays.
            b=str(np.asarray(a['solver_build']).ravel()[0]) if 'solver_build' in a else 'unrecorded'
            i=a['idx'];m=a['meta'];n=int(m[3]);sh=int(m[1]);ns=int(m[2]);nr=len(i)
            if ns<1 or sh<0 or sh>=ns or not np.array_equal(i,np.arange(n)[sh::ns]):err.append('declared partition')
            for k in ['E','npaths','nret','E_dedup','n_dup']:
                if k in a and a[k].shape!=i.shape:err.append(k+':shape')
            for k,v in a.items():
                if np.issubdtype(v.dtype,np.number) and not np.isfinite(v).all():
                    if k=='cfg' and p.name.startswith('ours') and v.shape==(4,) and np.isfinite(v[3]) and np.isnan(v[1:3]).all() and not np.isinf(v).any():expected.append(p.name)
                    else:err.append(k+':nonfinite')
        except Exception as e:err.append(type(e).__name__+':'+str(e))
        modified=p.stat().st_mtime_ns!=s.st_mtime_ns
        if modified:changing.append(p.name)
        elif err:bad.append(dict(file=p.name,errors=err))
        builds[b]+=1
        records.append(dict(file=p.name,mtime_ns=s.st_mtime_ns,size=s.st_size,solver_build=b,samples=nr,changed=modified))
        if pos and pos%2500==0:print('warehouse',pos,flush=True)
    L=base.js('outputs/elevation_sweep_md.json')
    c['checks']['warehouse']=dict(n_files=len(paths),seconds=round(time.monotonic()-start,2),stable_errors=bad,changed=changing,expected_legacy_cfg_nan=len(expected),solver_builds=dict(builds),ledger_rows=len(L['rows']),ledger_builds=dict(collections.Counter(str(r.get('solver_build')) for r in L['rows'])),ledger_mixed_build_rows=[r['engine']+f"/el{r['el_deg']:+g}" for r in L['rows'] if r.get('solver_build_seen')],manifest=records)
    save(c);print('warehouse saved',len(paths),len(bad),flush=True)

def report_chain():
    c=read();out={};import report_style as rs;import nbformat as nbf
    m=old.loadmod('src/build_volumes.py')
    with tempfile.TemporaryDirectory() as td:
        stage=Path(td);rep=stage/'reports';rep.mkdir();idx=stage/'volumes_index.json'
        for p in (ROOT/'reports').glob('*.ipynb'):shutil.copy2(p,rep/p.name)
        log=io.StringIO();origwrite=nbf.write
        def write_nb(nb,target,*a,**kw):return origwrite(nb,rep/Path(target).name,*a,**kw)
        with patch.object(nbf,'write',write_nb),contextlib.redirect_stdout(log):out['switch_builder']=attempt(lambda:bool(runpy.run_path(str(ROOT/'src/build_report18_switch_grid.py'),run_name='__audit__')))
        out['switch_builder']['log_tail']=log.getvalue()[-600:]
        # Only output destinations are redirected. Registry reads for the freshly written
        # bootstrap index are redirected too, so crossreferences use the staged index.
        bootstrap=m._write_bootstrap_index
        def staged_bootstrap(place):
            bootstrap(place);rs._JSON_CACHE[os.path.normpath(str(ROOT/'outputs/volumes_index.json'))]=json.loads(idx.read_text())
        log=io.StringIO()
        with patch.object(m,'OUT',str(rep)),patch.object(m,'INDEX',str(idx)),patch.object(m,'_write_bootstrap_index',staged_bootstrap),contextlib.redirect_stdout(log):out['volumes']=attempt(m.main)
        out['volumes']['log_tail']=log.getvalue()[-1600:];rs._JSON_CACHE.pop(os.path.normpath(str(ROOT/'outputs/volumes_index.json')),None)
        comparison=[]
        for p in sorted(rep.glob('*.ipynb')):
            live=ROOT/'reports'/p.name;a=json.loads(live.read_text());b=json.loads(p.read_text())
            # Cell IDs do not change displayed content, metadata or code outputs.
            for j in (a,b):
                for cell in j.get('cells',[]):cell.pop('id',None)
            dd=diffs(a,b);comparison.append(dict(file=p.name,bytes_equal=live.read_bytes()==p.read_bytes(),semantic_differences=dd))
        out['notebooks']=comparison
        out['index_diff']=diffs(base.js('outputs/volumes_index.json'),json.loads(idx.read_text())) if idx.exists() else None
    c['checks']['report_chain']=out;save(c);print('report chain saved',flush=True)

def cpu_repro():
    c=read();log=io.StringIO();m=old.loadmod('benchmark/thread_ladder_0903.py')
    with tempfile.TemporaryDirectory() as td,patch.object(m,'OUT',str(Path(td)/'repro.json')),patch.object(sys,'argv',['thread_ladder_0903.py','--reps','3','--threads','1','--n-side','24','--samples','40000000']),contextlib.redirect_stdout(log):
        result=attempt(m.main);p=Path(td)/'repro.json';result['output']=json.loads(p.read_text()) if p.exists() else None
    result['log']=log.getvalue();c['checks']['cpu_reproducer']=result;save(c);print('CPU reproducer saved',result['error'],flush=True)

def followup():
    warehouse();report_chain();cpu_repro()
    with patch.object(prev,'CACHE',CACHE):prev.queue();prev.depth_audit()
    c=read();c['checks']['gates']=old.gates();save(c)

def extra_cases():
    c=read();m=old.loadmod('benchmark/read_altitude_0914.py');N=8192;prf=19700.;k=53;n=np.arange(N)
    lo=np.exp(2j*np.pi*k*n/N);hi=np.exp(1j*np.pi*n)
    aa=np.vdot(hi[:-1],hi[1:]).real;bb=(np.vdot(lo[:-1],hi[1:])+np.vdot(hi[:-1],lo[1:])).real;cc=np.vdot(lo[:-1],lo[1:]).real
    weight=float(max(np.roots([aa,bb,cc])));E=lo+weight*hi
    c['checks']['lag1_with_low_frequency_component']=dict(n=N,prf_hz=prf,low_frequency_hz=k*prf/N,high_frequency_hz=prf/2,low_frequency_power_share_pct=100/(1+weight**2),production_real_lag=m.lag1_corr(E))
    m=old.loadmod('benchmark/read_bandflat_0913.py');arms={fc:m.arm_name('free',fc) for fc in [3450,3550]};rows=[]
    class ArrayMap(dict):
        @property
        def files(self):return list(self)
    Z=ArrayMap();N=8192;tone=np.exp(2j*np.pi*53*np.arange(N)/N)
    for fc,arm in arms.items():
        f=prev.parse(arm)
        for budget in [4000000000,3900000000]:
            ff={**f,'spp':str(budget)};a=prev.unparse(ff);key=f'{a}/el-30';Z[key]=tone*(10 if budget==3900000000 and fc==3550 else 1)
            rows.append(dict(engine=a,el_deg=-30,n_poses=N,n_missing=0,prf_hz=19700.,mixed_generations=None))
    valid=m.budget_shape_spread_db(arms,-30,rows,Z);badrows=copy.deepcopy(rows)
    for r in badrows:
        if prev.parse(r['engine'])['spp']=='3900000000':r.update(n_missing=N//2,prf_hz=10000.)
    c['checks']['budget_control_gate']=dict(valid=valid,invalid_controls=m.budget_shape_spread_db(arms,-30,badrows,Z),control_n_missing=N//2,control_prf_hz=10000.,reference_prf_hz=19700.,scope='合成 metadata mismatch; saved arrays held fixed')
    for name,args in [('check_reader_gate',[]),('check_arm_names',[]),('freeze_0912',['--check'])]:
        p=subprocess.run([sys.executable,'benchmark/'+name+'.py',*args],cwd=ROOT,text=True,capture_output=True,timeout=120)
        c['checks'].setdefault('extra_gates',{})[name]=dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
    from importlib.metadata import version
    c['_meta']['installed_versions']={k:version(k) for k in ['sionna','sionna-rt','mitsuba','drjit']}
    c['checks']['audit_isolation_incident']=dict(helper='benchmark/review_queue_followup_0914.py:inputs',issue='Temporary ROOT did not redirect module OUT and MD; current scene.main publishes successfully, so the old audit fixture overwrote the live pair.',restored_from='HEAD (both publications were initially clean)',restored_files=['outputs/read_scenephysics_0913.json','docs/SCENEPHYSICS_0913.md'],adapter_fix='This generator redirects both OUT and MD when loading the scene reader for the inherited test.',tracked_production_diff=subprocess.check_output(['git','diff','--stat'],cwd=ROOT,text=True))
    save(c);print('extra cases saved',flush=True)

def completed_budget_reading():
    c=read();records=[r for r in c['checks']['queue']['records'] if r['block']=='C'];choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation'];m=old.loadmod('benchmark/read_bandflat_0913.py');data=[];L=base.js('outputs/elevation_sweep_md.json');lookup={(r['engine'],float(r['el_deg'])):r for r in L['rows']}
    for arm in sorted({r['arm'] for r in records}):
        f=prev.parse(arm);fc=float(f.get('fc') or 3500);ref=prev.unparse({**f,'spp':str(c['checks']['budget_design']['base_spp'])});pair={};reasons=[]
        for key,a in [('new',arm),('reference',ref)]:
            fs=sorted(str(p) for p in (ROOT/'outputs/elev_sweep_shards').glob(a+'_el-60_*.npz'))
            with contextlib.redirect_stdout(io.StringIO()):fs,gen=choose(fs,a+'/el-60')
            N,prf,why=gate.check_shards(fs);reasons+=why
            if why:continue
            E=np.zeros(N,complex);seen=np.zeros(N,bool);meta=[]
            for p in fs:
                base.digest(str(p));z=np.load(p);ii=z['idx'];E[ii]=z['E'];seen[ii]=True;meta.append(dict(file=Path(p).name,meta=z['meta'].tolist(),cfg=z['cfg'].tolist()))
            why=gate.check_series(E,n_poses=N,prf=prf);reasons+=why
            if not seen.all():reasons.append('incomplete')
            pair[key]=dict(arm=a,n=N,prf=prf,ac_db=float(10*np.log10(np.mean(abs(E-E.mean())**2))),selection=gen,shards=meta)
        if len(pair)==2:
            if pair['new']['n']!=pair['reference']['n'] or pair['new']['prf']!=pair['reference']['prf']:reasons.append('pair time axis')
        data.append(dict(fc_mhz=fc,**pair,reasons=reasons,new_cell_in_published_ledger=(arm,-60.) in lookup))
    center=next(r for r in data if r['fc_mhz']==3500)
    for r in data:
        for key in ['new','reference']:r[key]['contrast_to_center_db']=r[key]['ac_db']-center[key]['ac_db']
        r['contrast_change_db']=r['new']['contrast_to_center_db']-r['reference']['contrast_to_center_db']
    c['checks']['completed_C_reading']=dict(env='outdoor01',el_deg=-60,n=len(data),rows=data,new_spp=c['checks']['budget_design']['new_spp'][0],reference_spp=c['checks']['budget_design']['base_spp'],maximum_shape_change_db=max(abs(r['contrast_change_db']) for r in data),new_ac_span_db=float(np.ptp([r['new']['ac_db'] for r in data])),reference_ac_span_db=float(np.ptp([r['reference']['ac_db'] for r in data])),quality_errors=sum(len(r['reasons']) for r in data))
    save(c);print('completed C raw-data comparison saved',flush=True)

def findings(c):
    x=c['checks'];out=[]
    def add(title,kind,evidence,fix,key,refs):
        out.append(dict(title=title,kind=kind,evidence=evidence,fix=fix,result_key=key,sources=[base.source(p,q) for p,q in refs]))
    a=x['lag1_counterexample'];b=x['lag1_with_low_frequency_component'];r=x['altitude_main_cases'][1]
    add('이웃 상관의 실수부로 날개 신호의 부재를 결론낸다','현재 발간 해석',
        f"생산 함수는 복소 이웃 상관의 실수부를 반환한다. 주기 {a['period_samples']}표본의 결정적 신호에서 반환값은 {abs(a['production_real_lag']):g}이고 복소 상관 크기는 {a['complex_corr_magnitude']:g}이다. 저주파 {b['low_frequency_hz']:.6f} Hz 성분이 전력의 {b['low_frequency_power_share_pct']:.3f}%인 합성 신호도 반환값이 {b['production_real_lag']:g}이다. 실제 실외 자료의 상관이 작다는 관측은 유지되지만, 날개를 따라 흐르는 성분이 없다는 결론은 이 통계에서 나오지 않는다. 합성 반례는 실제 오염 원인을 특정한 결과가 아니다. 리듬 몫도 전체 AC 중 비율이 아니라 날개끝 상한 밖 전력에 조건을 건 비율이므로 표 설명에 분모를 적어야 한다.",
        '열 이름을 정규화된 복소 이웃 상관의 실수부로 적는다. 복소 상관 크기·여러 지연·알려진 날개 위상과의 일관성을 별도로 본다. 발간 문구는 실외와 빈 하늘의 상관 구조 차이까지로 한정하고, 신호 부재와 잡음 종류 판정은 별도 대조에 맡긴다.',
        'checks.lag1_with_low_frequency_component',[('benchmark/read_altitude_0914.py','def lag1_corr'),('benchmark/read_altitude_0914.py','그 몫은 날개를 따라 흐르는 신호가 아니다'),('benchmark/read_altitude_0914.py','above = np.abs(fr) >= f_tip')])
    add('고도 main이 비교 쌍의 실제 표집률 차이를 통과시킨다','합성 입력으로 재현한 잠재 계산 결함',
        f"원장 값은 같은 채 기준 샤드의 표집률만 {r['base_actual_prf']:g} Hz로 바꿔도 생산 main이 {r['accepted_rows']}쌍을 발간했다. 기준 시계열의 올바른 리듬 몫 {r['correct_base_rhythm']:.2f}%를 높은 고도 쪽 표집률로 계산해 {r['published_row']['base_rhythm_share_pct']:.2f}%로 냈다. 양쪽 샤드가 원장과 함께 어긋난 경우도 통과했다. 현재 발간된 실제 고도 자료의 수치 오류를 발견했다는 뜻은 아니다.",
        '각 시계열의 저장 표집률과 해당 원장의 표집률을 대조하고, 비교 쌍의 실제 표집률도 대조한다. 빈 하늘 대조에도 같은 계약을 적용하고 사유를 남긴다. 고도 main 자체를 호출하는 회귀 반례로 유지한다.',
        'checks.altitude_main_cases',[('benchmark/read_altitude_0914.py','Eb, _ = got_b'),('benchmark/read_altitude_0914.py','w = check_series(E, n_poses=n_poses_ledger, prf=prf)')])
    z=x['budget_control_gate']
    add('새 대역 모양 민감도의 대조군은 입력 관문을 우회한다','합성 입력으로 재현한 잠재 비교 결함',
        f"대조군의 원장에 빠진 자세 {z['control_n_missing']}개와 다른 표집률 {z['control_prf_hz']:g} Hz를 기록해도 새 함수는 {z['invalid_controls']['shape_spread_db']:.1f} dB를 그대로 반환했다. 합성 시험은 배열을 고정하고 메타데이터만 바꿨다. 주 곡선에 적용하는 완전성·시간축 계약이 민감도 대조군에는 이어지지 않는다. 이번에 직접 읽은 완료 C 자료의 품질 오류는 {x['completed_C_reading']['quality_errors']}개라, 그 수치를 잘못됐다고 판정하는 지적은 아니다.",
        '예산별 곡선에도 완전성·유한값·세대·실제 표집률 검사를 적용한다. 제외된 예산과 주파수는 사유를 보존하고, 공통으로 통과한 주파수만 비교한다.',
        'checks.budget_control_gate',[('benchmark/read_bandflat_0913.py','def budget_shape_spread_db'),('benchmark/read_bandflat_0913.py','by_budget.setdefault(str(spp), {})')])
    w=x['warehouse'];same=next(t for t in x['altitude_main_cases'] if t['case']=='mixed_solver_builds');pair=next(t for t in x['altitude_main_cases'] if t['case']=='pair_solver_builds_differ')
    add('솔버 버전 기록과 비교 차단이 연결되지 않았다','현재 출처 기록의 한계와 향후 혼합 위험',
        f"샤드 {w['n_files']}개 중 버전 기록이 없는 것은 {w['solver_builds'].get('unrecorded',0)}개다. 새 필드를 쓰는 생산 코드가 있지만 현재 원장 {w['ledger_rows']}행은 그 필드를 아직 제공하지 않는다. 서로 다른 가상 버전의 샤드를 같은 칸에 넣은 main 시험은 {same['accepted_rows']}행, 버전이 다른 비교 쌍도 {pair['accepted_rows']}행을 발간했다. 실제로 새 버전 자료가 섞였다고 발견한 것은 아니다. 기록 없는 과거 자료의 버전을 현재 설치 버전에서 역산하면 출처를 만들어내게 된다.",
        '버전·설정 도장을 병합과 파생 비교까지 전달한다. 기록 없음, 동일 기록, 혼합 기록을 분리하고 혼합 비교에는 명시된 목적과 표시를 요구한다. 버전 전환 비교는 같은 입력·메쉬·실행 설정을 고정한 별도 팔로 유지한다.',
        'checks.warehouse',[('benchmark/elevation_sweep_md.py','def _solver_build'),('benchmark/elevation_sweep_md.py','solver_build=(next(iter(_builds))'),('benchmark/read_altitude_0914.py','bad = [k for k in')])
    z=x['orphan_cleanup_interleaving']
    add('고아 파일 정리가 다른 발간의 살아 있는 임시 파일을 지운다','동시 실행 순서로 재현한 잠재 발간 결함',
        f"임시 디렉터리에서 첫 파일 교체 직후 다른 판독기의 정리를 끼워 넣었다. 살아 있는 임시 파일 {z['removed_active_temps']}개가 삭제돼 다음 교체가 {z['error']}로 끝났다. JSON은 {z['json_value']['v']}, 글은 {z['markdown_value']}로 갈렸다. 전원 중단 없이 정상 정리 함수의 호출만으로도 일어난다. 실제 운영 중 해당 동시 실행이 발생했다고 확인한 것은 아니다.",
        '공유 디렉터리의 임시 파일 전체를 시작 시 삭제하는 처리를 없애거나, 발간과 정리가 공유하는 잠금 아래에서 소유권·실행 생존 여부를 확인한다. 나이만으로 삭제하면 오래 걸리는 정상 발간을 다시 지울 수 있다. 여러 파일 교체의 일관성 한계와 이번 정리 충돌을 별도로 기록한다.',
        'checks.orphan_cleanup_interleaving',[('src/reader_gate.py','def sweep_orphans'),('src/reader_gate.py','if n.startswith(".pub_")'),('benchmark/read_altitude_0914.py','sweep_orphans([os.path.dirname(OUT)')])
    add('기존 감사기의 임시 main 시험이 운영 발간물을 덮는다','이번 실행에서 발생하고 복원한 감사 격리 결함',
        '기존 queue_followup 감사기는 scene의 ROOT만 바꾸고 import 시 정해진 OUT·MD를 남긴다. 장면 main의 조기 반환 오류가 고쳐진 현재는 시험이 정상 발간까지 도달해 운영 파일을 덮는다. 이번 재사용 실행에서 발생해 시작 당시 깨끗했던 HEAD의 두 파일로 바이트 복원했다. 이후 실제 판독기 재실행 비교도 다시 했다. 이 감사 생성기에는 OUT·MD를 임시 경로로 보내는 어댑터를 넣었으며 기존 감사기 원본은 변경하지 않았다.',
        '기존 감사기의 해당 시험에서도 입력·출력 경로를 함께 격리한다. 시험 전후 운영 발간물 해시가 유지되는지를 회귀 조건에 넣는다. 생산 함수 수정 뒤 이전 감사기가 새로 도달하는 쓰기 경로도 점검한다.',
        'checks.audit_isolation_incident',[('benchmark/review_queue_followup_0914.py',"with patch.object(sc,'ROOT',td)"),('benchmark/read_scenephysics_0913.py','publish({OUT: out')])
    weekly='/workspace/Sionna_RT_UAV_RCS_ISAC_weekly_report_2026-09-14.md'
    add('주간 보고서의 정정과 본문·신규성 표현이 갈린다','외부 원문으로 확인한 현재 문면 오류',
        '머리말은 공식 릴리스가 관련 논의를 고쳤다고 명시한다고 정정했지만 본문 결론과 비교표는 여전히 명시를 못 찾았거나 정황이 강하다고 적는다. 공개 논의에 회절을 끈 PathSolver 사례가 없다는 문장도 틀리다. Discussion #1142의 공개 코드는 diffraction과 edge_diffraction을 False로 지정하고 기본 제공 munich 장면을 사용한다. 기존 버전까지 deterministic 인자를 켜는 완전교차 실험표는 지원하지 않는 조합을 포함한다. 역방향 CIR/CFR Doppler 수정이 연구 주제와 가깝다는 사실만으로 현재 정적 경로 합산값이 변한다고 확정할 수도 없다.',
        '정정 본문·요약표·다음 단계의 표현을 함께 교체한다. 공개 사례와 우리 사례의 기하·스위치·관측량·스레드 수 차이를 기여로 제시한다. 버전 비교는 옛 버전 기본값과 새 버전 기본값/결정 모드로 나누고, 각 릴리스 수정의 실제 호출 경로를 확인한 뒤 영향을 기술한다.',
        'external_sources',[(weekly,'라고 명시한 기록은 찾지 못했습니다.'),(weekly,'회절을 꺼도 나는 PathSolver 사례가 없다'),(weekly,'2.0.1 / 2.1.0 × deterministic False/True'),('benchmark/elevation_sweep_md.py','RP.unpack(p, want_doppler=False)')])
    cpu=x['cpu_reproducer']['output']['rows'][0]
    add('한 스레드에서 같다는 결과가 원인 확정으로 쓰인다','현재 시험 머리말과 원장 해석 규칙',
        f"이번 실제 CPU 시험에서도 {cpu['n_reps']}번 모두 경로 수 {cpu['mode_paths']}개, 진폭 편차 {cpu['max_dev_db']:.5f} dB로 같았다. 그러나 thread_ladder의 머리말과 reads_ko는 한 스레드에서 발생률이 영이면 병렬 축약 순서가 원인이라고 적는다. 스레드 수는 실행 순서·커널 실행 방식 등 여러 구현 조건에 영향을 주므로 이 관측만으로 특정 내부 연산을 확정하기에는 근거가 부족하다. 적은 반복에서 같은 값이었다는 사실도 다른 입력 전체의 보장이 아니다.",
        '관측은 시험한 입력과 반복에서 한 스레드 결과가 일치했다고 적는다. 원인 후보는 병렬 실행에 의존하는 처리로 두고, 특정 축약 연산의 대체·계측·동일 후보 집합 대조로 범위를 좁힌다.',
        'checks.cpu_reproducer',[('benchmark/thread_ladder_0903.py','스레드 1 에서 흔들림이 사라지면'),('benchmark/thread_ladder_0903.py','"reads_ko"')])
    return out

def publish_review():
    c=read();c['findings']=findings(c);x=c['checks'];w=x['warehouse'];q=x['queue'];C=x['completed_C_reading'];R=x['report_chain'];j='outputs/remaining_review_0914.json'
    assert all(v['error'] is None and v['published'] for v in x['actual_reader_mains'].values())
    assert all(d['path']=='/_meta/made_utc' for v in x['actual_reader_mains'].values() for d in v['differences'])
    assert R['switch_builder']['error'] is None and R['volumes']['error'] is None
    assert not any(t['semantic_differences'] for t in R['notebooks'])
    assert C['quality_errors']==0
    c['_meta'].update(finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),final_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),scope='All saved shard arrays; selected actual reader main functions; final notebook assembly and switch report rebuild; one CPU reproducer; current queue; weekly report. No fresh GPU solve or full figure/part-builder regeneration.')
    c['external_sources']=[
      dict(url='https://github.com/NVlabs/sionna/discussions/1142',checked_on='2026-09-14',finding='공개 재현 코드가 munich 장면과 diffraction=False, edge_diffraction=False를 쓴다. 페이지는 Closed Unanswered로 표시된다.'),
      dict(url='https://github.com/NVlabs/sionna-rt/releases/tag/v2.1.0',checked_on='2026-09-14',finding='PathSolver 결정 모드와 radio-map wedge 순서 수정에 각각 #1142와 #1175 링크를 명시한다. 역방향 CIR/CFR Doppler와 재료 모델 변경도 별도 항목으로 적는다.'),
      dict(url='https://nvlabs.github.io/sionna/rt/api/paths_solvers.html',checked_on='2026-09-14',finding='공식 PathSolver API는 deterministic=False 기본값과 결정 모드를 문서화한다.')]
    c['checks']['source_quotes_verified']=0
    for f in c['findings']:
        for s in f['sources']:
            assert s['found'],s
            p=Path(s['path']);p=p if p.is_absolute() else ROOT/p
            assert p.read_text().splitlines()[s['line']-1].strip()==s['quote'],s
            c['checks']['source_quotes_verified']+=1
    hashes={**c.get('source_hashes',{}),**base.HASHES};hashes={p:h for p,h in hashes.items() if (ROOT/p).exists()}
    c['checks']['snapshot_changes']=[p for p,h in hashes.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    for p in ['benchmark/review_remaining_0914.py','src/reader_gate.py','src/report_style.py','outputs/elevation_sweep_md.npz']:
        hashes[p]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    c['_meta']['source_sha256']=hashes;c.pop('source_hashes',None)
    good=[r for r in q['records'] if r['state']=='complete'];running=[r for r in q['records'] if r['state']=='running'];pending=[r for r in q['records'] if r['state']=='pending']
    c['queue_assessment']=[
      dict(block='A/B',priority='완료 자료 판독 우선',note='장면 부품과 고도 자료는 DC·AC 절대 전력, 위상 구조, 같은 조건의 빈 하늘 대조를 함께 제시한다. 고도는 환경 전체와 레이다·기체의 상대기하를 바꾼 실험으로 읽는다.'),
      dict(block='C',priority='완료 원자료의 비교를 이번 감사에서 수행',note=f"실외 {C['el_deg']:g}° · {C['n']}개 반송파에서 예산 {C['reference_spp']/1e9:g}B→{C['new_spp']/1e9:g}B 대역 대비 변화 최대 {C['maximum_shape_change_db']:.8f} dB. 현재의 단측 예산 변경과 해당 조건에 한정한 기술 통계다. 주 원장의 선택·완전성 관문을 거쳐 정식 판독에 연결한다."),
      dict(block='D',priority='완료 끝점 자료 활용',note='직하방의 절대 레벨은 판독하고 날개끝 띠 지표의 정의역을 별도로 다룬다. 끝점의 상승과 내부 국소 최대의 유무를 구별한다.'),
      dict(block='E',priority='진행 가치 있음 · 위상 판독 준비',note='알려진 공통 지연 제거, 잔여 지연이 만드는 주파수 간 위상 변화, 전계가 작은 칸의 위상 불안정, 반송파마다 바뀌는 경로 집합을 구분한다. 촘촘한 주파수라는 이유만으로 unwrap 결과를 유일한 지연으로 읽지 않는다.'),
      dict(block='F',priority='진행 가치 있음 · 시간 구간 맞추기',note='표본 수를 고정하고 표집률을 바꾸면 관측 길이와 주파수 분해능도 변한다. 공통 시간 구간과 일치하는 자세를 먼저 비교하고, 별도의 전체 구간 결과를 함께 둔다.'),
      dict(block='G',priority='기존 깊이 비교의 혼합 조건 해소',note='정본 메쉬·같은 스위치의 얕은 깊이 자료가 생기면 이전의 혼합 비교를 대체할 수 있다. 깊이에 따른 잔차와 용도별 허용 오차를 보고한다.')]
    lines=['# 현재 상태와 남아 있던 실행 경로 재점검','',f"시작 HEAD `{c['_meta']['head']}` · 종료 HEAD `{c['_meta']['final_head']}` · 완료 {c['_meta']['finished_utc']}.",'',
      '기존 수정은 실행에서 확인됐다. 이번에는 저장 자료 전체 읽기, 실제 판독기 main, 최종 보고서 조립, CPU 재현기를 추가로 실행했다. 현재 발간 해석과 일부 오류 입력·동시 발간 경로에는 아래 보완점이 남아 있다.','',
      '## 확인한 범위와 통과 결과','',
      f"- 샤드 {w['n_files']:,}개: ZIP 모든 멤버를 읽어 CRC·배열 길이·선언한 자세 분할·유한값 검사. 안정 파일 오류 {len(w['stable_errors'])}개, 읽는 동안 변경 {len(w['changed'])}개. 옛 ours cfg의 규약상 빈 메타데이터는 {w['expected_legacy_cfg_nan']}개로 별도 집계했다.",
      f"- 실제 판독기 main {len(x['actual_reader_mains'])}개를 임시 출력으로 실행했다. 파형·장면의 생성 시각을 제외한 JSON 내용과 대역·고도 JSON 전체가 현재 발간본과 일치했다.",
      f"- 파형 {x['actual_reader_mains']['read_wfsurvive_0912']['collections']['rows']}행 + 제외 {x['actual_reader_mains']['read_wfsurvive_0912']['collections']['skipped']}행 = 원장 {w['ledger_rows']}행. 장면 {x['actual_reader_mains']['read_scenephysics_0913']['collections']['rows']}행, 제외 {x['actual_reader_mains']['read_scenephysics_0913']['collections']['skipped']}행이며 범위 밖은 원장의 별도 집계다.",
      f"- 스위치 보고서 빌더와 최종 권 조립기를 임시 경로로 실행했다. 보고서 {len(R['notebooks'])}개 내용·메타데이터·출력 비교의 차이는 {sum(bool(t['semantic_differences']) for t in R['notebooks'])}개, 바이트까지 같은 것은 {sum(t['bytes_equal'] for t in R['notebooks'])}개다. 셀 ID는 내용 비교에서 제외했다. 최종 색인 차이 {len(R['index_diff'])}개.",
      f"- 기존 입력 반례 {len(x['reader_inputs'])}종을 재실행했다. 정상 자료는 수용하고 표집률 충돌·비유한 전계·잘못된 인덱스·불완전 세대는 거절했다. 병합 어댑터·분류 자가검사·노트북 거절 시 보존도 다시 실행했다.",
      f"- 기존 관문 { {k:v['exit'] for k,v in x['gates'].items()} }. 추가 관문 { {k:v['exit'] for k,v in x['extra_gates'].items()} }.",
      '- freeze의 차이는 창고 파일 수 증가다. 기준선을 갱신하지 않았다. 텍스트 관문의 알려진 우회 모양은 수치→문자열 변환 단계와 함께 검사해야 한다. check_reader_gate 화면의 nan 예시는 발간물 숫자를 치환한 합성 시험 출력이다.','',
      '## 남은 보완점','']
    for i,f in enumerate(c['findings'],1):
        lines += [f"### {i}. {f['title']}",'',f"**분류: {f['kind']}**",'',f['evidence'],'',f"**수정 방향:** {f['fix']}",'',f"원장 키: `{f['result_key']}`",'']
        for s in f['sources']:
            p=Path(s['path']);target=str(p) if p.is_absolute() else '../'+s['path']
            lines.append(f"- [{s['path']}:{s['line']}]({target}) — `{s['quote']}`")
        if f['result_key']=='external_sources':
            lines.append('공식 근거: [공개 재현 코드](https://github.com/NVlabs/sionna/discussions/1142), [릴리스 노트](https://github.com/NVlabs/sionna-rt/releases/tag/v2.1.0), [PathSolver API](https://nvlabs.github.io/sionna/rt/api/paths_solvers.html).')
        lines.append('')
    lines += ['## 완료 C 큐를 새로 읽은 결과','',
      f"조건: {C['env']} · 앙각 {C['el_deg']:g}° · 확산 팔 · 기준과 새 예산의 동일 메쉬·표집률·표본 수. 비교 주파수 {C['n']}개. 선택한 샤드를 직접 읽었고 품질 오류 {C['quality_errors']}개다. 각 예산의 중심 주파수 대비 AC 전력을 만든 뒤 두 곡선을 뺐다.",'',
      '| 반송파 MHz | 기준 예산의 중심 대비 dB | 새 예산의 중심 대비 dB | 대비 변화 dB | 새 칸이 발간 원장에 있나 |','|---:|---:|---:|---:|---|']
    for r in sorted(C['rows'],key=lambda t:t['fc_mhz']):lines.append(f"| {r['fc_mhz']:g} | {r['reference']['contrast_to_center_db']:+.8f} | {r['new']['contrast_to_center_db']:+.8f} | {r['contrast_change_db']:+.8f} | {r['new_cell_in_published_ledger']} |")
    lines += ['',f"예산 {C['reference_spp']/1e9:g}B→{C['new_spp']/1e9:g}B에서 대역 AC 전력 폭은 {C['reference_ac_span_db']:.8f}→{C['new_ac_span_db']:.8f} dB, 대비 변화 최대는 {C['maximum_shape_change_db']:.8f} dB다. 원장에는 새 비교 칸 {sum(r['new_cell_in_published_ledger'] for r in C['rows'])}/{C['n']}개만 들어 있어 기존 대역 main은 이 비교를 아직 구성하지 못한다.",
      '이 수치는 해당 예산 변화에 대한 대역 모양의 민감도다. 신뢰구간·잡음 검정·실제 표적의 대역 평탄성 확인으로 읽지 않는다. 두 예산 간 공통 레벨 이동과 곡선 모양 변화도 구분한다.','',
      '## 현재 큐와 우선순위','',f"관측 {q['checked_utc']} (UTC). 감독자 마지막 상태: `{q['last_status']}`.",f"발주 {q['jobs']}줄 중 완료 안정 샤드 {len(good)}, 실행 중 {len(running)}, 대기 {len(pending)}. 감독자 종료 실패 {q['failed']}, 관측 워커 {len(q['running_processes'])}. 회절·모서리회절 활성 줄 {q['diffraction_enabled']}.",'',
      '| 묶음 | 발주 줄 | 상태 | 완료분 일꾼시간 |','|---|---:|---|---:|']
    for r in q['blocks']:lines.append(f"| {r['block']} | {r['jobs']} | {r['states']} | {r['measured_worker_hours']:.2f} |")
    lines+=['','현재 큐는 계속 진행할 가치가 있다. 완료한 비교를 먼저 판독하고 아직 들어오지 않은 자료에 맞춘 판독 조건을 준비하는 것이 우선이다. 발주 시 총 예상 일꾼시간은 현재 남은 시간과 구별한다.']
    for r in c['queue_assessment']:lines += ['',f"**{r['block']} — {r['priority']}**",'',r['note']]
    lines+=['','## 주간 보고서에 바로 반영할 문장','',
      '> 공식 릴리스 노트는 PathSolver 결정 모드와 radio-map wedge 순서 수정에 관련 공개 논의를 직접 연결한다. 우리의 경로 합산 파이프라인에서 어느 차이가 사라지는지는 같은 입력을 사용한 버전별 재현 시험으로 확인한다.',
      '', '> 공개 논의에는 기본 제공 munich 장면에서 회절을 끈 PathSolver 재현 사례가 있다. 우리 합성 평판·드론 자료의 추가 가치는 서로 다른 기하, 스위치, 후보 규모와 스레드 조건에서 경로 수 및 합산 전계의 변화를 정량화하는 데 있다.',
      '', '> 한 스레드에서 같은 결과를 얻었다는 관측은 시험한 조건의 재현성을 뜻한다. 특정 내부 병렬 연산이 원인이라는 판단에는 그 연산을 바꾼 대조가 추가로 필요하다.',
      '', '> 버전 전환 시험은 옛 버전의 기본 PathSolver와 새 버전의 기본·결정 모드를 비교한다. 재료와 회절 모델 변경은 실제 쓰는 재료·주파수·스위치별로 영향을 계산하고, 역방향 CIR/CFR 수정은 해당 API 사용 여부부터 확인한다.','',
      '## 재현 방법과 남은 범위','',
      f"CPU 재현기: {x['cpu_reproducer']['output']['_meta']['mitsuba_variant']} · 설치 버전 {c['_meta']['installed_versions']}.",
      f"소스 인용 {x['source_quotes_verified']}건을 줄과 문자로 확인했다. 관측 도중 내용 해시가 달라진 기록: {x['snapshot_changes']}.",
      '샤드 검사는 저장 자료의 내부 무결성을 확인한다. 물리적 정확도는 별도 문제다. 실제 RF 계측 대조·새 버전 실행 비교·분류 재학습·모든 조각 빌더와 그림 재렌더링은 이번 실행 범위에 포함하지 않았다. 최종 권 재조립은 이미 생성된 조각을 입력으로 사용했다.',
      '이번 감사의 임시 출력 격리 결함으로 한때 덮인 장면 JSON·Markdown은 초기 HEAD 원본으로 복원했다. 최종 추적 파일 변경은 감사 기록에서 확인할 수 있다. 큐 실행·생산 소스·환경 설치에는 변경을 가하지 않았다. 기존 감사기의 영구 수정은 위 권고로 남겼다.','',
      '```bash',f'{sys.executable} benchmark/review_remaining_0914.py','```','',
      '기존 검사 캐시에서 문서만 다시 만들 때는 --publish를 붙인다. 큐와 창고 파일 수는 재실행 시점에 따라 바뀐다. 외부 웹 확인은 external_sources에 기록한 날짜의 별도 관측이다.']
    OUT.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n');MD.write_text('\n'.join(lines)+'\n')
    from report_style import header,md,next_steps,build_notebook
    cells=[header(num='현재 상태 재점검',title='생산 판독과 완료 큐의 추가 조사',did='저장 샤드·실제 판독기·최종 보고서 조립과 완료 큐 자료를 대조했다.',results=[f"저장 샤드 {w['n_files']}개 전체 배열 검사 ⟨{j} : checks.warehouse⟩.",f"보고서 {len(R['notebooks'])}개 내용 비교 ⟨{j} : checks.report_chain⟩.",f"완료 C 비교 {C['n']}개 주파수 판독 ⟨{j} : checks.completed_C_reading⟩."],method=[('계산','CPU 한 코어와 임시 출력에서 생산 main·합성 반례 실행'),('범위','저장 자료 무결성·소프트웨어 실행·해석 근거 대조')],repro=dict(cmd=[f'{sys.executable} benchmark/review_remaining_0914.py'],out=[j],runtime='CPU 한 코어·저장 자료 검사'))]
    for i,f in enumerate(c['findings']):cells.append(md(f"## {f['title']}",'',f['kind'],'',f"[재현과 수정 방향](REMAINING_REVIEW_0914.md) ⟨{j} : findings[{i}]⟩"))
    for i,r in enumerate(c['queue_assessment']):cells.append(md(f"## 큐 {r['block']} — {r['priority']}",'',f"[자료와 비교 조건](REMAINING_REVIEW_0914.md) ⟨{j} : queue_assessment[{i}]⟩"))
    cells.append(next_steps([('고도와 예산 대조군의 입력 계약을 연결한다','같은 조건 쌍의 수용과 제외 사유','REMAINING_REVIEW_0914.md'),('완료 C 자료를 정식 병합·판독에 연결한다','대역 모양의 예산 민감도','REMAINING_REVIEW_0914.md'),('공유 발간 정리와 감사 출력 경로를 격리한다','운영 발간물 보존','REMAINING_REVIEW_0914.md')]))
    build_notebook(str(NB),cells,strict=True)
    print('review published',len(c['findings']),flush=True)

if __name__=='__main__':
    if '--publish' in sys.argv:publish_review()
    else:
        init();real_readers();altitude_cases();followup();extra_cases();completed_budget_reading();publish_review()
