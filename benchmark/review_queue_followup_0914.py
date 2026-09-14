"""Read-only verification of publication fixes and the active 0930 queue.
Run: /workspace/.venvs/py312/bin/python benchmark/review_queue_followup_0914.py
Uses one CPU; all adverse publication inputs and outputs are temporary.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast,collections,contextlib,hashlib,io,json,math,re,shlex,subprocess,sys,tempfile,time,types
from pathlib import Path
from unittest.mock import patch
import numpy as np
import review_full_0912 as old
base=old.base;ROOT=old.ROOT
sys.path.insert(0,str(ROOT/'src'))
from arm_grammar import parse,unparse
import reader_gate as gate
CACHE=ROOT/'work/queue_followup_0914_cache.json'
OUT=ROOT/'outputs/queue_followup_0914.json'
MD=ROOT/'docs/QUEUE_FOLLOWUP_0914.md';NB=MD.with_suffix('.ipynb')

def save(c):
    c.setdefault('source_hashes',{}).update(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')

def outcome(fn):
    try:return {'result':fn(),'error':None}
    except BaseException as e:return {'error':type(e).__name__,'message':str(e)}

def inputs():
    c={'_meta':{'generator':'benchmark/review_queue_followup_0914.py','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},'checks':{}}
    wf=old.loadmod('benchmark/read_wfsurvive_0912.py');sc=old.loadmod('benchmark/read_scenephysics_0913.py')
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation'];cases=[]
    for case in ['valid','missing','different_prf','second_prf_nan','unresolved_generation','nan_complex64','negative_idx','wrong_meta_n']:
        with tempfile.TemporaryDirectory() as td:
            N=8
            for k in range(0 if case=='missing' else 4 if case=='unresolved_generation' else 2):
                idx=np.arange(k%2,N,2);E=np.full(idx.size,1 if k<2 else 2,dtype=np.complex64);prf=19700.
                if case=='different_prf' and k==1:prf=10000.
                if case=='second_prf_nan' and k==1:prf=float('nan')
                if case=='nan_complex64' and k==0:E[1]=complex(float('nan'),0)
                if case=='negative_idx':idx=idx-N
                meta=[0,k%2,2,N+1 if case=='wrong_meta_n' and k==1 else N,prf,0]
                np.savez(Path(td)/f'arm_el+0_{k:02d}.npz',idx=idx,E=E,meta=meta,t_start=[1700000000.])
            esm=types.SimpleNamespace(SHD=td,one_generation=choose);rec={'case':case}
            with contextlib.redirect_stdout(io.StringIO()):
                if case!='missing':
                    _,note=choose(sorted(str(p) for p in Path(td).glob('*.npz')),'arm/el+0');rec['generation_note']=note
                for name,fn in [('waveform',wf.cell_series),('scene',sc.series)]:
                    try:
                        val=fn(esm,'arm',0,8)
                        if val is None:rec[name]={'return_kind':'bare None','accepted':False}
                        else:rec[name]={'return_kind':'tuple','accepted':val[0] is not None,'reason':val[1], 'samples':np.asarray(val[0][0] if name=='waveform' else val[0]).real.tolist() if val[0] is not None else None}
                    except Exception as e:rec[name]={'error':type(e).__name__,'message':str(e)}
            cases.append(rec)
    c['checks']['reader_inputs']=cases
    # Real scene main, a valid ledger pair with the shard files missing.
    L=base.js('outputs/elevation_sweep_md.json');J=base.js('outputs/read_scenephysics_0913.json');r=J['rows'][0];keys={(r['engine'],r['el_deg']),(r['free_engine'],r['el_deg'])};mini={**L,'rows':[s for s in L['rows'] if (s['engine'],s['el_deg']) in keys]}
    with tempfile.TemporaryDirectory() as td:
        p=Path(td);(p/'outputs').mkdir();(p/'outputs/elevation_sweep_md.json').write_text(json.dumps(mini));esm=types.SimpleNamespace(SHD=td,one_generation=choose)
        # 2026-09-14(4): patch the OUTPUT paths too, not just ROOT.
        # sc.OUT and sc.MD are module-level constants resolved at import time from the
        # REAL root, so patching ROOT alone leaves main() publishing to production.
        # Before the scene reader's early-return bug was fixed this test died before
        # reaching publish(); now it reaches it and overwrote the production artifacts
        # (reproduced 2026-09-14 — outputs/read_scenephysics_0913.json went 83 rows to 0).
        # Guard the run with a before/after hash of every production artifact it could
        # touch, so a future path that escapes isolation fails loudly instead of silently.
        _watch=[Path(base.ROOT)/'outputs/read_scenephysics_0913.json',
                Path(base.ROOT)/'docs/SCENEPHYSICS_0913.md']
        _before={str(w):(hashlib.sha256(w.read_bytes()).hexdigest() if w.exists() else None)
                 for w in _watch}
        with patch.object(sc,'ROOT',td),patch.object(sc,'OUT',str(p/'scene.json')),patch.object(sc,'MD',str(p/'scene.md')),patch.object(sc,'prod',lambda:esm),patch.object(sc,'deck_filters',lambda:(None,None)),contextlib.redirect_stdout(io.StringIO()):
            c['checks']['scene_main_missing']=outcome(sc.main)
        _after={str(w):(hashlib.sha256(w.read_bytes()).hexdigest() if w.exists() else None)
                for w in _watch}
        _touched=[k for k in _before if _before[k]!=_after[k]]
        c['checks']['scene_main_missing']['production_untouched']=not _touched
        c['checks']['scene_main_missing']['production_touched']=_touched
        assert not _touched, f'audit wrote to production artifacts: {_touched}'
    boundary=[]
    for name,kw in [('valid',dict(n_poses=8,prf=19700,prf_seen=[19700])),('infinite_n',dict(n_poses=float('inf'),prf=19700)),('bad_seen',dict(n_poses=8,prf=19700,prf_seen=['bad'])),('seen_disagrees_with_row',dict(n_poses=8,prf=19700,prf_seen=[10000])),('fractional_n',dict(n_poses=8.5,prf=19700))]:
        boundary.append({'case':name,**outcome(lambda kw=kw:gate.check_series(np.ones(8),**kw))})
    c['checks']['series_gate_boundary']=boundary
    # Publication has both numeric and textual domains. Exercise ordinary prose too.
    texts=['NaN 감지','NaN 때문에 제외했다','비유한 값이 4 자세에 있다(NaN·무한)','| 값 |\n| nan |','| 값 |\n| 띠 안 nan · -6.0 dB |','| 값 |\n| h1 nan |','| 값 |\n| **nan** |','| 값 |\n| `nan` |','| 값 |\n| -6.0 dB |']
    pubs=[]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'value.md'
        for s in texts:
            p.write_text('old');rr=outcome(lambda s=s:gate.publish({str(p):s}));pubs.append({'text':s,'rejected':rr['error'] is not None,'old_preserved':p.read_text()=='old','error':rr['error']})
        p.write_text('old');c['checks']['numeric_nan_publish']=outcome(lambda:gate.publish({str(p):{'number':float('nan')}}));c['checks']['numeric_nan_publish']['old_preserved']=p.read_text()=='old'
    c['checks']['text_publish']=pubs
    # Scoping counterexample for new AST boundary checker: sibling local masks global.
    latest=old.loadmod('benchmark/review_latest_readers_0910.py')
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'scope.py';p.write_text('def f():\n return missing\ndef g(missing):\n return missing\n')
        ns={};c['checks']['extract_scope_boundary']=outcome(lambda:bool(latest.functions(str(p),['f','g'],ns)))
        c['checks']['extract_scope_boundary']['call']=outcome(lambda:ns['f']())
        base.HASHES.pop(str(p),None)
    # Rejected notebook preserves the published bytes. Failure injection stays temporary.
    import report_style as rs
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'review.ipynb';p.write_text('old')
        rr=outcome(lambda:rs.build_notebook(str(p),[rs.md('짧은 시험')],strict=True,quiet=True))
        rr.update(old_preserved=p.read_text()=='old',rejected_copy=Path(str(p)+'.rejected.ipynb').exists(),leftover_temps=len(list(Path(td).glob('.nb_*'))));c['checks']['notebook_rejection']=rr
    save(c);print('inputs saved',flush=True)


def corrected():
    c=json.loads(CACHE.read_text());x=c['checks']
    ext=old.loadmod('benchmark/review_extended_0911.py');latest=old.loadmod('benchmark/review_latest_readers_0910.py');repo=old.loadmod('benchmark/review_repository_0911.py')
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'s.npz';np.savez(p,idx=np.arange(8),E=np.ones(8,complex),meta=[0,0,1,8,19700,1],nret=np.full(8,1999980),n_trunc=[0,2000000])
        x['production_merge']=outcome(lambda:ext.production_merge([[p]]))
    x['atlas_extraction']=outcome(latest.atlas_check);print('atlas extraction tested',flush=True)
    x['save_interruption']=outcome(repo.save_interruption)
    sf=old.loadmod('benchmark/switch_factorial.py');J=base.js('outputs/switch_factorial.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz');od=[]
    from drones import DRONES
    for area in ['other_drone_switch_arms','reference_arms']:
        for key,r in J[area].items():
            f=parse(r['arm']);drone=f.get('drone')
            if not drone:continue
            d=DRONES[drone];ff=d.prop_blades*d.hover_rpm/60;E=Z[r['npz_key']];v=sf.columns(E,r['prf_hz'],ff,r['f_tip_hz']);v['rhythm_share_ref_pct']=sf.rhythm_share_ref(E,r['prf_hz'],ff,r['f_tip_hz'])
            od.append({'area':area,'key':key,'mismatch':[k for k,vv in v.items() if r[k]!=vv],'flash_mismatch':r['f_flash_hz']!=round(ff,4)})
    x['other_drone']={'n':len(od),'rows':od,'mismatch':sum(bool(r['mismatch']) or r['flash_mismatch'] for r in od)}
    axes=[dict(axis=ax,**r) for ax,rows in J['axis_diffs'].items() for r in rows];x['factorial']={'pairs':len(axes),'unclean':sum(not r['pair_is_clean'] for r in axes),'rows':axes,'verdict':J['verdict'],'headline':J['headline']}
    tr=ast.parse(base.read('benchmark/switch_factorial.py'));expr=next(k.value for n in ast.walk(tr) if isinstance(n,ast.Call) for k in n.keywords if k.arg=='contains_unit_within_3scale');co=compile(ast.Expression(expr),'production','eval');pc=[]
    for deg in [0,90,180]:
        a=np.exp(1j*np.deg2rad(deg));res=np.full(64,a-1);sig=np.linalg.norm(res)/8/8;_identical=bool(np.linalg.norm(res)==0);_dist=float(abs(a-1));pc.append({'phase':deg,'pass':bool(eval(co,dict(a=a,sig=sig,_identical=_identical,_dist=_dist)))})
    x['phase_cases']=pc
    wf=base.js('outputs/read_wfsurvive_0912.json');sc=base.js('outputs/read_scenephysics_0913.json');L=base.js('outputs/elevation_sweep_md.json')
    def keys(rows):return collections.Counter((r['engine'],r['el_deg']) for r in rows)
    allkeys=keys(L['rows']);wk=keys(wf['rows'])+keys(wf['skipped']);sceneL=[r for r in L['rows'] if parse(r['engine']).get('env') is not None];sk=keys(sc['rows'])+keys(sc['skipped'])
    x['accounting']={'ledger':len(L['rows']),'waveform':len(wf['rows']),'wf_skipped':len(wf['skipped']),'wf_missing':sum((allkeys-wk).values()),'wf_extra':sum((wk-allkeys).values()),'scene_outside':len(L['rows'])-len(sceneL),'scene':len(sc['rows']),'scene_skipped':len(sc['skipped']),'scene_missing':sum((keys(sceneL)-sk).values()),'scene_extra':sum((sk-keys(sceneL)).values()),'nadir_nonnull':sum(r.get('has_tipband') is False and r.get('ref_peak_in_tipband_hz') is not None for r in wf['rows'])}
    classify=old.loadmod('benchmark/switch_to_classification.py');P=base.js('outputs/switch_to_classification.json');print('classification selftest start',flush=True)
    x['classification_selftest']=outcome(lambda:classify.selftest(P))
    toc=old.loadmod('benchmark/build_atlas_toc.py');x['atlas_toc']=outcome(lambda:toc.self_checks(toc.audit()))
    save(c);print('corrected saved',flush=True)

def options(s):
    xs=shlex.split(s);out={};i=0
    while i<len(xs):
        t=xs[i]
        if t.startswith('--'):
            if '=' in t:k,v=t.split('=',1)
            else:k=t;i+=1;v=xs[i]
            out[k]=v
        i+=1
    return out

def queue():
    c=json.loads(CACHE.read_text());jobs=[];block=None
    text=base.read('runners/jobs_0930.txt')
    for line in text.splitlines():
        m=re.match(r'# ── ([A-G]) ',line)
        if m:block=m[1]
        if not line.strip() or line.startswith('#'):continue
        jobs.append(dict(block=block,line=line,args=options(line)))
    proc=subprocess.check_output(['ps','-eo','pid=,etimes=,args='],text=True);running=[]
    for line in proc.splitlines():
        parts=line.strip().split(None,2)
        if len(parts)<3:continue
        cmd=shlex.split(parts[2])
        if len(cmd)>1 and cmd[0].endswith('python') and cmd[1]=='benchmark/elevation_sweep_md.py':running.append({'pid':int(parts[0]),'elapsed_s':int(parts[1]),'args':options(parts[2])})
    records=[];group={};basefields=parse('sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2')
    argmap={'--sw':'switches','--spp':'spp','--n-poses':'n_poses','--max-depth':'max_depth','--range-m':'range_m','--env':'env','--env-alt':'env_alt','--prf':'prf'}
    for job in jobs:
        o=job['args'];f=dict(basefields)
        for arg,key in argmap.items():
            if arg in o:f[key]=o[arg]
        if '--fc-ghz' in o:f['fc']=f"{float(o['--fc-ghz'])*1000:g}"
        arm=unparse(f);assert parse(arm)==f
        el=float(o['--els']);shard=int(o['--shard']);name=f'{arm}_el{el:+g}_{shard:02d}.npz';p=base.SHD/name
        live=next((r for r in running if r['args']==o),None);r={'block':job['block'],'args':o,'arm':arm,'el':el,'shard':shard,'file':name,'running_pid':live['pid'] if live else None,'exists':p.exists()}
        r['state']='running' if live else 'pending';r['quality_errors']=[]
        if p.exists():
            stamp=p.stat()
            if time.time()-stamp.st_mtime<30:r['state']='recent output'
            else:
                with np.load(p,allow_pickle=False) as z:
                    for key in z.files:z[key] # CRC and payload decode
                    ii=z['idx'];E=z['E'];m=z['meta'];expected=np.arange(shard,int(o['--n-poses']),int(o['--nshards']))
                    if not np.array_equal(ii,expected):r['quality_errors'].append('idx')
                    if len(E)!=len(ii) or not np.isfinite(E).all():r['quality_errors'].append('E')
                    if int(m[3])!=int(o['--n-poses']) or abs(float(m[4])-float(o.get('--prf',19700)))>1e-6:r['quality_errors'].append('meta')
                    if int(z['cfg'][2])!=int(o['--spp']):r['quality_errors'].append('spp')
                    nt=z['n_trunc'];nr=z['nret'];r.update(seconds=float(m[5]),nret_max=int(nr.max()),cap=int(nt[1]),near_cap=int((nr>=.99*nt[1]).sum()),samples=len(ii),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                    r['state']='complete' if not r['quality_errors'] else 'invalid'
                    pair=group.setdefault((arm,el),{'E':np.zeros(int(o['--n-poses']),complex),'seen':np.zeros(int(o['--n-poses']),bool),'block':job['block'],'f':f})
                    pair['E'][ii]=E;pair['seen'][ii]=True
                r['changed_while_read']=p.stat().st_mtime_ns!=stamp.st_mtime_ns
        records.append(r)
    log=(ROOT/'runners/logs/sup_jobs_0930.log').read_text();launch=re.findall(r'띄움 #(\d+) pid=(\d+)',log);done=re.findall(r'끝 pid=(\d+) gpu=\d+ rc=(\d+) ([\d.]+)분',log)
    summaries=[]
    for block in 'ABCDEFG':
        rr=[r for r in records if r['block']==block];summaries.append({'block':block,'jobs':len(rr),'states':dict(collections.Counter(r['state'] for r in rr)),'measured_worker_hours':sum(r.get('seconds',0) for r in rr)/3600})
    x=c['checks'];x['queue']={'checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'jobs':len(jobs),'records':records,'blocks':summaries,'launched':len(launch),'finished':len(done),'failed':sum(int(r[1])!=0 for r in done),'running_processes':running,'last_status':next(s for s in reversed(log.splitlines()) if ' 상태 ' in s),'0928_end':(ROOT/'runners/logs/sup_jobs_0928.log').read_text().splitlines()[-1],'done_marker':(ROOT/'runners/logs/queue_chain_0910_done.txt').read_text().splitlines(),'diffraction_enabled':sum(r['args']['--sw'][3]!='0' or r['args']['--sw'][5]!='0' for r in records)}
    # Descriptive contrasts of newly completed cells against the currently published base.
    sf=old.loadmod('benchmark/switch_factorial.py');L=base.js('outputs/elevation_sweep_md.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz');by={(r['engine'],r['el_deg']):r for r in L['rows']};fresh=[]
    def stats(E):
        return dict(mean_magnitude_db=float(20*np.log10(np.mean(abs(E))+1e-300)),dc_power_db=float(10*np.log10(abs(np.mean(E))**2+1e-300)),ac_power_db=float(10*np.log10(np.mean(abs(E-E.mean())**2)+1e-300)))
    for (arm,el),g in group.items():
        if not g['seen'].all():continue
        f=g['f'];target=dict(f)
        target.pop('env_alt',None)
        if g['block']=='A':target.pop('env',None)
        key=unparse(target);npkey=f'{key}/el{el:+g}'
        if npkey not in Z:continue
        a,b=stats(g['E']),stats(Z[npkey]);fresh.append({'block':g['block'],'engine':arm,'el':el,'baseline':key,'new':a,'baseline_values':b,'difference_db':{k:a[k]-b[k] for k in a},'baseline_ledger_missing':by[(key,el)].get('n_missing'),'new_rhythm_share_pct':sf.columns(g['E'],by[(key,el)]['prf_hz'],L['_meta']['f_flash_hz'],by[(key,el)]['f_tip_hz'])['rhythm_share_pct'],'baseline_rhythm_share_pct':sf.columns(Z[npkey],by[(key,el)]['prf_hz'],L['_meta']['f_flash_hz'],by[(key,el)]['f_tip_hz'])['rhythm_share_pct']})
    x['fresh_descriptive']=fresh
    prfs=sorted({19700,*[int(r['args']['--prf']) for r in records if r['block']=='F']});N=int(next(r for r in records if r['block']=='F')['args']['--n-poses']);ff=L['_meta']['f_flash_hz']
    x['sampling_design']=[{'prf':p,'n':N,'duration_s':N/p,'dft_bin_hz':p/N,'flash_cycles':ff*N/p} for p in prfs]
    x['budget_design']={'new_spp':sorted({int(r['args']['--spp']) for r in records if r['block']=='C'}),'base_spp':int(L['_meta'].get('spp',4000000000)),'els':sorted({r['el'] for r in records if r['block']=='C'}),'fcs_mhz':sorted({float(r['args'].get('--fc-ghz',3.5))*1000 for r in records if r['block']=='C'})}
    # Exact translation applied by production helper; do not load solver or scene meshes.
    envsrc=ast.parse(base.read('benchmark/elevation_sweep_md.py'));ns={'os':os,'ENV_SPECS':{'probe':{'alt_m':20,'dir':str(ROOT),'parts':[('ground','m','c'),('building','m','c')]}},'_ENV_ALT':[80]};node=next(n for n in envsrc.body if isinstance(n,ast.FunctionDef) and n.name=='env_parts');exec(compile(ast.Module(body=[node],type_ignores=[]),'env_parts','exec'),ns)
    with patch('os.path.exists',lambda p:True):x['alt_translation']=ns['env_parts'](lambda **kw:kw,'probe')
    save(c);print('queue saved',flush=True)

def depth_audit():
    c=json.loads(CACHE.read_text());j=base.js('outputs/switch_factorial.json');rows=[]
    for r in j['depth_pairs']:
        a,b=j['cells'][r['d1']],j['cells'][r['dN']];fa,fb=parse(a['arm']),parse(b['arm']);diff={k:[fa.get(k),fb.get(k)] for k in ['mesh_fix','blade_law'] if fa.get(k)!=fb.get(k)}
        rows.append(dict(row=r,mesh_difference=diff,arm1=a['arm'],armN=b['arm']))
    c['checks']['depth_comparisons']={'n':len(rows),'mesh_mixed':sum(bool(r['mesh_difference']) for r in rows),'rows':rows,'unmeasurable_rhythm_counted_fail':sum(r['row']['d_rhythm_pp'] is None and r['row']['pass'] is False for r in rows)}
    # Counts are generated from actual tests, rather than assuming published metadata is complete.
    c['checks']['queue']['stable_complete_quality_errors']=sum(bool(r['quality_errors']) for r in c['checks']['queue']['records'] if r['state']=='complete')
    save(c)

def ray_control():
    c=json.loads(CACHE.read_text());b=old.loadmod('benchmark/read_bandflat_0913.py');j=base.js('outputs/bandflat_0913.json');s=next(r for r in j['series'] if r['env']=='free' and r['el_deg']==-30)
    fcs=s['fc_mhz'];levels=np.array(s['moving_db']);n=128;t=np.arange(n)/n;rows=[]
    class Arrays(dict):
        @property
        def files(self):return list(self)
    z=Arrays();curves=[]
    for budget,offset in [(4000000000,0.),(3900000000,1.)]:
        curve=[]
        for fc,level in zip(fcs,levels):
            f=parse(b.arm_name('free',fc));f['spp']=str(budget);arm=unparse(f);E=np.exp(2j*np.pi*t)*10**((level+offset)/20);z[f'{arm}/el-30']=E;rows.append({'engine':arm,'el_deg':-30});curve.append(float(10*np.log10(np.mean(abs(E-E.mean())**2))))
        curves.append(curve)
    spread,num=b.ray_spread_db(b.arm_name('free',3500),-30,rows,z);d=[np.array(v)-v[fcs.index(3500)] for v in curves]
    # 2026-09-14(4): this audit used to die here with StopIteration.
    # It looked for the literal production node `mv_band > 2.0 * ray_spread`, which this
    # very finding caused to be removed - the band verdict no longer compares the band
    # spread against the CENTRE CARRIER's level sensitivity at all. An audit that dies
    # when its finding is acted on cannot re-bake its own ledger, so record the state
    # instead of raising.
    tree=ast.parse(base.read('benchmark/read_bandflat_0913.py'))
    expr=next((node for node in ast.walk(tree) if isinstance(node,ast.Compare) and ast.unparse(node)=='mv_band > 2.0 * ray_spread'),None)
    if expr is None:
        verdict=None
        threshold_state='removed — production no longer thresholds the band spread against the centre-carrier level sensitivity'
    else:
        verdict=bool(eval(compile(ast.Expression(expr),'production threshold','eval'),{'mv_band':float(np.ptp(curves[0])),'ray_spread':spread}))
        threshold_state='present'
    # What production uses now, if anything, so the ledger says which ruler was read.
    shape_fn=any(isinstance(nd,ast.FunctionDef) and nd.name=='budget_shape_spread_db' for nd in ast.walk(tree))
    c['checks']['ray_control']={'current_series':j['series'],'counterexample':{'frequencies_mhz':fcs,'n_samples':n,'curves_db':curves,'constant_budget_offset_db':1.,'production_ray_spread_db':spread,'production_n_points':num,'band_spread_db':float(np.ptp(curves[0])),'production_says_larger':verdict,'production_threshold_state':threshold_state,'production_has_band_shape_statistic':shape_fn,'maximum_change_in_frequency_contrast_db':float(np.max(abs(d[0]-d[1]))),'scope':'Synthetic common offset; disproves general implication, does not establish physical correctness of existing curves.'}}
    save(c)


def findings(c):
    x=c['checks'];fs=[]
    def add(title,kind,evidence,fix,key,refs):
        fs.append(dict(title=title,kind=kind,evidence=evidence,fix=fix,result_key=key,sources=[base.source(p,n) for p,n in refs]))
    sc='benchmark/read_scenephysics_0913.py';wf='benchmark/read_wfsurvive_0912.py';g='src/reader_gate.py';sf='benchmark/switch_factorial.py'
    add('장면 판독기의 조기 반환이 실제 main에서 다시 예외를 낸다','재현한 입력 처리 결함',
        f"유효한 원장 비교 쌍을 두고 샤드만 비운 임시 실행에서 생산 main은 {x['scene_main_missing']['error']}: {x['scene_main_missing']['message']}로 끝났다. series는 자료 없음·표집률 혼합·불완전 커버리지에서 None 하나를 반환하지만 main은 항상 두 값으로 푼다. 정상 자료의 행 수가 닫히는 것과 오류 입력 처리의 완결성은 별개다.",
        'series의 모든 반환을 (전계 또는 None, 사유 목록)으로 통일하고 실제 main에서 자료 없음·미완성·표집률 혼합을 각각 재현한다.',
        'checks.scene_main_missing / checks.reader_inputs',[(sc,'def series('),(sc,'Es, why_s = series')])
    conf=next(r for r in x['reader_inputs'] if r['case']=='unresolved_generation')
    add('두 raw 판독기가 세대 충돌과 샤드 메타데이터 이상을 여전히 통과시킨다','기존 지적 잔존 · 임시 반례',
        f"세대 선택 결과 kept_conflicting_poses={conf['generation_note']['kept_conflicting_poses']}인데 두 판독기 모두 뒤쪽 파일의 전계로 덮고 통과했다. 두 번째 샤드의 NaN 표집률, 음수 idx, 서로 다른 meta 표본수도 통과했다. 이유는 선택 진단을 버리고, 첫 파일에서만 크기·표집률을 취하며, idx를 배열에 대입한 뒤 유한성만 확인하기 때문이다. 음수 idx는 NumPy에서 끝 기준 인덱스이므로 예외 없이 잘못된 저장을 허용한다. 현재 실제 창고에서 이 합성 오류가 발생했다고 판정한 것은 아니다.",
        'one_generation의 남은 충돌 진단을 확인하고 모든 샤드의 idx 범위·정수성·중복·meta 표본수·유한 양수 표집률을 대입 전에 대조한다. 명시적으로 해결된 세대 선택까지 일괄 거절하는 처방은 피한다.',
        'checks.reader_inputs',[(wf,'fs, _ = esm.one_generation'),(sc,'fs, _ = esm.one_generation'),(wf,'E[ii] = z["E"]'),(sc,'elif abs(_p - prf0) > 1.0')])
    add('발간 텍스트 관문은 정상 문장을 거절하고 다른 표기 값은 통과시킨다','새 관문의 양방향 반례',
        '실제 publish가 “NaN 감지”와 “NaN 때문에 제외했다”를 거절했다. 반대로 표 칸의 “h1 nan”, 굵게 표시한 nan, 코드 서식의 nan은 발간했다. 사용자가 보고한 혼합 칸 “띠 안 nan · -6.0 dB”는 올바르게 거절한다. 그 수정의 성공과 모든 표기에서의 판정 완결성은 구분해야 한다.',
        '숫자는 구조화된 원장에서 유한성을 검증하고, 표 렌더러가 숫자·없음·사유를 구분해 출력하게 한다. 텍스트 검사는 보조 검사로 두고 숫자 꼬리표와 Markdown 서식 처리, 정상 사유 문장의 허용을 명시한다.',
        'checks.text_publish',[(g,'if any(c.isdigit() for c in pre)'),(g,'if len(post) > 8'),(g,'for part in _PART_SPLIT.split(cell)')])
    add('공통 입력 관문의 예외 없는 반환 약속에도 경계 누락이 있다','잠재 입력 처리 결함',
        'n_poses=무한대는 OverflowError, prf_seen에 문자가 있으면 ValueError를 낸다. 원장 PRF와 유일한 prf_seen 값이 서로 달라도 통과하며, 소수인 표본수는 int로 잘려 실제 정수 길이와 같으면 통과한다. 정상 자료의 결과가 틀렸다는 뜻은 아니지만 입력 관문 자체의 계약을 좁히거나 구현을 보완해야 한다.',
        '정수 표본수와 유한 양수 표집률을 변환 전후로 검증하고, prf_seen 전체를 원장의 prf와 대조한다. 변환 실패는 사유로 반환한다.',
        'checks.series_gate_boundary',[(g,'want = int(n_poses)'),(g,'seen = sorted({float(x) for x in prf_seen})')])
    add('추출 경계 검사가 서로 다른 함수의 지역변수를 합쳐 누락을 가린다','잠재 감사 결함 · 합성 소스로 재현',
        'f()가 미제공 전역 missing을 읽고 g(missing)는 같은 이름의 인자를 받을 때 새 functions 경계 검사는 통과한다. 그 후 f() 실행에서 NameError가 난다. 현재 atlas_check와 production_merge의 원래 누락은 고쳐져 실행되지만, 새 검사가 향후 같은 유형의 누락을 전부 잡는다는 보장은 없다.',
        '함수별 스코프를 구분해 전역·자유 이름을 검사하고, 다른 함수의 매개변수나 지역 대입이 의존성을 제공한 것으로 집계되지 않게 한다.',
        'checks.extract_scope_boundary',[('benchmark/review_latest_readers_0910.py','assigned, readn = set(), set()'),('benchmark/review_latest_readers_0910.py','elif isinstance(n,ast.arg)')])
    d=x['depth_comparisons'];v=x['factorial']['verdict']
    add('조건 혼합 관문이 깊이 비교에 전파되지 않았다','현재 발간 비교의 해석에 영향',
        f"depth_pairs {d['n']}쌍 중 {d['mesh_mixed']}쌍은 mesh_fix 또는 blade_law가 다르지만 혼합 표시 없이 깊이 판정으로 들어간다. 계측 불가인 리듬 값 None을 실패 False로 집계한 행도 {d['unmeasurable_rhythm_counted_fail']}개다. 예를 들어 직하방은 해당 띠가 퇴화하므로 물리적 깊이 민감도 실패와 계측 불가를 구분해야 한다. 새 스위치 조건 관문은 적용됐지만 이 별도 루프에는 적용되지 않았다.",
        '깊이 외 조건이 같은 쌍을 구성하고 비교 부적격·계측 불가·기준 초과를 분리한다. G 큐가 채우는 정본 깊이 자료로 해당 쌍을 다시 구성한다.',
        'checks.depth_comparisons',[(sf,'a, b = cells[k1], cells[k3]'),(sf,'row["rhythm_within_3pp"] = bool')])
    add('수정된 판정과 옛 확정 문장이 현재 완전요인 원장에 공존한다','현재 발간 문면의 잔존 오류',
        f"복소 거리와 같은 조건 쌍을 쓰는 새 판정은 확인됐다. 현재 주판정에 쓰는 유효 쌍은 {v['A_cover_n_pairs']}개다. 그러나 A_headline_ko는 제외된 옛 기본 비교의 계수 0.92(±0.04), 잔차 11.8%(백색)를 계속 머리기사로 쓴다. E_axis_mechanism의 항목별 reads_ko는 바꾼다고 쓰면서 E_axis_mechanism_ko는 D·E·F가 얹는 축이라고 단정한다. 현재 원문의 전체 값은 checks.factorial에 보존했다.",
        '머리기사·기작 설명·적용 범위를 현재 사용한 비교 쌍과 판정에서 함께 생성한다. 가정 척도 통과와 물리적 기작 입증을 구분하고, 백색잡음 단정도 동일한 규칙으로 정정한다.',
        'checks.factorial.verdict / checks.factorial.headline',[(sf,'verdict["A_headline_ko"] = ('),(sf,'E_axis_mechanism=mech, E_axis_mechanism_ko=mech_note')])
    add('아틀라스의 기본 기체 명시 태그 검사가 여전히 오경보를 낸다','검사 문면 보완',
        '팔별 반송파·프로펠러 배율 검사와 최신 색인 규모는 맞는다. 다만 기본 기체 matrice4e를 이름에 명시한 팔까지 기본 박자와 달라야 한다는 검사가 남아 실패한다. 원장 박자 정수배 검사의 불일치와 이 검사식 자체의 오경보는 서로 다른 문제다.',
        '기체별 명세 값과 직접 비교하고 기본 기체와 달라야 한다는 조건은 실제로 다른 박자를 가진 기체에만 적용한다.',
        'checks.atlas_toc',[('benchmark/build_atlas_toc.py','기체 태그 팔의 박자가 원장 기본값과')])
    rc=x['ray_control']['counterexample']
    add('대역 판독기가 중심 주파수 레벨 민감도를 대역 모양의 판정 문턱으로 쓴다','현재 판정 설계와 큐 C 활용의 결함',
        f"현행 main은 중심 반송파만 ray_spread_db에 넘기고 대역 퍼짐이 그 값의 두 배를 넘는지로 크다/묻힌다를 나눈다. 주파수별 곡선이 동일하고 예산 변경이 공통 레벨만 {rc['constant_budget_offset_db']:g} dB 이동시키는 합성 반례에서 주파수 대비 변화는 {rc['maximum_change_in_frequency_contrast_db']:.3g} dB인데 생산 판정은 크다={rc['production_says_larger']}다. 이는 현재 자료의 물리적 정확도를 증명하는 반례가 아니라, 중심 레벨 변화로 대역 모양의 식별 가능성을 판정하는 일반 논리의 반례다. C가 새로 사는 비중심 주파수 예산 쌍도 현재 대조 통계에는 들어가지 않는다.",
        '각 예산의 동일 주파수 쌍으로 대역 대비 곡선과 그 변화량을 계산한다. 민감도 기술 통계와 판정 문턱을 구분하고 가정 없는 두 배 기준의 확정 표현을 제거한다.',
        'checks.ray_control',[('benchmark/read_bandflat_0913.py','ray_spread, ray_n = ray_spread_db'),('benchmark/read_bandflat_0913.py','if mv_band > 2.0 * ray_spread else')])
    return fs


def render(c):
    x=c['checks'];a=x['accounting'];q=x['queue'];j='outputs/queue_followup_0914.json';sd=x['sampling_design'];bd=x['budget_design']
    good=x['other_drone'];cl=x['classification_selftest']['result'];dep=x['depth_comparisons'];t=x['fresh_descriptive'];br=[r for r in t if r['block']=='A' and 'bldg' in r['engine']]
    b=next(r for r in t if r['block']=='B' and r['el']==-60 and 'envoutdoor01_alt80_' in r['engine'])
    queue_notes=[
      ('A','조각 장면·굴절','유용 · 완료 자료부터 판독',f"건물만 둔 굴절 팔 {len(br)}칸의 빈 하늘 대비 평균 진폭 dB 차이는 절댓값 최대 {max(abs(r['difference_db']['mean_magnitude_db']) for r in br):.7f} dB다. 두 자리 반올림 영과 정확한 영을 구분한다. 건물 단독 효과가 작다는 사실로 전체 장면에서 건물의 역할까지 영이라고 단정하면 지면·건물 상호작용을 놓친다."),
      ('B','고도','유용 · 판정 문장 수정',f"생산 구현은 드론만 올리는 대신 환경 부품 전체를 수직 이동한다. 상대기하 실험으로 읽어야 한다. 실외 el {b['el']:g}°·고도 80 대 기본 20 m에서 DC 전력 {b['difference_db']['dc_power_db']:+.3f} dB, AC 전력 {b['difference_db']['ac_power_db']:+.3f} dB인데 리듬 몫은 {b['baseline_rhythm_share_pct']:.2f} → {b['new_rhythm_share_pct']:.2f}%다. 비율이 비슷해도 절대 바닥은 크게 변한다. ‘리듬 몫이 널 근처면 지면 탓이 아니다’는 판정은 성립하지 않는다."),
      ('C','광선 예산·대역','우선 판독 가치 높음',f"실제 새 예산은 {bd['new_spp']}, 앙각은 {bd['els']}°뿐이다. 기준 {bd['base_spp']}에서 한쪽으로 줄인 비교로, ± 변동이나 다른 앙각까지의 사다리는 아니다. 각 예산의 주파수 대비 D(f)=L(f)−L(f중심)를 먼저 만들고 D새−D기준을 비교한다. 개별 칸의 공통 레벨 이동으로 대역 기울기를 곧바로 거절하지 않는다. 이 비교는 결정적 격자 민감도이며 신뢰구간이 아니다."),
      ('D','직하방 끝점','범위 확장에 유용',"직하방의 레벨을 읽고 날개끝 띠 지표는 계측 불가로 둔다. 끝점에서 값이 다시 증가해도 기존 내부 국소 최대의 존재가 사라지는 것은 아니다. 곡선 형상 관측으로 쓴다."),
      ('E','촘촘한 반송파·위상','필요하지만 판독 설계가 선행돼야 함',"자료가 오기 전에도 알려진 단일 지연·복수 지연·상쇄점을 합성해 지연 제거와 감김 복원의 조건을 시험할 수 있다. 알려진 공통 지연을 먼저 제거하고, 작은 전계에서 불안정한 위상·경로 집합 변화·잔여 지연 범위를 구분한다. 간격이 촘촘하다는 사실만으로 복원 가능성이 보장되지 않는다. C와 새 주파수 조건이 같은지도 확인한다."),
      ('F','표집률','가치 있음 · 동일 시간 구간 비교 필수',f"표본수는 {sd[0]['n']}로 고정이다. PRF를 {sd[0]['prf']} → {sd[-1]['prf']} Hz로 바꾸면 관측 시간 {sd[0]['duration_s']:.6f} → {sd[-1]['duration_s']:.6f} s, DFT 간격 {sd[0]['dft_bin_hz']:.6f} → {sd[-1]['dft_bin_hz']:.6f} Hz, 날개 통과 주기 {sd[0]['flash_cycles']:.3f} → {sd[-1]['flash_cycles']:.3f}개가 된다. 시간 길이·분해능이 함께 변한다. 공통 시간 구간과 일치하는 자세 시각을 비교하고 넓은 스펙트럼만으로 독립 잡음을 판정하지 않는다."),
      ('G','굴절 깊이 1','비용 대비 우선 가치 높음',f"현재 깊이 비교의 메쉬 혼합 {dep['mesh_mixed']}/{dep['n']} 문제와 연결된다. 정본 깊이 1 자료를 채운 뒤 같은 조건 쌍으로 바꿔 읽는다. 깊이 차이가 ‘같은 자릿수’라는 것만으로 수렴했다고 판정하지 말고 실제 잔차와 사용 목적에 필요한 오차를 함께 제시한다.")]
    c['queue_assessment']=[dict(block=a,topic=b,priority=d,assessment=e) for a,b,d,e in queue_notes]
    lines=['# 수정 재검증과 0930 큐의 조사 가치','',f"시작 HEAD `{c['_meta']['head']}` · 종료 HEAD `{c['_meta']['final_head']}`.",f"완료 시각: {c['_meta']['finished_utc']}. 큐 관측 시각: {q['checked_utc']} (UTC). 감독자 로그의 로컬 시각은 별도로 그대로 보존했다.",'',
      '## 판단','',
      '주요 수정은 실행과 수치로 확인됐다. 다만 오류 입력의 조기 반환·샤드 진단·텍스트 관문·파생 비교에는 남은 결함이 있어 전체 종료로 묶기는 이르다. 큐는 조사할 가치가 있으며, 완료된 자료의 판독과 비교 조건 정리가 다음 실험 추가보다 먼저다. 실기 정확도의 확인과 이번 소프트웨어 회귀 재현은 구분한다.','',
      '## 확인된 수정','',
      f"- 분류 자가검사: {cl['reproduces_switch_factorial']['detail_ko']}",
      f"- 기체별 보조 표: {good['n']}행에서 현재 기체별 계산과 발간 열의 불일치 {good['mismatch']}행. f_flash의 저장 반올림을 적용해 대조했다.",
      f"- 파형 원장: {a['ledger']} = {a['waveform']} + {a['wf_skipped']}. 행 정체성으로도 빠진 것 {a['wf_missing']}, 추가·중복 {a['wf_extra']}.",
      f"- 장면 원장: {a['ledger']} = 범위 밖 {a['scene_outside']} + {a['scene']} + {a['scene_skipped']}. 대상 행의 누락 {a['scene_missing']}, 추가·중복 {a['scene_extra']}.",
      f"- 직하방의 띠 전용 봉우리 누출: {a['nadir_nonnull']}행.",
      '- production_merge·atlas_check·저장 중단 시험이 현재 의존성으로 실행된다. 저장 중단은 의도한 OSError를 내며 불완전 파일을 재개 완료로 인정하지 않는다.',
      f"- 복소 계수 시험: {x['phase_cases']}. 동일 신호와 위상 회전 신호의 판정이 수정됐다.",
      f"- 노트북 거절 반례: 기존 파일 보존 {x['notebook_rejection']['old_preserved']}, 거절본 보존 {x['notebook_rejection']['rejected_copy']}, 임시 파일 잔존 {x['notebook_rejection']['leftover_temps']}.",
      f"- 기존 관문 결과: { {k:v['exit'] for k,v in x['gates'].items()} }. 이 통과가 아래 합성 반례나 해석 문제까지 검사했다는 뜻은 아니다.",'',
      '## 남은 보완점','']
    for i,f in enumerate(c['findings'],1):
        lines += [f"### {i}. {f['title']}",'',f"**분류:** {f['kind']}",'',f['evidence'],'',f"**권고:** {f['fix']}",'',f"원장: `{j}` → `{f['result_key']}`",'']
        lines += [f"- [{s['path']}:{s['line']}](../{s['path']}#L{s['line']}) — `{s['quote']}`" for s in f['sources']];lines.append('')
    lines += ['## 큐 현황','',q['0928_end'],'',f"0930은 {q['jobs']}줄 중 시작 {q['launched']}, 종료 {q['finished']}, 종료코드 실패 {q['failed']}다. 실제 워커 프로세스 {len(q['running_processes'])}개. 회절·모서리회절 활성 줄은 {q['diffraction_enabled']}개다.",
      'queue_chain_done은 완료 증명이 아니라 시작 확인 또는 포기 처리 표식이다. 이 파일에 0930이 있어도 진행 중일 수 있다. 실제 상태는 감독자 종료 기록·프로세스·샤드 내용을 대조했다.','',
      '| 묶음 | 전체 줄 | 상태 | 완료 자료의 일꾼시간 |','|---|---:|---|---:|']
    for r in q['blocks']:lines.append(f"| {r['block']} | {r['jobs']} | {r['states']} | {r['measured_worker_hours']:.2f} |")
    complete=[r for r in q['records'] if r['state']=='complete']
    lines += ['',f"완료 안정 샤드 {len(complete)}개에서 CRC·배열 길이·idx 분할·유한 전계·meta·예산을 확인했다. 품질 오류 {q['stable_complete_quality_errors']}개, 현재 규칙으로 상한 근접한 자세 {sum(r.get('near_cap',0) for r in complete)}개. 이 상한 근접 진단이 후보 생성의 무손실 증명은 아니다.",
      '141 일꾼시간은 발주 당시 장면별 단가에 따른 계획값이며 현재 남은 시간이 아니다. 실제 처리시간은 표에 별도로 기록했다. 병렬 자원·장면별 시간 차이 때문에 나눗셈만으로 완료 시각을 확정하지 않는다.','',
      '## 큐를 어떻게 읽을 것인가','']
    for k,topic,priority,note in queue_notes:lines += [f"### {k}. {topic} — {priority}",'',note,'']
    lines += ['## 완료된 새 자료의 관측','',
      '아래는 저장 전계를 idx로 합친 기술 통계다. 외부 계측, 경로 기여의 인과 분해, 공식 발간 갱신을 대신하지 않는다. 평균 크기의 dB와 평균 제거 전력의 dB를 구분했다.','',
      '| 묶음 | 팔 | 앙각 | 기준 대비 평균 크기 dB | 기준 대비 DC 전력 dB | 기준 대비 AC 전력 dB | 리듬 몫 기준→새 % |','|---|---|---:|---:|---:|---:|---|']
    for r in t:lines.append(f"| {r['block']} | `{r['engine']}` | {r['el']:g} | {r['difference_db']['mean_magnitude_db']:+.6f} | {r['difference_db']['dc_power_db']:+.6f} | {r['difference_db']['ac_power_db']:+.6f} | {r['baseline_rhythm_share_pct']} → {r['new_rhythm_share_pct']} |")
    lines += ['', '기준 팔과 원정밀도는 checks.fresh_descriptive에 있다. 고도 비교의 기준은 같은 환경의 기본 고도이며, A 비교의 기준은 같은 스위치의 빈 하늘이다.','',
      '## 여러 파일의 발간과 실기 대조에 대한 의견','',
      '파일별 원자성과 여러 파일을 묶은 일관성을 구분한 설명은 맞다. 다만 디렉터리 통째 교체만이 해법은 아니다. 세대별 불변 파일과 마지막에 원자적으로 바꾸는 manifest 포인터를 쓰면 독자가 한 세대만 읽게 할 수 있다. 가벼운 보완은 JSON·문서에 같은 build_id와 입력 해시를 남겨 혼합을 검출하는 것이다. 후자는 감지책이며 여러 파일의 원자성을 제공하지 않는다.',
      '실기 계측 부재는 현실 정확도와 기작 입증의 한계다. 입력 관문 통과·특정 반례 재현·생산 함수와의 수치 일치까지 모두 같은 말로 지우기보다, 무엇을 확인했는지 범위를 붙여 적는 편이 정확하다.','',
      '## 재현 범위와 산출물','',
      f"인용 {c['checks']['source_quotes_verified']}개를 줄·문자로 확인했다. 입력 해시 변경: {c['checks']['snapshot_changes']}.",
      '이번 범위는 최신 수정·명시된 생산 함수·임시 반례·현재 큐의 안정 완료 샤드다. 전체 과거 샤드 재검사나 실기 시험은 하지 않았다. 분류 전체 학습을 다시 실행한 것이 아니라 저장된 결과를 대상으로 현재 selftest를 실제 실행했다. 전체 보고서 묶음의 바이트 동일 재빌드는 별도로 실행하지 않았다.',
      '생산 코드·기존 발간물·큐 순서는 바꾸지 않았다. 새 감사 생성기·JSON·Markdown·Jupyter와 검사 캐시를 남겼다. 작업 중 늘어난 큐 로그와 샤드는 다른 실행 작업의 산출물이다.','',
      '```bash',f'{sys.executable} benchmark/review_queue_followup_0914.py','```','',
      '캐시에서 문서만 생성하려면 `--publish`를 붙인다. 큐 스냅샷은 매 실행 시점의 값이다.','']
    MD.write_text('\n'.join(lines))
    from report_style import header,md,next_steps,build_notebook
    cells=[header(num='수정과 큐 점검',title='수정 재현과 진행 중 실험의 해석 범위',did='현재 생산 함수·발간 행·임시 반례와 완료 샤드를 대조했다.',results=[f"기체별 보조 표 {good['n']}행 재현 ⟨{j} : checks.other_drone⟩.",f"파형 {a['waveform']}행과 제외 사유 대조 ⟨{j} : checks.accounting⟩.",f"현재 큐 시작 {q['launched']}줄·종료 {q['finished']}줄 ⟨{j} : checks.queue⟩."],method=[('수정','함수 실행·임시 실패 입력·발간 행 정체성 대조'),('큐','실행 조건·완료 샤드·관측 통계')],repro=dict(cmd=[f'{sys.executable} benchmark/review_queue_followup_0914.py'],out=[j],runtime='CPU 한 코어·저장 자료 읽기'))]
    for i,f in enumerate(c['findings']):cells.append(md(f"## {i+1}. {f['title']}",'',f['fix'],'',f"[재현과 코드 인용](QUEUE_FOLLOWUP_0914.md) ⟨{j} : findings[{i}]⟩"))
    for i,(k,topic,priority,note) in enumerate(queue_notes):cells.append(md(f"## 큐 {k}. {topic}",'',priority,'',f"[설계·관측 근거](QUEUE_FOLLOWUP_0914.md) ⟨{j} : queue_assessment[{i}]⟩"))
    cells.append(next_steps([('반환 계약·샤드 관문을 완성한다','입력 오류 처리의 일관성','QUEUE_FOLLOWUP_0914.md'),('완료 A·B와 진행 C·G를 우선 판독한다','동일 조건의 관측과 민감도','QUEUE_FOLLOWUP_0914.md'),('E·F 판독을 합성 신호로 미리 시험한다','위상·시간 구간·분해능 조건','QUEUE_FOLLOWUP_0914.md')]))
    # Source footnotes resolve queue_assessment from JSON, so persist that generated table first.
    OUT.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')
    build_notebook(str(NB),cells,strict=True)


def publish():
    c=json.loads(CACHE.read_text());c['findings']=findings(c);c['_meta']['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());c['_meta']['final_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    hashes=dict(c.get('source_hashes',{}));hashes.update(base.HASHES)
    for p in ['benchmark/review_queue_followup_0914.py','src/reader_gate.py','src/report_style.py','outputs/elevation_sweep_md.npz']:
        with (ROOT/p).open('rb') as f:hashes[p]=hashlib.file_digest(f,'sha256').hexdigest()
    c['checks']['queue']['stable_complete_quality_errors']=sum(bool(r['quality_errors']) for r in c['checks']['queue']['records'] if r['state']=='complete')
    c['_meta']['source_sha256']=hashes;c.pop('source_hashes',None);c['checks']['snapshot_changes']=[]
    for p,h in hashes.items():
        path=Path(p) if Path(p).is_absolute() else ROOT/p
        with path.open('rb') as f:now=hashlib.file_digest(f,'sha256').hexdigest()
        if now!=h:c['checks']['snapshot_changes'].append(p)
    for f in c['findings']:
        for s in f['sources']:
            assert s['found'],s
            assert (ROOT/s['path']).read_text().splitlines()[s['line']-1].strip()==s['quote'],s
    c['checks']['source_quotes_verified']=sum(len(f['sources']) for f in c['findings'])
    OUT.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n');render(c)
    print('published',len(c['findings']),'findings; changed source hashes',c['checks']['snapshot_changes'],flush=True)

if __name__=='__main__':
    if '--publish' in sys.argv:publish()
    else:
        inputs();corrected();queue();depth_audit();ray_control()
        c=json.loads(CACHE.read_text());c['checks']['gates']=old.gates();save(c);publish()
