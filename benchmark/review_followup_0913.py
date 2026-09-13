"""Verify the claimed follow-up fixes and audit newly affected comparisons.
Run: python benchmark/review_followup_0913.py
CPU only. Live production files are read-only; adverse inputs and outputs are temporary.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast,collections,contextlib,copy,hashlib,io,json,re,subprocess,sys,tempfile,time,types
from pathlib import Path
from unittest.mock import patch
import numpy as np
import review_full_0912 as old
base=old.base;repo=old.repo;ROOT=old.ROOT
sys.path.insert(0,str(ROOT/'src'))
from arm_grammar import parse,unparse
import md_mapstyle as mp
OUT=ROOT/'outputs/followup_review_0913.json';MD=ROOT/'docs/FOLLOWUP_REVIEW_0913.md';NB=MD.with_suffix('.ipynb');CACHE=ROOT/'work/followup_review_0913_cache.json'

def save(c):
    c['source_hashes'].update(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')

def start():
    c={'_meta':{'generator':'benchmark/review_followup_0913.py','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},'checks':{},'source_hashes':{}}
    x=c['checks'];x['queue']=old.prev.queue();x['boundaries']=old.boundary_checks();x['resume']=old.prev.resume_checks()
    # Source adapters are actually exercised; exceptions are retained as unverified results.
    prev=base.js('outputs/current_review_0913.json')['checks']['shards']
    try:x['generation']=old.prev.generation_checks(prev)
    except Exception as e:x['generation']={'error':type(e).__name__,'message':str(e)}
    manifest={r['file']:r for r in prev['manifest']};changed=[];recent=[];stable=[]
    for p in sorted(base.SHD.glob('*.npz')):
        st=p.stat()
        if st.st_mtime>time.time()-120:recent.append(p.name);continue
        stable.append(p.name)
        if p.name not in manifest or st.st_mtime_ns!=manifest[p.name]['mtime_ns']:
            changed.append({'file':p.name,'mtime_ns':st.st_mtime_ns})
    x['incremental_arrays']=old.full_arrays({'manifest':changed});x['incremental_arrays']['stable_files']=len(stable);x['incremental_arrays']['recent_skipped']=recent
    x['incremental_arrays']['scope']='Only new or mtime-changed stable shards received fresh full-array checks; unchanged shards retain the prior audit scope.'
    x['gates']=old.gates()
    for name,args in [('check_arm_names',['--shards']),('freeze_0912',['--check'])]:
        p=subprocess.run([sys.executable,'benchmark/'+name+'.py',*args],cwd=ROOT,text=True,capture_output=True,timeout=180)
        x['gates'][name]={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    save(c);print('start saved',flush=True)


def numpy_band(E,prf,ffl,ft,halfwidth=18.):
    # Independent periodic-Hann STFT and temporal harmonic readout, without scipy.
    ratio=prf/ffl;p=next((p for p in [.45,.6] if round(p*ratio)>=24),.6)
    nper=max(8,round(p*ratio));win=.5-.5*np.cos(2*np.pi*np.arange(nper)/nper)
    seg=np.lib.stride_tricks.sliding_window_view(np.asarray(E,complex),nper)[::2]
    fr=np.fft.fftfreq(8*nper,1/prf);m=(abs(fr)>=.35*ft)&(abs(fr)<=max(ft,1e-6))
    if m.sum()<2:return dict(n_bins=int(m.sum()),beat_hz=None,h1_over_h2_db=None,band_power_db=None)
    S=abs(np.fft.fft(seg*win,n=8*nper,axis=1))/win.sum();g=(S[:,m]**2).sum(axis=1)
    pw=10*np.log10(g.mean());g=g-g.mean();A=abs(np.fft.rfft(g*np.hanning(len(g)),n=64*len(g)));f=np.fft.rfftfreq(64*len(g),2/prf)
    if A.max()<=0:return dict(n_bins=int(m.sum()),beat_hz=None,h1_over_h2_db=None,band_power_db=round(float(pw),2))
    A/=A.max();sel=np.flatnonzero((f>=40)&(f<=400));i=sel[np.argmax(A[sel])];den=A[i-1]-2*A[i]+A[i+1]
    pk=f[i]+(.5*(A[i-1]-A[i+1])/den if den else 0)*(f[1]-f[0])
    def peak(q):return 20*np.log10(A[(f>=q-halfwidth)&(f<=q+halfwidth)].max())
    return dict(n_bins=int(m.sum()),beat_hz=round(float(pk),2),h1_over_h2_db=round(float(peak(ffl)-peak(2*ffl)),2),band_power_db=round(float(pw),2))

def producer():
    c=json.loads(CACHE.read_text());J=base.js('outputs/elevation_sweep_md.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz');meta=J['_meta'];rr={(r['engine'],r['el_deg']):r for r in J['rows']}
    prev=base.js('outputs/current_review_0913.json')['checks']['numeric']['drone_flash']
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='analyse')
    defs=[n for n in fn.body if isinstance(n,ast.FunctionDef) and n.name in ['_stft','band_metrics']]
    ns=dict(np=np,prf=meta['prf_hz'],ffl=meta['f_flash_hz'],_stft_cache={},auto_periods=mp.auto_periods,flash_spec=mp.flash_spec)
    exec(compile(ast.Module(body=defs,type_ignores=[]),'production band_metrics','exec'),ns)
    tip=base.funcs('benchmark/elevation_sweep_md.py',['f_tip_at','carrier_of'],dict(np=np,re=re,ROOT=str(ROOT),TJ=meta,FC=meta['fc_hz']))['f_tip_at']
    from drones import DRONES
    rows=[]
    for v in prev['rows']:
        r=rr[(v['engine'],v['el'])];E=np.asarray(Z[f"{r['engine']}/el{r['el_deg']:+g}"],complex);sp=DRONES[v['drone']];ff=int(sp.prop_blades)*sp.hover_rpm/60
        ft=tip(r['el_deg'],r['engine']);got=ns['band_metrics'](E,.35*ft,max(ft,1e-6),r['prf_hz'],ff)
        rows.append({'engine':r['engine'],'el':r['el_deg'],'old':v['published'],'new':r['track'],'production':got,'previous_prediction':v['with_drone_flash'],'f_flash_hz':r['f_flash_hz'],'expected_flash':ff})
    e=prev['example'];r=rr[(e['engine'],e['el'])];E=np.asarray(Z[f"{e['engine']}/el{e['el']:+g}"],complex);ft=tip(e['el'],e['engine'])
    windows=[{'halfwidth_hz':h,'old':numpy_band(E,r['prf_hz'],e['default_flash_hz'],ft,h),'new':numpy_band(E,r['prf_hz'],e['correct_flash_hz'],ft,h)} for h in [6,12,18,30,45,60]]
    c['checks']['producer']={'rows':rows,'n':len(rows),'changed':sum(v['old']!=v['new'] for v in rows),'production_mismatch':sum(v['production']!=v['new'] for v in rows),'previous_prediction_mismatch':sum(v['previous_prediction']!=v['new'] for v in rows),'example':e,'numpy_windows':windows}
    save(c);print('producer saved',flush=True)

def readers():
    c=json.loads(CACHE.read_text());x=c['checks'];wf=old.loadmod('benchmark/read_wfsurvive_0912.py');sc=old.loadmod('benchmark/read_scenephysics_0913.py');band=old.loadmod('benchmark/read_bandflat_0913.py');freeze=old.loadmod('benchmark/freeze_0912.py')
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation'];esm=types.SimpleNamespace(SHD=str(base.SHD),one_generation=choose)
    rinput=[]
    for case in ['different_prf','unresolved_generation','nan_complex64']:
        with tempfile.TemporaryDirectory() as td:
            N=8
            for k in range(4 if case=='unresolved_generation' else 2):
                idx=np.arange(k%2,N,2);E=np.full(idx.size,1+0j if k<2 else 2+0j,dtype=np.complex64)
                if case=='nan_complex64' and k==0:E[1]=complex(float('nan'),0)
                np.savez(Path(td)/f'arm_el+0_{k:02d}.npz',idx=idx,E=E,meta=[0,k%2,2,N,10000 if case=='different_prf' and k==1 else 19700,0],t_start=[1700000000.])
            row={'case':case};fixture=types.SimpleNamespace(SHD=td,one_generation=choose)
            for name,fn in [('waveform',wf.cell_series),('scene',sc.series)]:
                try:
                    with contextlib.redirect_stdout(io.StringIO()):v=fn(fixture,'arm',0.)
                    E=v[0] if name=='waveform' and v is not None else v
                    row[name]={'accepted':v is not None,'nonfinite_E':int((~np.isfinite(E)).sum()) if E is not None else None}
                except Exception as e:row[name]={'accepted':False,'error':type(e).__name__}
            rinput.append(row)
    pub=base.js('outputs/read_wfsurvive_0912.json')
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);out=td/'wf.json';doc=td/'wf.md'
        with patch.object(wf,'OUT',str(out)),patch.object(wf,'MD',str(doc)),patch.object(wf,'prod',lambda:esm),contextlib.redirect_stdout(io.StringIO()):rc=wf.main()
        got=json.loads(out.read_text());oldnum=freeze.scrape_numbers(pub);newnum=freeze.scrape_numbers(got)
        moved=[k for k in set(oldnum)|set(newnum) if oldnum.get(k)!=newnum.get(k)]
        oldrows={(r['engine'],r['el_deg']) for r in pub['rows']};newrows={(r['engine'],r['el_deg']) for r in got['rows']}
        counts=collections.Counter(r['row_label'] for r in got['rows'])
        x['waveform_publication']={'main_exit':rc,'rows':len(got['rows']),'skipped':len(got['skipped']),'published_rows':len(pub['rows']),'numeric_changes':moved,'row_identity_changes':sorted(oldrows^newrows),'duplicate_labels':[k for k,v in counts.items() if v>1]}
    x['reader_inputs']=rinput
    # Reproduce the two reports using both explicitly declared time grids.
    tonecases=[]
    for fs,N in [(20000.,8000),(19700.,8192)]:
        for amp in [0.,.1,1.]:
            t=np.arange(N)/fs;E=.01*np.exp(2j*np.pi*400*t)+amp*np.exp(2j*np.pi*1600*t)
            got=wf.survive(E,fs,[dict(std='nr',frame_rate_hz=2000.,frame_ms=.5)],400.)
            tonecases.append({'prf':fs,'n':N,'inband_hz':400.,'inband_amplitude':.01,'offband_hz':1600.,'offband_amplitude':amp,'nr':got['nr']})
    x['tone_conditions']=tonecases
    nadir=[]
    for r in pub['rows']:
        if not r['has_tipband']:
            vals={k:r.get(k) for k in ['ref_peak_in_tipband_hz','f_tip_hz','prf_hz']}
            vals.update({k:r[k]['peak_frameavg_in_tipband_hz'] for k in ['nr','wifi','lte']})
            nadir.append({'engine':r['engine'],'el':r['el_deg'],**vals})
    x['nadir_band']={'rows':nadir,'n':len(nadir),'rows_with_band_peak':sum(any(r.get(k) is not None for k in ['ref_peak_in_tipband_hz','nr','wifi','lte']) for r in nadir)}
    bd=base.js('outputs/bandflat_0913.json');real=np.load(ROOT/'outputs/elevation_sweep_md.npz');data={f"{r['engine']}/el{r['el_deg']:+g}":np.asarray(real[f"{r['engine']}/el{r['el_deg']:+g}"],complex) for r in bd['cells']}
    runs=[]
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for case in ['baseline','nan_input','short_input','phase_rotated']:
            arr={k:v.copy() for k,v in data.items()}
            if case=='nan_input':arr[next(iter(arr))][123]=complex(float('nan'),0)
            if case=='short_input':arr[next(iter(arr))]=arr[next(iter(arr))][:80]
            if case=='phase_rotated':
                for row in bd['cells']:arr[f"{row['engine']}/el{row['el_deg']:+g}"]*=np.exp(1j*(row['fc_mhz']-3500)/25*1.1)
            inp=td/(case+'.npz');out=td/(case+'.json');doc=td/(case+'.md');np.savez(inp,**arr)
            rc=None;error=None
            try:
                with patch.object(band,'LED_N',str(inp)),patch.object(band,'OUT_J',str(out)),patch.object(band,'OUT_MD',str(doc)),contextlib.redirect_stdout(io.StringIO()),np.errstate(all='ignore'):rc=band.main()
            except Exception as e:error=type(e).__name__+': '+str(e)
            g=json.loads(out.read_text()) if out.exists() else {};nums=freeze.scrape_numbers(g)
            bad=[k for k,v in nums.items() if isinstance(v,float) and not np.isfinite(v)]
            expected=freeze.scrape_numbers(bd);changed=[k for k in set(nums)|set(expected) if nums.get(k)!=expected.get(k)] if g else []
            runs.append({'case':case,'exit':rc,'error':error,'output_exists':out.exists(),'n_cells':g.get('_meta',{}).get('n_cells'),'skipped':g.get('skipped'),'nonfinite_fields':bad,'numeric_changes':changed})
    lengths=[]
    for N in [8,24,70,71,72,73,80,128]:
        try:
            v=band.modspec_norm(np.ones(N,complex),19700.,126.6666666667,1102.);lengths.append({'n':N,'arity':len(v),'has_result':v[0] is not None,'error':None})
        except Exception as e:lengths.append({'n':N,'error':type(e).__name__})
    x['band_runs']=runs;x['band_lengths']=lengths
    save(c);print('readers saved',flush=True)


def parity():
    c=json.loads(CACHE.read_text());J=base.js('outputs/bandflat_0913.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz');band=old.loadmod('benchmark/read_bandflat_0913.py');rows=[]
    for s in J['series']:
        group=sorted([r for r in J['cells'] if r['env']==s['env'] and r['el_deg']==s['el_deg']],key=lambda r:r['fc_mhz'])
        power=[];scales=[];gap=[]
        for r in group:
            E=np.asarray(Z[f"{r['engine']}/el{r['el_deg']:+g}"],complex);ac=E-E.mean()
            pw=[float(np.mean(abs(ac[k::2])**2)) for k in range(2)];power.append(pw);gap.append(10*np.log10(pw[0]/pw[1]))
            if r['fc_mhz']==3500:
                scales=[{'factor':factor,'signed_split_db':float(np.subtract(*band.halves_level_db(ac*factor,ac=True)))} for factor in [1e-6,1.,1e6]]
        pp=np.asarray(power);db=10*np.log10(pp);ref=next(i for i,r in enumerate(group) if r['fc_mhz']==3500);contrasts=db-db[ref,:]
        rows.append({'env':s['env'],'el':s['el_deg'],'fcs_mhz':[r['fc_mhz'] for r in group],'ac_split_signed_db':[float(v) for v in gap],'ac_split_variation_over_fc_db':float(np.ptp(gap)),
            'parity_band_spread_db':np.ptp(db,axis=0).tolist(),'parity_contrasts_vs_center_db':contrasts.tolist(),'max_difference_between_parity_contrasts_db':float(np.max(abs(contrasts[:,0]-contrasts[:,1]))),'published_moving_spread_db':s['moving_band_spread_db'],'published_reading':s['reading_ko'],'amplitude_scale_test':scales})
    c['checks']['parity']=rows;save(c);print('parity saved',flush=True)

def factorial_checks():
    sf=old.loadmod('benchmark/switch_factorial.py');J=base.js('outputs/switch_factorial.json');L=base.js('outputs/elevation_sweep_md.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz');cells=J['cells'];ff0=L['_meta']['f_flash_hz'];led={(r['engine'],r['el_deg']):r for r in L['rows']}
    from drones import DRONES
    other=[]
    for area in ['other_drone_switch_arms','reference_arms']:
        for key,v in J[area].items():
            drone=parse(v['arm']).get('drone')
            if not drone:continue
            sp=DRONES[drone];ff=int(sp.prop_blades)*sp.hover_rpm/60;r=led[(v['arm'],v['el_deg'])];E=Z[v['npz_key']]
            before=sf.columns(E,r['prf_hz'],ff0,r['f_tip_hz']);after=sf.columns(E,r['prf_hz'],ff,r['f_tip_hz'])
            before['rhythm_share_ref_pct']=sf.rhythm_share_ref(E,r['prf_hz'],ff0,r['f_tip_hz']);after['rhythm_share_ref_pct']=sf.rhythm_share_ref(E,r['prf_hz'],ff,r['f_tip_hz'])
            mismatch=[k for k,b in before.items() if v.get(k)!=b]
            other.append({'area':area,'key':key,'drone':drone,'f_flash_hz_used':ff0,'f_flash_hz_required':ff,'current':before,'corrected':after,'published':{k:v.get(k) for k in before},'publication_mismatch':mismatch,'changed_fields':[k for k in before if before[k]!=after[k]]})
    # Preserve the old last-row-wins selection to test the commit's correction claim.
    last={}
    for r in L['rows']:
        arm=r['engine'];combo=sf.combo_of(arm)
        if not combo or arm in sf.REF_ARMS or any(k in arm for k in ['mavic4pro','mini5pro','s1000plus']):continue
        tag,dep,_=combo;last[f"{tag}_d{dep}/el{r['el_deg']:+g}"]=r
    selections=[]
    for item in J['collisions']:
        key=item['cell'];r=last[key];v=cells[key];ac=sf.columns(Z[f"{r['engine']}/el{r['el_deg']:+g}"],r['prf_hz'],ff0,r['f_tip_hz'])['ac_db']
        selections.append({'cell':key,'old_last_engine':r['engine'],'current_engine':v['arm'],'old_last_ac_db':ac,'current_ac_db':v['ac_db'],'same_engine':r['engine']==v['arm'],'same_ac':ac==v['ac_db']})
    # Read the exact production membership expression, including its phase omission.
    tr=ast.parse(base.read('benchmark/switch_factorial.py'))
    expr=next(k.value for node in ast.walk(tr) if isinstance(node,ast.Call) for k in node.keywords if k.arg=='contains_unit_within_3sigma')
    compiled=compile(ast.Expression(expr),'production membership','eval')
    def contain(e0,e1):
        a=np.vdot(e0,e1)/np.vdot(e0,e0);sig=float(np.linalg.norm(e1-e0)/(np.linalg.norm(e0)*np.sqrt(e0.size)))
        return {'a_real':float(a.real),'a_imag':float(a.imag),'a_abs':float(abs(a)),'phase_deg':float(np.angle(a,deg=True)),'sigma':sig,'production_pass':bool(eval(compiled,{'a':a,'sig':sig})),'complex_distance_from_one':float(abs(a-1)),'complex_distance_over_sigma':float(abs(a-1)/sig) if sig>0 else None}
    axes=[]
    for ax,rs in J['axis_diffs'].items():
        for r in rs:
            a,b=cells[r['off']],cells[r['on']];fa,fb=parse(a['arm']),parse(b['arm']);fields=['mesh_fix','blade_law']
            mesh_diff={k:[fa.get(k),fb.get(k)] for k in fields if fa.get(k)!=fb.get(k)}
            d={'axis':ax,'off':r['off'],'on':r['on'],'el':r['el_deg'],'off_engine':a['arm'],'on_engine':b['arm'],'mesh_difference':mesh_diff,'published':r}
            if not r['off_zero_echo'] and not r['on_zero_echo']:
                e0=np.asarray(Z[a['npz_key']],complex);e1=np.asarray(Z[b['npz_key']],complex);e0-=e0.mean();e1-=e1.mean();d['recomputed']=contain(e0,e1)
            axes.append(d)
    t=np.arange(64)/64;e0=np.exp(2j*np.pi*t)
    phase_cases=[{'phase_deg':deg,'result':contain(e0,np.exp(1j*np.deg2rad(deg))*e0)} for deg in [0,90,180]]
    density=[]
    for N in [64,256,1024,8192]:
        t=np.arange(N)/N;e0=np.exp(2j*np.pi*t);e1=1.1*e0+np.exp(4j*np.pi*t)
        density.append({'n':N,'same_continuous_functions':True,'result':contain(e0,e1)})
    return {'other_drone':{'rows':other,'n':len(other),'areas':dict(collections.Counter(r['area'] for r in other)),'changed':sum(bool(r['changed_fields']) for r in other),'publication_mismatch':sum(bool(r['publication_mismatch']) for r in other)},
        'old_selection':{'rows':selections,'n':len(selections),'engine_changes':sum(not r['same_engine'] for r in selections),'ac_changes':sum(not r['same_ac'] for r in selections),'current_metadata':J['_meta']['collisions_ko']},
        'axis_pairs':{'rows':axes,'n':len(axes),'mesh_mixed':sum(bool(r['mesh_difference']) for r in axes),'diffraction_plate_mixed':sum(bool(r['mesh_difference']) and r['axis']=='D' and r['el']==-30 for r in axes),'membership_mismatch':sum(r['recomputed']['production_pass']!=r['published']['contains_unit_within_3sigma'] for r in axes if 'recomputed' in r),'phase_false_accepts':[r for r in axes if 'recomputed' in r and r['recomputed']['production_pass'] and (r['recomputed']['complex_distance_over_sigma'] or 0)>3]},
        'containment':{'production_expression':ast.unparse(expr),'phase_cases':phase_cases,'sampling_density':density},
        'verdict':J['verdict'],'headline':J['headline'],'plate_rows':J['diffraction_on_plate_el30']}

def toc_checks():
    toc=old.loadmod('benchmark/build_atlas_toc.py');A=toc.audit();checks=toc.self_checks(A);bad=[]
    from drones import DRONES
    for arm,a in toc.IDX_ARM.items():
        s=DRONES[a['airframe']];f_rev=s.hover_rpm/60;legacy=2*(2*np.pi*f_rev*s.prop_dia_mm/2000)/(toc.C_LIGHT/toc.META['fc_hz'])
        if abs(legacy-a['f_tip0_hz'])>.2:
            ps=float(parse(arm).get('prop_scale') or 1);fc=a['fc_hz'];correct=legacy*ps*fc/toc.META['fc_hz']
            bad.append({'engine':arm,'published_tip':a['f_tip0_hz'],'toc_expectation':float(legacy),'with_carrier_and_prop_scale':float(correct),'corrected_matches':abs(correct-a['f_tip0_hz'])<=.2})
    nb=base.js('reports/A_atlas.ipynb');text='\n'.join(''.join(c['source']) for c in nb['cells'])
    lines=[s for s in text.splitlines() if '1014' in s or '260 칸' in s or ('정수배' in s and '독립' in s)]
    return {'self_checks':checks,'old_report_lines':lines,'wrong_toc_tip_checks':bad,'n_wrong_toc_tip':len(bad),'fixed_tip_matches':sum(r['corrected_matches'] for r in bad),'current_index_cells':toc.META['n_cells'],'newer_shards':A['shards_newer_than_ledger']}

def downstream():
    c=json.loads(CACHE.read_text());c['checks']['factorial']=factorial_checks();save(c);print('factorial saved',flush=True)
    c['checks']['toc']=toc_checks();save(c);print('toc saved',flush=True)

def latest_repeat():
    c=json.loads(CACHE.read_text());J=base.js('outputs/elevation_sweep_md.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    changed=['benchmark/read_bandflat_0913.py','outputs/bandflat_0913.json','outputs/freeze_0912.json','docs/BANDFLAT_0913.md','docs/FREEZE_0912.md']
    c['checks']['snapshot_transition']={'initial_head':c['_meta']['head'],'latest_head':head,'changed_files':changed,'initial_hashes':{p:c['source_hashes'].get(p) for p in changed}}
    for p in changed:base.HASHES.pop(p,None);c['source_hashes'].pop(p,None)
    b=old.loadmod('benchmark/read_bandflat_0913.py');pub=base.js('outputs/bandflat_0913.json');by={(r['engine'],r['el_deg']):r for r in J['rows']};items=[];selected=set()
    for s in pub['series']:
        sub=[]
        for fc in pub['_meta']['fcs_mhz']:
            arm=b.arm_name(s['env'],fc);f=parse(arm);candidates=[]
            for r in J['rows']:
                if r['el_deg']!=s['el_deg']:continue
                rf=parse(r['engine'])
                if {k:v for k,v in rf.items() if k!='rep'}!=f:continue
                key=f"{r['engine']}/el{r['el_deg']:+g}";E=np.asarray(Z[key],complex);p=float(np.mean(abs(E-E.mean())**2));selected.add(key)
                candidates.append({'engine':r['engine'],'rep':rf.get('rep'),'ac_db':float(10*np.log10(p)),'n_missing':r.get('n_missing'),'n_zero_field':r.get('n_zero_field'),'truncated':r.get('truncated'),'mixed_generations':r.get('mixed_generations'),'nonfinite':int((~np.isfinite(E)).sum())})
            v=b.repeat_spread_db(arm,s['el_deg'],J['rows'],Z);vals=[r['ac_db'] for r in candidates]
            sub.append({'fc_mhz':fc,'candidates':candidates,'n':len(vals),'exact_spread_db':float(np.ptp(vals)) if len(vals)>1 else None,'production_spread_db':v[0],'production_count':v[1]})
        items.append({'env':s['env'],'el':s['el_deg'],'published_n_runs':s['repeat_n_runs'],'published_repeat_spread_db':s['repeat_spread_db'],'groups':sub,'repeat_tested_fcs':[r['fc_mhz'] for r in sub if r['n']>1],'runs_in_repeated_groups':sum(r['n'] for r in sub if r['n']>1),'singleton_frequencies':sum(r['n']==1 for r in sub),'published_reading':s['reading_ko']})
    freeze=old.loadmod('benchmark/freeze_0912.py');data={k:np.asarray(Z[k],complex) for k in selected};runs=[]
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for case in ['baseline','nan_input','short_input','phase_rotated']:
            arr={k:v.copy() for k,v in data.items()};key=f"{pub['cells'][0]['engine']}/el{pub['cells'][0]['el_deg']:+g}"
            if case=='nan_input':arr[key][123]=complex(float('nan'),0)
            if case=='short_input':arr[key]=arr[key][:80]
            if case=='phase_rotated':
                for k in arr:
                    f=parse(k.rsplit('/el',1)[0]);fc=float(f.get('fc') or 3500);arr[k]*=np.exp(1j*(fc-3500)/25*1.1)
            inp=td/f'{case}.npz';out=td/f'{case}.json';doc=td/f'{case}.md';np.savez(inp,**arr);error=None;rc=None
            try:
                with patch.object(b,'LED_N',str(inp)),patch.object(b,'OUT_J',str(out)),patch.object(b,'OUT_MD',str(doc)),contextlib.redirect_stdout(io.StringIO()),np.errstate(all='ignore'):rc=b.main()
            except Exception as e:error=type(e).__name__+': '+str(e)
            val=json.loads(out.read_text()) if out.exists() else {};a=freeze.scrape_numbers(pub);z=freeze.scrape_numbers(val)
            runs.append({'case':case,'exit':rc,'error':error,'output_exists':out.exists(),'n_cells':val.get('_meta',{}).get('n_cells'),'skipped':val.get('skipped'),'nonfinite_fields':[k for k,v in z.items() if isinstance(v,float) and not np.isfinite(v)],'numeric_changes':[k for k in set(a)|set(z) if a.get(k)!=z.get(k)] if val else []})
    x=c['checks'];x['latest_repeat']={'head':head,'groups':items,'band_main_runs':runs,'scope':'New commit audited after the initial snapshot. Per-frequency runs are enumerated by complete parsed field identity, varying rep only.'}
    p=subprocess.run([sys.executable,'benchmark/freeze_0912.py','--check'],cwd=ROOT,text=True,capture_output=True,timeout=180)
    x['gates_latest_freeze']={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    save(c);print('latest repeat saved',flush=True)

def findings(c):
    x=c['checks'];sf=x['factorial'];od=sf['other_drone'];ap=sf['axis_pairs'];tc=x['toc'];lr=x['latest_repeat'];fs=[]
    def add(title,status,evidence,fix,key,sources):
        fs.append(dict(title=title,status=status,evidence=evidence,fix=fix,result_key=key,sources=[base.source(p,n) for p,n in sources]))
    s='benchmark/switch_factorial.py';w='benchmark/read_wfsurvive_0912.py';b='benchmark/read_bandflat_0913.py'
    nan=next(r for r in lr['band_main_runs'] if r['case']=='nan_input');short=next(r for r in lr['band_main_runs'] if r['case']=='short_input')
    add('입력 검증이 새 판독기의 실제 실행 경로에 여전히 빠져 있다','우선 수정 · 임시 반례에서 발간 실패와 오염 재현',
        f"파형·장면 판독기 모두 표집률 불일치, 세대 선택 뒤 남은 전계 충돌, complex64 NaN 입력을 받아들였다. 최신 대역 main에 NaN을 넣으면 비유한 수 {len(nan['nonfinite_fields'])}개를 포함한 JSON을 먼저 저장한 다음 {nan['error']}로 중단한다. 기대 길이와 다른 짧은 입력도 exit {short['exit']}, 건너뜀 {len(short['skipped'])}개로 통과하고 숫자 {len(short['numeric_changes'])}개가 바뀐다. 현재 정상 자료가 오염됐다는 판정이 아니라, 임시 입력으로 재현한 오류 처리 결함이다.",
        '모든 판독기가 같은 입력 관문을 사용하게 한다. 저장된 표본수·표집률·idx 완전성·유한성·세대 충돌 진단을 확인하고 거절 사유를 남긴다. 계산과 문서 생성이 모두 성공한 뒤 검증된 임시 산출물로 교체한다.',
        'checks.reader_inputs / checks.latest_repeat.band_main_runs',[(w,'fs, _ = esm.one_generation'),('benchmark/read_scenephysics_0913.py','fs, _ = esm.one_generation'),(b,'json.dump(out, open(OUT_J')])
    examples=[]
    for drone in ['mini5pro','mavic4pro']:
        q=next(r for r in od['rows'] if r['area']=='reference_arms' and r['drone']==drone and r['key'].endswith('/el-30'))
        examples.append(f"{q['key']}: 리듬 몫 {q['current']['rhythm_share_pct']:.2f} → {q['corrected']['rhythm_share_pct']:.2f}%")
    add('완전요인 분석의 보조 표에 기본 기체 날개 통과율이 남아 있다','발간 수치에 영향 · 새로 확인',
        f"other_drone_switch_arms와 reference_arms의 {od['n']}행을 현재 함수로 재계산한 발간값 불일치는 {od['publication_mismatch']}행이다. 그 함수에 기체별 날개 통과율을 넣으면 {od['changed']}행의 한 개 이상 열이 달라진다. 영역별 행 수는 {od['areas']}이다. "+' / '.join(examples)+'. 이 범위는 다른 기체 보조 표이며 기본 기체의 완전요인 전체가 바뀐다는 뜻은 아니다.',
        '행별 기체에서 날개 통과율을 구해 columns와 rhythm_share_ref에 전달하고, 사용한 값을 행에 기록한다. 영향받는 보조 표와 파생 설명을 다시 생성한다.',
        'checks.factorial.other_drone',[(s,'PRF, FFL ='),(s,'col = columns(Z[key_np]'),(s,'col["rhythm_share_ref_pct"] =')])
    add('메쉬가 다른 비교가 주판정용 회절 비교에도 들어간다','발간 비교의 해석에 영향 · 범위 추가 확인',
        f"axis_diffs {ap['n']}쌍 중 {ap['mesh_mixed']}쌍은 mesh_fix 또는 blade_law가 다르다. 주판정용 el −30° 회절 비교 {len(sf['plate_rows'])}쌍 중에도 {ap['diffraction_plate_mixed']}쌍이 들어간다. 조합별 대표 행 선택이 명시적이어도 on/off 쌍이 같은 메쉬가 되는 것은 보장되지 않는다.",
        '변경하려는 스위치 외의 조건이 같은 쌍만 주판정에 사용한다. 짝이 없는 조건은 비교 보류와 이유를 기록하고, 기존 혼합 쌍은 조건 차이를 표시한다.',
        'checks.factorial.axis_pairs',[(s,'o, n = c, cells[k1]'),(s,'a_cover = bool')])
    q=next(r for r in ap['phase_false_accepts'] if r['axis']=='D' and r['el']==-30);r=q['recomputed'];pc=sf['containment']['phase_cases'];den=sf['containment']['sampling_density']
    add('계수 1 포함 판정이 복소 위상을 버리고 불확도 가정을 확정적으로 쓴다','계산·해석 결함 · 실제 비교와 반례로 재현',
        f"생산식은 {sf['containment']['production_expression']}이다. 실제 {q['off']} → {q['on']}에서 |a|={r['a_abs']:.6f}, 위상 {r['phase_deg']:.5f}°인데 통과한다. 합성 동일 신호의 판정은 {pc[0]['result']['production_pass']}, 위상 {pc[1]['phase_deg']}°와 {pc[2]['phase_deg']}° 회전 신호는 각각 {pc[1]['result']['production_pass']}, {pc[2]['result']['production_pass']}다. 같은 시간 구간의 같은 연속 함수를 표본화한 반례에서도 N={[v['n'] for v in den]}에 따라 판정은 {[v['result']['production_pass'] for v in den]}로 바뀐다. 코드가 밝힌 무상관 가정은 이 결정적 자세열에 대해 검증된 불확도 모형이 아니다.",
        '복소 계수의 크기와 위상을 따로 보여주고 계수 1과의 복소 거리를 검사한다. 동일 신호·잔차 영의 경계도 처리한다. 현재 sigma를 그대로 신뢰구간으로 재사용하지 말고, 시간 의존성과 실제 반복 설계에 맞는 불확도 근거를 먼저 마련한다.',
        'checks.factorial.containment / checks.factorial.axis_pairs.phase_false_accepts',[(s,'sig = float(np.linalg.norm(res)'),(s,'contains_unit_within_3sigma=bool')])
    add('보류 판정과 계수·위상 확정 설명이 같은 발간물에 공존한다','현재 발간 문면에 영향',
        f"현재 A_cover_pass={sf['verdict']['A_cover_pass']}인데 A_cover_why_ko는 계수 1·위상 약 0°로 그대로 품는다고 단정한다. headline에도 판정 보류와 얹는 축이라는 단정이 공존한다. 앞의 혼합 메쉬·복소 계수 문제를 고치기 전에도 이 조건 없는 설명은 현재 판정값과 모순된다. 실제 headline 원문은 연결 원장에 보존했다.",
        '설명과 제목을 판정 상태에 따라 생성한다. 보류·실패·입력 부적격 각각의 이유를 쓰고, 잔차 분해나 높은 상관만으로 물리적 원인을 단정하지 않는다.',
        'checks.factorial.verdict / checks.factorial.headline',[(s,'A_cover_why_ko=')])
    nd=x['nadir_band']['rows'];q=nd[0]
    add('직하방에서 존재하지 않는 날개끝 띠의 봉우리 값이 발간된다','발간 열 정의와 값 불일치 · 새로 확인',
        f"has_tipband=false인 {len(nd)}행 모두에 띠 내부 봉우리 값이 남아 있다. 예: {q['engine']} / el {q['el']:g}°, f_tip={q['f_tip_hz']:g} Hz인데 기준 띠 봉우리는 {q['ref_peak_in_tipband_hz']:.6f} Hz다. 경계가 None이면 peak가 전체 스펙트럼을 탐색하는 것이 원인이다. ‘띠 값이 전부 null’이라는 메타 설명과도 어긋난다.",
        '띠가 없는 경우 띠 전용 peak 열을 명시적으로 null로 둔다. 전체 스펙트럼 봉우리를 유지하려면 기존 전체 봉우리 열로 분리해 표시한다.',
        'checks.nadir_band',[(w,'def peak(v, fs_, lo=None'),(w,'ref_peak_hz=peak(x, prf)'),(w,'띠 값이 전부 null')])
    add('아틀라스 안내 노트북뿐 아니라 자체 검사식도 낡았다','문면과 검사 오경보 · 새 원인 확인',
        f"기존 안내의 검사 문장: {tc['old_report_lines'][0]}. 현재 같은 검사 결과: {tc['self_checks'][1][2]}. 날개끝 도플러 검사에서 지적한 {tc['n_wrong_toc_tip']}팔은 전역 반송파를 쓰고 프로펠러 배율을 빠뜨린 검사식 때문이다. 행별 반송파와 프로펠러 배율을 적용하면 {tc['fixed_tip_matches']}팔 모두 현재 색인과 맞는다. 기본 기체를 이름에 명시한 팔의 박자가 기본값과 다르다고 요구하는 별도 검사도 수정 대상이다.",
        '행별 반송파·프로펠러 배율·기체를 반영하도록 검사기를 먼저 고친 뒤 안내 노트북을 재생성한다. 이번에 재계산과 일치한 색인 값은 유지한다.',
        'checks.toc',[('benchmark/build_atlas_toc.py','fc = float(META["fc_hz"])'),('benchmark/build_atlas_toc.py','tip0 = 2.0 *')])
    err=x['boundaries']['old_audit_failure']
    add('저장 중단 시험의 생산 의존성 누락이 남았다','감사 재현 경로 결함',
        f"현재 review_repository_0911.save_interruption() 재실행은 {err['type']}: {err['message']}로 끝난다. 추출한 생산 저장 코드가 bake_stamp를 호출하지만 시험의 실행 namespace에 해당 의존성이 없다. raw_merge 어댑터를 고친 것과 별개의 경로다. 실제 워커의 저장 실패로 분류하지 않는다.",
        '시험에 현재 생산 의존성을 명시적으로 제공하고, 의도한 저장 예외와 시험 자체의 준비 오류를 구분한다. 실행 준비 오류는 검증 보류로 집계한다.',
        'checks.boundaries.old_audit_failure',[('benchmark/review_repository_0911.py',"assert failure=='OSError'")])
    osel=sf['old_selection']
    add('현재 생성기와 JSON에 옛 중복 선택의 잘못된 이력이 남아 있다','현재 발간 이력 설명 오류',
        f"옛 마지막 행 우선 선택을 재현한 {osel['n']}칸에서 현재와 팔이 다른 칸 {osel['engine_changes']}, AC가 다른 칸 {osel['ac_changes']}이다. 따라서 사용자가 전달한 정정은 맞는다. 그러나 현재 _meta.collisions_ko는 여전히 ‘먼저 온 것’이 정본 메쉬를 버렸다고 적는다. 원문: {osel['current_metadata']}",
        '생성기와 JSON의 이력 설명을 ‘값의 정정이 아니라 선택 규칙의 명시화’로 고친다. 되돌린 중간 구현과 그 이전 발간 구현의 이력을 구분한다.',
        'checks.factorial.old_selection',[(s,'⛔옛 판은 조용히 덮었고')])
    counts=[g['published_n_runs'] for g in lr['groups']];actual=[g['runs_in_repeated_groups'] for g in lr['groups']];sp=[next(v['exact_spread_db'] for v in g['groups'] if v['n']>1) for g in lr['groups']]
    add('최신 되풀이 대조의 주파수 범위와 판 수·정밀도를 명시해야 한다','최신 변경의 해석 범위 보완',
        f"{lr['head'][:8]}에서 짝·홀을 판정 대조로 쓰던 코드는 제거됐다. 같은 조건 되풀이가 있는 주파수는 각 그룹의 {lr['groups'][0]['repeat_tested_fcs']} MHz뿐이다. 표의 판 수 {counts}에는 각기 다른 주파수의 단독 실행이 섞여 있고, 실제 반복 그룹의 판 수는 {actual}이다. 반올림 전 AC 퍼짐은 {sp} dB로, 표시된 영은 정확한 영이 아니다. 현재 관측 대역 퍼짐이 이 중심 주파수 되풀이 퍼짐보다 크다는 수치 비교는 재현되지만 전 대역의 격자 민감도나 물리적 정확도의 검증으로 확장할 수 없다.",
        '반복이 있는 주파수, 그 조건의 반복 수, 다른 주파수의 단독 실행 수를 나누어 적는다. 재현성은 원정밀도로 저장하고 작은 값은 과학적 표기로 표시한다. 중심 주파수 반복과 대역 전체 수렴성의 범위를 구분한다.',
        'checks.latest_repeat.groups',[(b,'rep_n = sum(x[1] for x in _rs)'),(b,'되풀이 재현성 {rep_spread:.3f}')])
    add('위상·백색잡음 설명이 문서와 코드 머리글에서 서로 다르다','문면 정정 부분 완료',
        '생성 문서는 구조 문턱이 잡음 모형 검정이 아니라는 제한을 추가했다. 반면 코드 머리글에는 실외 값은 백색잡음 널과 구별되지 않는다는 문장과 날개가 아니라는 단정이 남아 있다. 위상을 다루지 않는다는 제한은 코드 머리글에는 있지만 발간 문서 제목·도입의 평탄성 질문에는 충분히 드러나지 않는다. 반송파마다 상수 위상을 회전시킨 최신 main 시험에서도 수치가 그대로다.',
        '정정된 해석 하나로 코드 머리글·문서 제목·소개·자동 설명을 맞춘다. 크기와 변조구조에 대한 관측이며 위상 평탄성은 별도 분석임을 독자용 문서에도 명시한다.',
        'checks.latest_repeat.band_main_runs',[(b,'실외 값은 **백색잡음 널과 구별되지 않는다.**'),(b,'**이 판독기는 위상을 못 본다.**'),('docs/BANDFLAT_0913.md','두 문턱은 우리가 정한 값')])
    return fs

def render(c):
    x=c['checks'];p=x['producer'];wf=x['waveform_publication'];j='outputs/followup_review_0913.json';lr=x['latest_repeat'];a=x['incremental_arrays']
    lines=['# 후속 수정 재검증과 파생 비교 점검','',f"점검 시작 커밋 `{c['_meta']['head']}` → 최신 확인 `{c['_meta']['final_head']}`.",f"완료 시각 {c['_meta']['finished_at_utc']}. 조사 도중 변경된 대역 판독기는 최신 커밋에서도 main을 다시 실행했다.",'',
      '## 기존 아홉 항목에 대한 판정','',
      '| 기존 항목 | 이번 확인 | 남은 범위 |','|---|---|---|',
      f"| 기체별 날개 통과율 | 주 집계 {p['n']}행 중 {p['changed']}행 변경, 현재 함수 불일치 {p['production_mismatch']} | 완전요인 보조 표로 전파 필요 |",
      '| 대역 퍼짐 대조 | 최신판에서 되풀이 실행으로 변경 | 중심 주파수 반복 범위와 판 수 표시 보완 |',
      '| 띠 생존 지표 | 안/밖 분리 열과 누출 한계 설명 확인 | 입력 마스크에 따른 분리 지표이며 성분 생존의 단독 증거가 아님 |',
      '| 위상 해석 | 코드 머리글의 범위 정정 확인 | 독자용 제목·도입 보완 |',
      '| 구조 문턱 해석 | 문서의 잡음 검정 단정 철회 확인 | 코드 머리글에 옛 단정 잔존 |',
      '| 입력 검증 | 짧은 STFT helper 수정 확인 | raw loader와 main의 검증 누락 |',
      f"| 파형 행 선택·표시 | 실제 main 재실행 {wf['rows']}행·건너뜀 {wf['skipped']}행, 수치 변화 {len(wf['numeric_changes'])} | 이번 정상 입력 재현은 일치 |",
      '| 감사 어댑터 | 세대 선택·raw merge 경로 재현 | 저장 중단 시험은 실행 준비 오류 |',
      '| 선행연구 안내 | 현재 통계와 과거 통계 구분 확인 | 이번 범위에서 기존 지적을 반복하지 않음 |','',
      '## 재현된 수정과 숫자 차이의 해석','',
      f"날개 통과율의 이전 감사 예측과 현재 주 집계가 다른 행은 {p['previous_prediction_mismatch']}이다. 대표 {p['example']['engine']} / el {p['example']['el']:g}°는 scipy를 사용하지 않은 NumPy STFT로도 아래 값을 재현했다.",'',
      '| 배음 창 반폭 Hz | 옛 통과율의 H1/H2 dB | 기체별 통과율의 H1/H2 dB |','|---|---|---|']
    for r in p['numpy_windows']:lines.append(f"| {r['halfwidth_hz']:g} | {r['old']['h1_over_h2_db']:.2f} | {r['new']['h1_over_h2_db']:.2f} |")
    lines += ['', '이 창 변화 시험은 해당 대표 신호의 민감도 확인이다. 모든 신호에서 창 선택과 무관하다는 주장으로 확대하지 않는다.','',
      '파형 반례의 두 보고 숫자는 실험 조건이 달랐다. 같은 입력 조건으로 다시 계산하면 각각 다음과 같다.','',
      '| PRF Hz | 표본수 | 띠 밖 진폭 | 옛 합계 비율 dB | 새 from_inband dB |','|---|---|---|---|---|']
    for t in x['tone_conditions']:lines.append(f"| {t['prf']:g} | {t['n']} | {t['offband_amplitude']:g} | {t['nr']['rms_keep_tipband_db']:.2f} | {t['nr']['tipband_from_inband_db']:.2f} |")
    t=x['tone_conditions'][0]
    lines += ['',f"공통 조건: 입력 관심 톤 {t['inband_hz']:g} Hz·진폭 {t['inband_amplitude']:g}, 띠 밖 톤 {t['offband_hz']:g} Hz, 출력 NR 프레임률 {t['nr']['frame_rate_hz']:g} Hz. 서로 다른 표집 조건의 숫자 차이를 수정 실패로 보거나 ‘동일 조건의 자릿수까지 독립 재현’이라고 쓰는 것은 피한다.",'',
      '## 추가 보완점','']
    for i,f in enumerate(c['findings'],1):
        lines.extend([f"### {i}. {f['title']}",'',f"**등급:** {f['status']}",'',f['evidence'],'',f"**권고:** {f['fix']}",'',f"근거 원장: `{j}` → `{f['result_key']}`",''])
        lines.extend(f"- [{s['path']}:{s['line']}](../{s['path']}#L{s['line']}) — `{s['quote']}`" for s in f['sources']);lines.append('')
    par=next(r for r in x['parity'] if r['env']=='outdoor01' and r['el']==-30)
    lines += ['## 대조군 논의에서 더 정확히 표현할 점','',
      '진폭을 공통 배율로 바꿔도 짝·홀 dB 차이가 유지된다는 사실만으로 대조군이 부적절하거나 계통 오차라고 증명되지는 않는다. 전력비 10 log10(c²P짝 / c²P홀)에서는 공통 배율이 정의상 소거된다. 질문에 대응하는 차이와 그 불확도를 비교해야 한다.',
      f"실외 el {par['el']:g}°의 짝·홀 절대 레벨 차이가 크더라도, 각 집합을 중심 주파수에 맞춰 비교하면 주파수 변화 대비의 최대 차이는 {par['max_difference_between_parity_contrasts_db']:.8f} dB다. 짝수만·홀수만으로 잰 대역 퍼짐은 각각 {par['parity_band_spread_db'][0]:.6f}, {par['parity_band_spread_db'][1]:.6f} dB다. 이 관측은 옛 ‘대역 변화가 절대 짝·홀 차이에 묻힌다’의 비교가 부적절했음을 구체화한다. 새 신뢰구간이나 물리적 원인의 확정은 아니다. 최신 커밋은 이미 그 판정 대조를 제거했다.",'',
      '## 검사 범위와 재현','',
      f"이전 전수 감사의 샤드 목록을 이어받았다. 현재 안정된 샤드 {a['stable_files']}개 중 새로 생기거나 mtime이 바뀐 {a['files']}개를 전체 배열 검사했고 오류 {len(a['errors'])}개, 읽는 중 변경 {len(a['changed_during_read'])}개였다. 그대로인 샤드를 전부 재검사한 것으로 집계하지 않는다. GPU·솔버 실행과 아틀라스 전체 그림 재렌더링은 이번 범위에 포함하지 않았다.",
      f"최신 freeze 검사 exit {x['gates_latest_freeze']['exit']}. 최초 freeze 차이는 작업 중 늘어난 창고 샤드 수였으며, 이후 생산측 기준선 갱신 후 통과했다. 기준선 통과는 여기서 재현한 계산·입력 결함을 반증하지 않는다. 이름·의미·각주 등의 검사 원문은 checks.gates에 저장했다. 기존 규약 검사 누적 부채와 링크 경고까지 없다는 뜻으로 ‘관문 통과’를 쓰지 않는다.",
      f"인용 {c['checks']['source_quotes_verified']}개를 줄·문자 대조했다. 저장한 입력 해시와 종료 시점이 다른 파일: {c['checks']['snapshot_changes']}. 변경된 커밋의 초기 해시는 checks.snapshot_transition에 따로 보존했다.",
      '생산 코드·발간 원장·워커·큐는 수정하지 않았다. 이번 감사 생성기와 감사 JSON·Markdown·Jupyter 노트북, work 캐시만 작성했다. 저장소에 추가된 최신 생산 커밋은 다른 작업자의 변경이다.','',
      '```bash',f'{sys.executable} benchmark/review_followup_0913.py','```','',
      '기존 캐시로 보고서만 다시 만들려면 같은 명령에 `--publish`를 붙인다. 보고서 생성은 생산 산출물을 갱신하지 않는다.','']
    MD.write_text('\n'.join(lines))
    from report_style import header,md,next_steps,build_notebook
    cells=[header(num='후속 점검',title='수정 완료 주장과 현재 파생 비교의 재검증',did='저장 자료의 재계산과 임시 입력으로 생산 판독 경로를 확인했다.',results=[f"주 집계 {p['n']}행 재계산 ⟨{j} : checks.producer⟩.",f"파형 발간 {wf['rows']}행 재현 ⟨{j} : checks.waveform_publication⟩.",f"보완점 {len(c['findings'])}건 기록 ⟨{j} : findings⟩."],method=[('정상 자료','생산 함수 대조·NumPy STFT 검산'),('경계 입력','임시 파일로 실제 main과 loader 실행')],repro=dict(cmd=[f'{sys.executable} benchmark/review_followup_0913.py'],out=[j],runtime='CPU 한 코어·저장 자료 읽기'))]
    cells.append(md('## 확인 범위','',f"[기존 항목 판정과 재현 조건](FOLLOWUP_REVIEW_0913.md) ⟨{j} : checks⟩"))
    for i,f in enumerate(c['findings']):cells.append(md(f"## {i+1}. {f['title']}",'',f"등급: {f['status']}",'',f['fix'],'',f"[수치와 코드 인용](FOLLOWUP_REVIEW_0913.md) ⟨{j} : findings[{i}]⟩"))
    cells.append(next_steps([('입력 관문과 발간 순서를 정비한다','오류 입력의 거절과 산출물 보존','FOLLOWUP_REVIEW_0913.md'),('기체별 계산과 조건이 같은 비교 쌍을 적용한다','수치·복소 계수·설명의 일치','FOLLOWUP_REVIEW_0913.md'),('검사식과 독자용 문서를 함께 갱신한다','되풀이 범위·과거 이력·표 정의','FOLLOWUP_REVIEW_0913.md')]))
    build_notebook(str(NB),cells,strict=True)

def publish():
    c=json.loads(CACHE.read_text());c['findings']=findings(c)
    c['_meta']['finished_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());c['_meta']['final_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    c['checks']['queue_final']=old.prev.queue();sources=dict(c.get('source_hashes',{}));sources.update(base.HASHES)
    for p in ['benchmark/review_followup_0913.py','src/arm_grammar.py','src/drones.py','outputs/elevation_sweep_md.npz','outputs/freeze_0912.json','docs/FREEZE_0912.md']:
        with (ROOT/p).open('rb') as f:sources[p]=hashlib.file_digest(f,'sha256').hexdigest()
    c['_meta']['source_sha256']=sources;c.pop('source_hashes',None);c['checks']['snapshot_changes']=[]
    for p,d in sources.items():
        path=Path(p) if Path(p).is_absolute() else ROOT/p
        with path.open('rb') as f:now=hashlib.file_digest(f,'sha256').hexdigest()
        if d!=now:c['checks']['snapshot_changes'].append(p)
    for f in c['findings']:
        for s in f['sources']:
            assert s['found'],s
            assert (ROOT/s['path']).read_text().splitlines()[s['line']-1].strip()==s['quote'],s
    c['checks']['source_quotes_verified']=sum(len(f['sources']) for f in c['findings'])
    OUT.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n');render(c)
    print('published',len(c['findings']),'findings',c['checks']['snapshot_changes'],flush=True)

if __name__=='__main__':
    if '--publish' in sys.argv:publish()
    else:
        start();producer();readers();parity();downstream();latest_repeat();publish()
