"""Current repository audit; CPU only, live sources and publications read only.
Run: /workspace/.venvs/py312/bin/python benchmark/review_full_0912.py
Synthetic failures use temporary files; report outputs use a new dated basename.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast,collections,contextlib,copy,hashlib,importlib.util,io,json,re,subprocess,sys,tempfile,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import review_status_0911 as prev
repo=prev.repo;base=repo.base;ROOT=base.ROOT
sys.path.insert(0,str(ROOT/'src'))
from arm_grammar import parse as _agparse,unparse as _agunparse  # noqa: E402
OUT=ROOT/'outputs/full_review_0912.json';MD=ROOT/'docs/FULL_REVIEW_0912.md';NB=MD.with_suffix('.ipynb')
CACHE=ROOT/'work/full_review_0912_cache.json'

def loadmod(rel):
    p=base.digest(rel);spec=importlib.util.spec_from_file_location(p.stem,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def gates():
    out={}
    for name in ['check_new_file_rules','check_report_links','check_row_pointers','check_retracted','check_stale_titles']:
        base.digest('benchmark/'+name+'.py')
        p=subprocess.run([sys.executable,'benchmark/'+name+'.py'],cwd=ROOT,text=True,capture_output=True,timeout=120)
        out[name]=dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
    return out

def full_arrays(shards):
    bad=[];expected_cfg=[];gate_reject=[];keys=collections.Counter();changed=[];stamp=0
    done=base.funcs('benchmark/elevation_sweep_md.py',['shard_done'],dict(os=os,np=np))['shard_done']
    for j,r in enumerate(shards['manifest']):
        p=base.SHD/r['file'];s0=p.stat();errors=[]
        try:
            with np.load(p,allow_pickle=False) as z:a={k:z[k] for k in z.files}
            keys.update(a.keys());stamp+=int('t_start' in a)
            for k,v in a.items():
                if np.issubdtype(v.dtype,np.number) and not np.isfinite(v).all():
                    if k=='cfg' and p.name.startswith('ours') and v.shape==(4,) and np.isfinite(v[3]) and np.isnan(v[1:3]).all() and not np.isinf(v).any():expected_cfg.append(p.name)
                    else:errors.append(k+':nonfinite')
            i=a['idx'];m=a['meta'];n=int(m[3]);sh=int(m[1]);ns=int(m[2])
            if not np.array_equal(i,np.arange(n)[sh::ns]):errors.append('idx differs from declared partition')
            for k in ['E','npaths','nret','E_dedup','n_dup']:
                if k in a and a[k].shape!=i.shape:errors.append(k+':shape')
            with contextlib.redirect_stdout(io.StringIO()):ok=done(str(p))
            if not ok:gate_reject.append(p.name)
        except Exception as e:errors.append(type(e).__name__+':'+str(e))
        if errors:bad.append(dict(file=p.name,errors=errors))
        if p.stat().st_mtime_ns!=s0.st_mtime_ns or s0.st_mtime_ns!=r['mtime_ns']:changed.append(p.name)
        if j and j%2500==0:print('full arrays',j,flush=True)
    return dict(files=len(shards['manifest']),errors=bad,production_gate_rejected=gate_reject,changed_during_read=changed,keys=dict(keys),with_stamp=stamp,expected_cfg_nan=expected_cfg)

def scan():
    c=dict(queue=prev.queue(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),checked_at_utc=datetime.now(timezone.utc).isoformat())
    c['inventory']=repo.inventory();print('inventory',c['inventory']['file_count'],flush=True)
    c['shards']=repo.shards();c['arrays']=full_arrays(c['shards']);print('arrays done',flush=True)
    c['aggregation']=repo.zero_and_overlap(c['shards']);c['generation_current']=repo.generation_selection(c['aggregation'])
    c['previous_resume']=prev.resume_checks();c['previous_generation']=prev.generation_checks(c['shards']);c['pfa']=prev.pfa_checks()
    prev.SNAPSHOT.update(inventory=c['inventory'],shards=c['shards']);c['builders']=prev.builder_checks()
    c['publications']=repo.previous.actual_publications();c['gates']=gates()
    c['source_hashes']=dict(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')
    print('scan saved',str(CACHE),flush=True)



def waveform_checks():
    import types
    wf=loadmod('benchmark/read_wfsurvive_0912.py')
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation']
    esm=types.SimpleNamespace(SHD=str(base.SHD),one_generation=choose)
    old=base.js('outputs/read_wfsurvive_0912.json');rates=wf.net_rates()
    tree=ast.parse(base.read('src/experiment_detection.py'))
    cfg=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CPI_CFG' for t in n.targets))
    cfg=eval(compile(ast.Expression(cfg),'CPI_CFG','eval'),{'dict':dict})
    corrected=copy.deepcopy(rates)
    for r in corrected:r['frame_ms']*=cfg[r['std']]['b']
    rows=[];mismatch=[]
    for r in old['rows']:
        E,prf=wf.cell_series(esm,r['engine'],r['el_deg'])
        before=wf.survive(E,prf,rates,r['f_tip_hz']);after=wf.survive(E,prf,corrected,r['f_tip_hz'])
        if before['wifi']!=r['wifi']:mismatch.append(dict(engine=r['engine'],el=r['el_deg']))
        # Independent cumulative-sum implementation of the same discrete averaging model.
        x=E-E.mean();rr=next(v for v in corrected if v['std']=='wifi');L=max(1,round(prf*rr['frame_ms']/1000))
        starts=np.round(np.arange(0,x.size-L,prf/rr['frame_rate_hz'])).astype(int)
        cs=np.r_[0j,np.cumsum(x)];y=(cs[starts+L]-cs[starts])/L
        independent=round(float(20*np.log10(np.std(y)/(np.std(x)+1e-300)+1e-300)),2)
        assert abs(independent-after['wifi']['rms_keep_db'])<0.011
        rows.append(dict(engine=r['engine'],el=r['el_deg'],scene=r['scene'],prf=prf,
            before=before['wifi'],after=after['wifi'],independent_rms_db=independent,
            delta_db=round(after['wifi']['rms_keep_db']-before['wifi']['rms_keep_db'],2)))
    # A known single line inside the original tip band folds below the clipped band.
    fs=19700.;N=8192;f0=1550.;ft=1102.;tone=np.exp(2j*np.pi*f0*np.arange(N)/fs)
    tone_out=wf.survive(tone,fs,[dict(std='nr',frame_rate_hz=2000.,frame_ms=.5)],ft)
    alias=abs((f0+1000)%2000-1000)
    return dict(rates=rates,corrected_rates=corrected,cpi_cfg=cfg,rows=rows,published_reproduction_mismatch=mismatch,
        max_abs_delta_db=max(abs(r['delta_db']) for r in rows),median_delta_db=float(np.median([r['delta_db'] for r in rows])),
        delta_range=[min(r['delta_db'] for r in rows),max(r['delta_db'] for r in rows)],
        changed_peaks=sum(r['before']['peak_frameavg_in_tipband_hz']!=r['after']['peak_frameavg_in_tipband_hz'] for r in rows),
        tone=dict(input_hz=f0,f_tip_hz=ft,expected_alias_hz=alias,output=tone_out,
            true_line_inside_report_band=bool(tone_out['nr']['tipband_lo_hz']<=alias<=tone_out['nr']['tipband_hi_hz'])))

def timeaxis_checks(c):
    sys.path.insert(0,str(ROOT/'src'));import md_mapstyle as mp
    base.digest('src/md_mapstyle.py')
    ledger=base.js('outputs/elevation_sweep_md.json');rows={(r['engine'],r['el_deg']):r for r in ledger['rows']}
    default=float(ledger['_meta']['prf_hz']);ff=float(ledger['_meta']['f_flash_hz'])
    tr=ast.parse(base.read('benchmark/elevation_sweep_md.py'));fn=next(n for n in tr.body if isinstance(n,ast.FunctionDef) and n.name=='analyse')
    defs=[n for n in fn.body if isinstance(n,ast.FunctionDef) and n.name in ['_stft','band_metrics']]
    out=[]
    for g in c['shards']['groups']:
        if len(g['prfs'])!=1 or g['prfs'][0]==default:continue
        key=(g['engine'],g['el_deg']);r=rows.get(key)
        if r is None:continue
        E=repo.raw_merge([str(base.SHD/f) for f in g['files']])['E'];ft=r['f_tip_hz']
        vals=[]
        for prf in [default,g['prfs'][0]]:
            ns=dict(np=np,prf=prf,ffl=ff,per=mp.auto_periods(prf,ff),flash_spec=mp.flash_spec,_stft_cache={})
            exec(compile(ast.Module(body=defs,type_ignores=[]),'production band_metrics','exec'),ns)
            # f_tip is recomputed at full precision, exactly as production analyse().
            tip=base.funcs('benchmark/elevation_sweep_md.py',['f_tip_at','carrier_of'],dict(np=np,re=re,ROOT=str(ROOT),TJ=ledger['_meta'],FC=ledger['_meta']['fc_hz']))['f_tip_at'](g['el_deg'],g['engine'])
            vals.append(ns['band_metrics'](E,.35*tip,max(tip,1e-6)))
        v=E-E.mean();S=abs(np.fft.fft(v*np.hanning(len(v))));ix=int(np.argmax(S));freq=abs(np.fft.fftfreq(len(v),1/g['prfs'][0])[ix])
        out.append(dict(engine=g['engine'],el=g['el_deg'],stored_prf=g['prfs'][0],used_prf=default,
            time_axis_factor=g['prfs'][0]/default,published=r['track'],current=vals[0],with_stored_prf=vals[1],
            correct_fft_peak_hz=freq,atlas_fft_peak_hz=freq*default/g['prfs'][0]))
    atlas=base.js('outputs/md_atlas_index.json');keys={(eng,float(v['el_deg'])) for t in atlas['topics'].values() for eng,a in t['arms'].items() for v in a['cells'].values()}
    return dict(default_prf=default,rows=out,n_rows=len(out),in_atlas=sum((r['engine'],r['el']) in keys for r in out),
        mismatched_current_publication=sum(r['current']!=r['published'] for r in out),
        changed_metrics=sum(r['current']!=r['with_stored_prf'] for r in out))

def freeze_checks():
    from unittest.mock import patch
    m=loadmod('benchmark/freeze_0912.py');realjs=m.js
    data={r:base.js(r) for r in ['outputs/elevation_sweep_md.json','outputs/md_atlas_index.json','outputs/read_canyonnull_0910.json']}
    fake=type('Result',(),dict(returncode=0,stdout='isolated gate output',stderr=''))()
    def measure():
        with patch.object(m,'js',lambda rel:copy.deepcopy(data[rel])),patch.object(m.subprocess,'run',return_value=fake):return m.measure()
    original=measure();mut=copy.deepcopy(data['outputs/read_canyonnull_0910.json'])
    changed=[]
    def walk(o,path=''):
        if isinstance(o,dict):
            for k,v in o.items():
                p=path+'.'+k
                if k in ['n_static_changed','n_hampel','n_changed','n_mask'] and isinstance(v,int):changed.append(dict(path=p,before=v,after=v+17));o[k]=v+17
                else:walk(v,p)
        elif isinstance(o,list):
            for i,v in enumerate(o):walk(v,path+f'[{i}]')
    walk(mut);data['outputs/read_canyonnull_0910.json']=mut;after=measure()
    # Equality tests production measures, without real-file edits or freezing a new baseline.
    return dict(mutated_fields=changed,measure_changed=original!=after,
        before_canyon=original['canyon_events'],after_canyon=after['canyon_events'],
        measured_keys=list(original),baseline_has_dropladder=any('drop' in k for k in original),
        limitation='Gate subprocess return values held fixed; the actual measure() and source-reader path were executed.')


def additional_checks(c):
    out={}
    for name,fn in [('waveform',waveform_checks),('timeaxis',lambda:timeaxis_checks(c)),('freeze',freeze_checks)]:
        out[name]=fn();print('additional',name,flush=True)
    c['additional']=out;c['source_hashes'].update(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')



def boundary_checks():
    import types
    wf=loadmod('benchmark/read_wfsurvive_0912.py')
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation']
    res=[]
    for case in ['different_prf','unresolved_generation']:
        with tempfile.TemporaryDirectory() as td:
            fs=[];N=8
            for k in range(2 if case=='different_prf' else 4):
                idx=np.arange(k%2,N,2);f=Path(td)/f'arm_el+0_{k:02d}.npz'
                np.savez(f,idx=idx,E=np.full(idx.size,1+0j if k<2 else 2+0j),meta=[0,k%2,2,N,10000 if case=='different_prf' and k==1 else 19700,0],t_start=[1700000000.])
                fs.append(str(f))
            with contextlib.redirect_stdout(io.StringIO()):kept,note=choose(fs,'fixture')
            esm=types.SimpleNamespace(SHD=td,one_generation=choose)
            try:out=wf.cell_series(esm,'arm',0.);err=None
            except Exception as e:out=None;err=type(e).__name__
            res.append(dict(case=case,returned_series=out is not None,error=err,returned_prf=out[1] if out else None,selection_note=note))
    # The existing audit's isolated save call grew a dependency it does not provide.
    try:repo.save_interruption();error=None
    except Exception as e:
        import traceback
        error=dict(type=type(e).__name__,message=str(e),traceback=traceback.format_exc())
    return dict(waveform_inputs=res,old_audit_failure=error,dsp_api_check=repo.dsp_checks()['pfa'])


def design_and_literature():
    # The stored complex field explicitly includes exp(-j 2 pi f tau).
    base.digest('runners/make_jobs_0929.py');base.digest('benchmark/elevation_sweep_md.py')
    r=15.;c0=299792458.;fc=np.array([3.450,3.475,3.500,3.525,3.550])*1e9;tau=2*r/c0
    transfer=np.exp(-2j*np.pi*(fc-fc[2])*tau)
    flat=dict(range_m=r,tau_s=tau,frequency_hz=fc.tolist(),constant_scatter_coefficient=1.,
        propagated_phase_deg=np.angle(transfer,deg=True).tolist(),max_complex_difference_from_center=float(abs(transfer-1).max()),
        after_removing_known_delay_max_error=float(abs(transfer*np.exp(2j*np.pi*(fc-fc[2])*tau)-1).max()),
        grid_spacing_hz=float(fc[1]-fc[0]),delay_alias_s=float(1/(fc[1]-fc[0])),
        limitation='Analytic point scatterer counterexample; no result from the pending frequency sweep is asserted.')
    survey=loadmod('prior_work/src/build_toptier_0911.py');p=Path(survey.STORE)/'toptier_0911.json';data=base.js(p)
    bydoi={r['doi'].lower():r for r in data['rows']};anchors=survey.check_anchors(bydoi)
    return dict(frequency_design=flat,literature=dict(path=str(p),n_rows=len(data['rows']),n_abstracts=sum(bool(r.get('abstract')) for r in data['rows']),
        anchors=anchors,stored_recall=data['_meta']['recall'],duplicate_dois=len(data['rows'])-len(bydoi),
        scope='Local stored metadata and anchor lookup verified; papers and external indexes were not all re-read.'),
        current_readme_sources=[base.source('prior_work/README.md','2025-01 이후 **275 편**'),base.source('prior_work/README.md','재현율(아는 6 편)')])


def wide_artifact_check():
    # Enumerate ignored files too, explicitly separate from the earlier rg-based inventory.
    files=[];broken=[];counts=collections.Counter();json_errors=[];nb_errors=[];names=collections.Counter();syntax=[];parsed=collections.Counter();recent=[]
    for d,dirs,ns in os.walk(ROOT):
        dirs[:]=[v for v in dirs if v not in ['.git','__pycache__']]
        for n in ns:
            p=Path(d)/n;rel=str(p.relative_to(ROOT));counts[rel.split('/')[0] if '/' in rel else '(root)']+=1
            if p.is_symlink() and not p.exists():broken.append(rel);continue
            if not p.is_file():continue
            files.append(rel);names[p.suffix]+=1
            if p.suffix=='.py':
                try:
                    import warnings
                    with warnings.catch_warnings():warnings.simplefilter('ignore');ast.parse(p.read_text())
                    parsed['python']+=1
                except Exception as e:syntax.append(dict(path=rel,error=type(e).__name__))
            if p.suffix not in ['.json','.ipynb']:continue
            if p.stat().st_mtime>time.time()-120:recent.append(rel);continue
            try:
                with p.open() as fh:j=json.load(fh)
                parsed[p.suffix]+=1
                if p.suffix=='.ipynb' and (not isinstance(j,dict) or not isinstance(j.get('cells'),list)):nb_errors.append(rel)
            except Exception as e:
                (nb_errors if p.suffix=='.ipynb' else json_errors).append(dict(path=rel,error=type(e).__name__))
    return dict(enumerator='os.walk excluding .git and __pycache__; includes ignored files, assets and archives',file_count=len(files),root_counts=dict(counts),extensions=dict(names),broken_symlinks=broken,json_parse_errors=json_errors,notebook_errors=nb_errors,syntax_errors=syntax,parsed=dict(parsed),recent_skipped=recent,
        limitation='Binary geometry/PDF/image bytes were enumerated, not re-rendered or semantically validated.')


def final_probes(c):
    # Reclassify declared not-applicable cfg slots using source schema, not blanket isfinite.
    raw=c['arrays'];expected=[];remaining=[]
    for r in raw['errors']:
        if r['errors']==['cfg:nonfinite'] and r['file'].startswith('ours'):
            with np.load(base.SHD/r['file']) as z:v=z['cfg']
            if v.shape==(4,) and np.isfinite(v[3]) and np.isnan(v[1:3]).all() and not np.isinf(v).any():expected.append(r['file']);continue
        remaining.append(r)
    raw['errors']=remaining;raw['expected_cfg_nan']=expected or raw.get('expected_cfg_nan',[])
    c['additional']['freeze']=freeze_checks()
    for name,fn in [('boundary',boundary_checks),('design_literature',design_and_literature),('wide_artifacts',wide_artifact_check)]:
        c['additional'][name]=fn();print('final probes',name,flush=True)
    c['source_hashes'].update(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')



def filter_design_check():
    fn=base.funcs(ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py',['hampel_mask'],dict(np=np))['hampel_mask']
    N=8192;t=np.arange(N);free=1+.1*np.sin(2*np.pi*t/512);scene=2*free
    mask=fn(scene,51,5.0);g=np.flatnonzero(~mask);b=np.flatnonzero(mask);filtered=scene.copy()
    if b.size:filtered[b]=np.interp(b,g,scene[g])
    return dict(N=N,win=51,k=5.,mask_count=int(mask.sum()),after_filter_above_free=int((filtered>free).sum()),
        filter_change_max=float(abs(filtered-scene).max()),
        switch_bits=dict(R0D1E1F1=dict(refraction=False,diffraction=True,edge_diffraction=True,diffuse=True,specular_reflection=True)),
        scope='Analytic time series passed through the existing Hampel mask; no scene physics is inferred.')


def scope_summaries(c):
    w=c['additional']['waveform'];published=base.js('outputs/read_wfsurvive_0912.json')['rows'];groups=collections.defaultdict(list)
    for r in published:groups[(r['scene'],r['el_deg'],r['arm'])].append(r['engine'])
    sub=[r for r in w['rows'] if r['scene']!='free' and r['el'] in [-30,-60]]
    w['outdoor_el30_el60']=dict(n=len(sub),min_delta_db=min(r['delta_db'] for r in sub),max_delta_db=max(r['delta_db'] for r in sub))
    w['display_identity']=dict(negative_az_rows=sum('_az-' in r['engine'] for r in published),prf_rows=sum('_prf' in r['engine'] for r in published),
        rotor_variants=sum('_rot' in r['engine'] for r in published),ambiguous_groups=[dict(scene=k[0],el=k[1],arm=k[2],engines=v) for k,v in groups.items() if len(v)>1])
    c['additional']['filter_design']=filter_design_check()
    c['additional']['wide_artifacts']=wide_artifact_check()
    c['queue_final']=prev.queue()
    c['queue_completed_logs']={str(p.relative_to(ROOT)):[ln for ln in p.read_text().splitlines() if '== 종료' in ln][-1:] for p in sorted((ROOT/'runners/logs').glob('sup_jobs_092[3-6].log'))}
    c['source_hashes'].update(base.HASHES)
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')


def other_arrays():
    import zipfile
    errors=[];recent=[];changed=[];objects=[];manifest=[]
    for p in sorted(ROOT.rglob('*.npz')):
        if 'elev_sweep_shards' in p.parts or '.git' in p.parts:continue
        s=p.stat();rel=str(p.relative_to(ROOT))
        if s.st_mtime>time.time()-120:recent.append(rel);continue
        try:
            with zipfile.ZipFile(p) as z:
                bad=z.testzip()
                if bad:errors.append(dict(file=rel,error='CRC',member=bad))
                members=z.namelist()
                for name in members:
                    if not name.endswith('.npy'):continue
                    with z.open(name) as f:
                        ver=np.lib.format.read_magic(f)
                        if ver==(1,0):shape,fort,dtype=np.lib.format.read_array_header_1_0(f)
                        elif ver==(2,0):shape,fort,dtype=np.lib.format.read_array_header_2_0(f)
                        else:
                            import struct
                            size=struct.unpack('<I',f.read(4))[0];h=ast.literal_eval(f.read(size).decode('utf-8'))
                            shape,fort,dtype=h['shape'],h['fortran_order'],np.dtype(h['descr'])
                        if dtype.hasobject:objects.append(dict(file=rel,member=name))
                manifest.append(dict(file=rel,bytes=s.st_size,members=len(members),mtime_ns=s.st_mtime_ns))
        except Exception as e:errors.append(dict(file=rel,error=type(e).__name__,message=str(e)))
        if p.stat().st_mtime_ns!=s.st_mtime_ns:changed.append(rel)
    return dict(n_files=len(manifest),manifest=manifest,errors=errors,recent_skipped=recent,changed_during_read=changed,
        object_members=objects,scope='CRC and NPY headers; object arrays were not unpickled, scientific values not recomputed.')


def make_findings(c):
    a=c['additional'];out=[]
    def add(title,severity,scope,evidence,fix,refs,key):
        sources=[base.source(p,n) for p,n in refs];assert all(s['found'] for s in sources),sources
        out.append(dict(title=title,severity=severity,scope=scope,evidence=evidence,fix=fix,sources=sources,result_key=key))
    t=a['timeaxis'];ex=t['rows'][0]
    add('주 집계와 아틀라스가 표집률 사다리를 기본 시간축으로 읽는다','발간 지표·그림 축에 영향',
        '원본 샤드와 현재 발간 원장을 대조하고, 생산 band_metrics에서 표집률만 바꿔 재계산했다.',
        f"저장 표집률이 기본 {t['default_prf']:g} Hz와 다른 {t['n_rows']}칸이 있고, {t['in_atlas']}칸이 아틀라스에도 있다. "
        f"현재 생산식은 발간값과 {t['mismatched_current_publication']}칸 불일치였으며, 저장 표집률을 적용하면 {t['changed_metrics']}칸의 track 지표가 바뀐다. "
        f"예: {ex['engine']} / el{ex['el']:+g}에서 beat_hz는 {ex['current']['beat_hz']} → {ex['with_stored_prf']['beat_hz']} Hz다. "
        '저장 표집률에 비해 주파수축이 줄고 시간축이 늘어난다. 이 재계산은 표집률 효과만 분리했으며 다른 기체별 잣대의 타당성까지 인증하지 않는다.',
        '샤드 meta[4]를 칸별 prf_hz로 발행하고 일치 여부를 검사한다. STFT 창·시간축·리듬 지표·아틀라스에 그 값을 전달한 뒤 영향받는 원장과 그림을 재생성한다.',
        [('benchmark/elevation_sweep_md.py','prf, ffl = float(TJ["prf_hz"])'),('benchmark/build_md_atlas.py','PRF = float(M["prf_hz"])')],'additional.timeaxis')
    w=a['waveform'];wifi=next(r for r in w['rates'] if r['std']=='wifi');corr=next(r for r in w['corrected_rates'] if r['std']=='wifi');sub=w['outdoor_el30_el60']
    add('Wi-Fi 프레임 평균 길이에 블록 수가 빠졌다','신규 발간값에 영향',
        '현재 파형 원장의 모든 행을 원본 E로 재현하고, 평균 길이만 바꿨다. 누적합 구현으로 별도 검산했다.',
        f"CPI_CFG의 Wi-Fi 프레임은 b={w['cpi_cfg']['wifi']['b']}개 블록이다. 판독기는 주석의 블록 길이 {wifi['frame_ms']:g} ms만 읽어 "
        f"프레임 길이 {corr['frame_ms']:g} ms 대신 쓴다. {len(w['rows'])}행의 현재 Wi-Fi 값은 모두 재현됐다. "
        f"평균 길이 보정 시 rms_keep_db 변화의 중앙값은 {w['median_delta_db']:.2f} dB이고, 양·음 변화가 모두 있다. "
        f"실외 el−30/−60 {sub['n']}칸에서는 {sub['min_delta_db']:+.2f}~{sub['max_delta_db']:+.2f} dB다. "
        '전체 최댓값 하나를 대표 효과로 인용하면 표본 선택과 조건 차이를 숨기게 된다.',
        '주석 대신 실제 블록 길이·블록 수·표집률에서 프레임 길이와 반복률을 함께 유도한다. 현재의 이산 평균 모형 안에서 보정한 뒤 파형 표를 다시 생성한다.',
        [('benchmark/read_wfsurvive_0912.py','blk_ms = float(bl.group(1))'),('src/experiment_detection.py','"wifi": dict(M=112, b=9)')],'additional.waveform')
    tone=w['tone'];nr=tone['output']['nr']
    add('접힌 주파수 띠를 잘라서 실제 주성분을 제외한다','분석 방법 결함 · 합성 반례',
        '기존 survive()에 단일 복소 정현파를 넣었다.',
        f"입력 {tone['input_hz']:g} Hz는 날개끝 기준 {tone['f_tip_hz']:g} Hz의 원래 띠 안에 있다. "
        f"프레임율 {nr['frame_rate_hz']:g} Hz에서 실제 접힘은 {tone['expected_alias_hz']:g} Hz지만, 판독 띠는 "
        f"{nr['tipband_lo_hz']:g}~{nr['tipband_hi_hz']:g} Hz다. 전체 FFT는 {nr['peak_frameavg_hz']:.2f} Hz를 찾고, "
        f"띠 안 최강선은 {nr['peak_frameavg_in_tipband_hz']:.2f} Hz를 반환한다. 예상한 선을 스스로 제외한 뒤 다른 성분을 고른 것이다.",
        '입력 띠 전체를 접힘 사상으로 옮겨 구간의 합집합을 만든다. 입력 피크와 접힌 피크의 대응도 따로 확인한다. 단순한 상한 자르기나 접힌 중심 주변의 임의 비율 띠를 대체한다.',
        [('benchmark/read_wfsurvive_0912.py','if lo >= ny:'),('benchmark/read_wfsurvive_0912.py','return lo, min(hi, ny)')],'additional.waveform.tone')
    ident=w['display_identity'];b=a['boundary']['waveform_inputs']
    add('파형 표가 서로 다른 조건을 같은 행 이름으로 표시한다','현재 문면 영향 · 입력 검증의 잠재 결함',
        '발간 행의 engine과 사람이 읽는 표의 장면·앙각·팔 열을 대조했다. 시간축·세대 충돌은 임시 샤드로 시험했다.',
        f"선택 목록에 음수 방위 {ident['negative_az_rows']}행, 표집률 변경 {ident['prf_rows']}행, 로터 설정 꼬리표 {ident['rotor_variants']}행이 들어간다. "
        f"장면·앙각·팔 표시가 같은 묶음은 {len(ident['ambiguous_groups'])}개다. JSON의 engine으로는 구별되지만 Markdown 표에서는 생략된다. "
        f"별도 합성 시험에서는 서로 다른 PRF의 두 샤드도 반환={b[0]['returned_series']}, "
        f"세대 선택 뒤 충돌 {b[1]['selection_note']['kept_conflicting_poses']}자세가 남아도 반환={b[1]['returned_series']}였다. "
        '후자의 손상이 현재 발간 입력에서 발견됐다는 뜻은 아니다.',
        '기체·방위·표집률·로터 설정을 명시적 조건으로 선택하고 표에도 표시한다. 공통 로더에서 PRF·N·idx·유한값과 선택 후 충돌 상태를 검사하고 제외 사유를 기록한다.',
        [('benchmark/read_wfsurvive_0912.py','and not re.search(r"_(ps|fs|bs|az'),('benchmark/read_wfsurvive_0912.py','fs, _ = esm.one_generation')],'additional.waveform.display_identity')
    f=a['freeze']
    add('기준선 검사가 사건 수의 변화를 놓친다','기준선 검증 기능에 영향',
        '원장을 메모리에 복제해 사건 수를 바꿨고, 실제 measure()를 실행했다. 별도 검사기의 반환은 동일하게 유지했다.',
        f"협곡의 사건 수·Hampel 마스크 수 {len(f['mutated_fields'])}필드를 바꿔도 measure 변경={f['measure_changed']}였다. "
        '해당 원장은 사건 수를 구조적으로 보존하지 않고 문자열 안에 특정 숫자가 있는지만 검사한다. '
        f"낙차 사다리 측정 키 포함={f['baseline_has_dropladder']}다. 저장된 보고서의 숫자를 읽는 방식이므로 원본 샤드가 바뀌고 상류 보고서가 낡으면 그것도 직접 재계산하지 않는다. "
        '새 파일 관문은 이 기준선 원장의 _meta.generator 누락도 보고했다.',
        '조건별 실제 사건 수·집합 식별자·선택 파일 해시를 저장한다. 낙차 원장도 포함하고, 샤드 재계산 또는 상류 최신성 확인을 구분해 검사한다. generator를 정해진 메타 위치로 옮긴다.',
        [('benchmark/freeze_0912.py','m["canyon_events"]["has_96"]'),('benchmark/freeze_0912.py','m["canyon_events"]["has_339"]')],'additional.freeze')
    f=a['filter_design']
    add('실외 발주서의 물리 이름과 필터 판정 기준을 고쳐야 한다','실험 설계·해석 문면',
        '발주서의 팔 이름을 실제 스위치 해석과 대조했고, 기존 Hampel 함수로 인과 반례를 계산했다.',
        '발주서는 R0D1E1F1을 «굴절+모서리»로 설명하지만 실제 설정은 굴절 꺼짐·회절 켜짐·모서리회절 켜짐이다. '
        '또 «여러 앙각에서 계속 위로 뜨면 필터가 만든 구조»라는 판정은 대조가 부족하다. '
        f"합성 입력에서는 필터 마스크 {f['mask_count']}개, 필터 변화 {f['filter_change_max']:g}인데 "
        f"빈 하늘보다 높은 자세가 {f['after_filter_above_free']}/{f['N']}개다. 필터 후 차이만으로 필터가 만든 효과를 판정할 수 없다.",
        'R=굴절·D=회절·E=모서리회절을 정확히 적고 정반사는 별도 상시 설정임을 구분한다. 동일 입력의 필터 전후 변화와 장면·빈 하늘 양쪽의 동일 처리 결과를 함께 비교한다. 지면·건물 기여 해석에는 차폐와 경로 상호작용도 남긴다.',
        [('runners/make_jobs_0928.py','A 지면만·건물만 +굴절+모서리'),('runners/make_jobs_0928.py','여러 앙각에서 계속 위로 뜨면'),('benchmark/elevation_sweep_md.py','sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)')],'additional.filter_design')
    f=a['design_literature']['frequency_design']
    add('0929의 복소 평탄성에는 전파 지연 기준이 먼저 필요하다','대기 중인 실험의 해석 설계',
        '생산 E의 위상 정의를 확인하고, 산란계수가 일정한 점 표적을 해석식으로 계산했다.',
        f"거리 {f['range_m']:g} m 점 표적의 산란계수를 일정하게 둬도 지정한 주파수 격자에서 위상은 "
        f"{[round(v,2) for v in f['propagated_phase_deg']]}도로 움직인다. 중앙과의 복소 차이는 최대 "
        f"{f['max_complex_difference_from_center']:.6f}이고, 알려진 전파 지연을 제거하면 오차가 {f['after_removing_known_delay_max_error']:.2g}다. "
        '원본 E는 경로 전파 위상을 포함하므로 이를 그대로 반사율의 주파수 의존성이라고 읽으면 혼동된다. 대기 중인 실험의 결과를 미리 판정한 것은 아니다.',
        '원시 채널 응답과 공통 지연을 제거한 표적 응답을 나란히 정의한다. 대역 안 성긴 점검이 부반송파 전부의 평탄성을 보증하는 범위도 구분한다. 동일 자세·솔버 설정·수치 민감도를 맞춘 뒤 해석한다.',
        [('runners/make_jobs_0929.py','네 점의 복소 반사율이 크기·위상 모두'),('benchmark/elevation_sweep_md.py','_t = aa[hit] * np.exp(-1j * 2 * np.pi * fc * tau[hit])')],'additional.design_literature.frequency_design')
    f=a['boundary']['old_audit_failure']
    add('기존 전체 감사 생성기는 다른 의존성 누락으로 멈춘다','점검 도구의 실행 실패',
        '기존 main을 임시 출력으로 실행하고 실패 함수를 별도로 재현했다.',
        f"Pfa 예외 처리는 수정됐지만, 저장 중단 시험에서 현재 {f['type']}({f['message']})가 발생한다. "
        '생산 저장 호출에 bake_stamp(t0)가 추가됐는데 AST로 호출을 떼어 실행하는 시험 환경에는 그 함수가 없다. '
        '따라서 저장 중단을 주입하기 전에 실패하며 기존 보고서를 다시 생성하지 못한다. 이는 생산 워커의 실패와 구분된다.',
        '생산 저장 함수와 의존성을 함께 불러 실행한다. 장기적으로는 저장 경로를 작은 함수로 분리해, AST 내부 줄을 떼어내는 시험의 의존성 누락을 줄인다.',
        [('benchmark/review_repository_0911.py',"assert failure=='OSError',failure"),('benchmark/elevation_sweep_md.py','**bake_stamp(t0),')],'additional.boundary.old_audit_failure')
    l=a['design_literature']['literature']
    add('선행연구 README가 갱신 전 조사와 옛 원인 설명을 유지한다','현재 안내 문서의 불일치',
        '로컬 외부 저장 원장과 README를 대조했다. 개별 논문 전체나 외부 색인은 재검토 범위 밖이다.',
        f"저장 원장은 {l['n_rows']}편·초록 {l['n_abstracts']}편이며, 점검 가능한 기준 논문의 DOI 발견은 "
        f"{l['stored_recall']['found']}/{l['stored_recall']['total']}이다. README는 이전 편 수와 다른 분모의 재현율을 «지금»으로 표시하고, "
        '이미 수정한 제목 검색 실패의 원인도 예전 설명으로 남긴다. 기준 논문 몇 편의 발견률을 전체 관련 논문의 검색 재현율로 넓혀 읽을 수도 있다.',
        'README 요약을 현재 원장에서 생성하고 이전 표에는 기준 날짜를 붙인다. DOI가 확인되는 범위 내 기준 논문의 발견률이라는 이름과 분모를 유지하며 전체 문헌의 망라율과 구분한다.',
        [('prior_work/README.md','2025-01 이후 **275 편**'),('prior_work/README.md','재현율(아는 6 편)')],'additional.design_literature.literature')
    return out


def render_report(o):
    c=o['checks'];a=c['additional'];wide=a['wide_artifacts'];j=str(OUT.relative_to(ROOT));q=c['queue_final']
    lines=['# 시오나 현재 상태 전수 점검','',f"조사 시작 {c['checked_at_utc']} · 작성 {o['_meta']['made_utc']} · 초기 기준 커밋 `{c['head']}`",'',
        '[주피터 보고서](FULL_REVIEW_0912.ipynb) · [검증 원장](../outputs/full_review_0912.json) · [생성기](../benchmark/review_full_0912.py)','',
        f"추가 점검 커밋 `{a['late_scene']['head']}`: 조사 중 새로 들어온 장면 판독기의 {a['late_scene']['n_rows']}행을 별도로 재현했다.",'',
        '## 먼저 읽을 결과','',
        '이전 CRC·배열 길이 반례와 파일 시각 변경 반례는 수정됐다. 현재 원본 발간 사건도 재현됐다. '
        '이번에는 표집률 사다리와 새 파형 분석의 발간 지표, 기준선 검증, 다음 실험의 해석 기준에서 보완점을 확인했다.','',
        '## 조사 범위','',
        '| 대상 | 검사 | 결과 |','|---|---|---|',
        f"| 숨김·보관 포함 파일 {wide['file_count']}개 | .git·__pycache__ 제외 열거 | 바이너리 내용의 과학적 타당성과는 별도 |",
        f"| Python {wide['extensions']['.py']}개 | 문법 파싱 | 성공 {wide['parsed']['python']}개, 코드 조각 파일의 문법 오류 {len(wide['syntax_errors'])}개 |",
        f"| JSON {wide['parsed']['.json']}개·노트북 {wide['parsed']['.ipynb']}개 | 실제 파싱 | 오류 {len(wide['json_parse_errors'])+len(wide['notebook_errors'])}개 |",
        f"| 생산 샤드 {c['arrays']['files']}개 | 모든 배열 CRC·shape·유한값·idx 분할·완료 함수 | 오류 {len(c['arrays']['errors'])}개, 판독 중 변경 {len(c['arrays']['changed_during_read'])}개 |",
        f"| 나머지 NPZ {a['other_arrays']['n_files']}개 | CRC·NPY 헤더, 객체 역직렬화 제외 | 오류 {len(a['other_arrays']['errors'])}개 |",
        f"| 기존 발간 사건 원본 {c['publications']['union_shards']}개 | 협곡·낙차·동체 판독 재계산 | 기존 발간값과 일치 |",
        f"| 파형 원장 {len(a['waveform']['rows'])}행 | 현재 값 재현·평균 길이 대조·독립 누적합 검산 | 아래 지적 참조 |",
        f"| 표집률 사다리 {a['timeaxis']['n_rows']}칸 | 생산식·발간값·저장 표집률 비교 | 아래 지적 참조 |",'',
        f"우리 커널 cfg의 NaN {len(c['arrays']['expected_cfg_nan'])}파일은 깊이·광선 예산의 미해당 표식으로 코드에 정의돼 있어 결함에서 제외했다. "
        '문법 오류 파일 outputs/_prop_law_literals_0816.py는 실행 스크립트가 아닌 붙여 넣기용 딕셔너리 조각이다. '
        '미완 칸은 계산 진행 상태와 분할 세대 선택을 구분해 읽어야 한다. 메쉬·사진·PDF의 내용 전체 판정이나 GPU 재실험은 이번 범위에 포함되지 않는다.','',
        f"⟨{j} : checks.additional.wide_artifacts⟩ ⟨{j} : checks.arrays⟩ ⟨{j} : checks.additional.other_arrays⟩",'',
        '## 실행 상태','',f"{q['checked_at_utc']} 조회에서 워커 {q['workers']}개, 감독자와 지킴이 실행을 확인했다. 큐 분수는 투입 포인터다.",'']
    for v in q['supervisor_logs']:lines += [f"- `{v['job']}`: {v['last_lines'][-1]}"]
    lines+=['']
    for p,v in c['queue_completed_logs'].items():lines += [f"- `{p}`: {v[-1] if v else '종료 기록 미확인'}"]
    lines+=['','현재 사슬의 후속 차례는 0929 → 0928이다. 작업 중 수치는 변하므로 위 조회 시각을 함께 읽는다.','',
        '## 확인된 보완점','']
    for i,f in enumerate(o['findings'],1):
        lines += [f"### {i}. {f['title']}",'',f"**영향:** {f['severity']}",'',f"**검증 범위:** {f['scope']}",'',f['evidence'],'','**수정 제안:** '+f['fix'],'',f"⟨{j} : checks.{f['result_key']}⟩",'']
        for s in f['sources']:lines += [f"- [{s['path']}:{s['line']}](../{s['path']}#L{s['line']})",'```python',s['quote'],'```','']
    lines+=['## 관문 결과와 해석 한계','',
        '관문 통과는 해당 검사기가 다루는 범위의 결과다. 링크 존재·조건 선택의 일치가 문장 속 수치나 인과 설명까지 인증하지 않는다.','']
    for k,v in c['gates'].items():lines += [f"- `{k}`: exit {v['exit']}",'```text',v['stdout'].strip(),'```','']
    lines += ['## 수정 순서','',
        '1. 새 장면 판독기의 대조군을 맞추고, 표집률과 Wi-Fi 프레임 길이를 고쳐 영향받는 수치·그림·표를 재생성한다.',
        '2. 파형의 접힘 띠와 조건 선택·공통 입력 검증을 고친다.',
        '3. 기준선 비교가 사건 수 변경을 감지하도록 만들고 감사 생성기를 현재 저장 경로에 맞춘다.',
        '4. 대기 실험의 해석 기준과 선행연구 안내 문서를 수정한다.','',
        '기존 원장·생산 코드·GPU 워커를 변경하지 않았다. 새 점검 생성기·원장·메모·노트북만 작성했다. '
        '합성 반례가 현재 실험에서 발생했다고 일반화하지 않았으며, 모든 이진 자산의 내용까지 읽었다고 주장하지 않는다.','',
        '```bash',f'{sys.executable} benchmark/review_full_0912.py','```','']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'));from report_style import header,md,next_steps,build_notebook
    cells=[header(num='현재 전수 점검',title='저장 자료·분석 시간축·실험 해석 점검',did='현재 저장소를 열거하고 원본·생산 함수·발간 기록을 대조했다.',
        results=[f"생산 샤드 {c['arrays']['files']}개 전체 배열을 검사했다 ⟨{j} : checks.arrays⟩.",
            f"표집률 사다리 {a['timeaxis']['n_rows']}칸을 재계산했다 ⟨{j} : checks.additional.timeaxis⟩.",
            f"파형 원장 {len(a['waveform']['rows'])}행을 재현했다 ⟨{j} : checks.additional.waveform⟩.",
            f"보완점 {len(o['findings'])}건을 범위별로 기록했다 ⟨{j} : findings⟩."],
        method=[('재고','전체 파일 열거와 배열·JSON·노트북 검사'),('수치','원본 재계산·합성 대조·생산 함수 실행')],
        repro=dict(cmd=[f'{sys.executable} benchmark/review_full_0912.py'],out=[j],runtime='CPU 한 코어, 저장 자료 검사'))]
    cells.append(md('## 범위와 실행 상태','',f"전체 열거 {wide['file_count']}개. 바이너리 자산은 열거했고, 내용 전부의 과학적 타당성 평가는 별도 작업이다.",'',f"[검사별 범위와 큐 조회 기록](FULL_REVIEW_0912.md) ⟨{j} : checks.additional.wide_artifacts⟩"))
    for i,f in enumerate(o['findings']):cells.append(md(f"## {i+1}. {f['title']}",'',f['fix'],'',f"[범위·반례·코드 인용](FULL_REVIEW_0912.md) ⟨{j} : findings[{i}]⟩"))
    cells.append(next_steps([('시간축과 평균 길이를 보정한다','발간 지표의 변화 범위','FULL_REVIEW_0912.md'),('입력·기준선 검사를 강화한다','자료 선택과 변화 검출','FULL_REVIEW_0912.md'),('발주서의 판정을 관찰로 바꾼다','다음 실험이 답하는 범위','FULL_REVIEW_0912.md')]))
    build_notebook(str(NB),cells,strict=True)


def publish(c):
    fs=make_findings(c);base.digest(__file__)
    hashes=dict(c['source_hashes']);hashes.update(base.HASHES)
    hashes[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    o=dict(_meta=dict(generator='benchmark/review_full_0912.py',made_utc=datetime.now(timezone.utc).isoformat(),source_sha256=hashes),checks=c,findings=fs)
    OUT.write_text(json.dumps(o,ensure_ascii=False,indent=1,allow_nan=False)+'\n');render_report(o)
    print('published',len(fs),'findings',str(MD))


def late_scene_check():
    import types
    m=loadmod('benchmark/read_scenephysics_0913.py');old=base.js('outputs/read_scenephysics_0913.json')
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation']
    esm=types.SimpleNamespace(SHD=str(base.SHD),one_generation=choose)
    filters=base.funcs(ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py',['hampel_mask','drop_outliers'],dict(np=np))
    rows=[]
    for r in old['rows']:
        desired=re.sub(r'_env(?:sionna-simple_street_canyon|outdoor01_ground|outdoor01_bldg|outdoor01)(?=_|$)','',r['engine'])
        Es=m.series(esm,r['engine'],r['el_deg']);Ef=m.series(esm,r['free_engine'],r['el_deg']);Efix=m.series(esm,desired,r['el_deg'])
        Er,n=filters['drop_outliers'](Es,51,5.)
        current=round(m.db(np.std(Er-Er.mean()))-m.db(np.std(Ef-Ef.mean())),2)
        computed=dict(above_free_db=current,n_replaced=int(filters['hampel_mask'](np.abs(Es),51,5.).sum()),n_replaced_dropfn=n,
            level_scene_db=m.db(np.abs(Es).mean()),level_free_db=m.db(np.abs(Ef).mean()),
            lift_db=round(m.db(np.abs(Es).mean())-m.db(np.abs(Ef).mean()),2),
            ac_after_db=m.db(np.std(Er-Er.mean())),ac_free_db=m.db(np.std(Ef-Ef.mean())))
        assert all(computed[k]==r[k] for k in computed),(r['engine'],computed)
        fixed=round(m.db(np.std(Er-Er.mean()))-m.db(np.std(Efix-Efix.mean())),2) if Efix is not None else None
        # Independent variance formula, same population variance convention.
        if Efix is not None:
            def rms(E):return np.sqrt(np.mean(abs(E-E.mean())**2))
            independent=round(round(float(20*np.log10(rms(Er)+1e-300)),2)-round(float(20*np.log10(rms(Efix)+1e-300)),2),2)
            assert independent==fixed
        rows.append(dict(scene=r['scene'],arm=r['arm'],el=r['el_deg'],engine=r['engine'],chosen_free=r['free_engine'],matched_free=desired,
            selected_wrong=r['free_engine']!=desired,matched_exists=Efix is not None,n_replaced=n,
            published_above_db=current,matched_above_db=fixed,delta_db=round(fixed-current,2) if fixed is not None else None,
            sign_flip=(current>0)!=(fixed>0) if fixed is not None else None))
    return dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),rows=rows,n_rows=len(rows),
        selected_wrong=sum(r['selected_wrong'] for r in rows),missing_matched=sum(not r['matched_exists'] for r in rows),
        sign_flips=sum(bool(r['sign_flip']) for r in rows),max_abs_delta_db=max(abs(r['delta_db']) for r in rows if r['delta_db'] is not None),
        scope='Latest commit added during audit. Published values reproduced; only the free-space engine identity was changed for comparison.')

_original_make_findings=make_findings

def make_findings(c):
    findings=_original_make_findings(c)
    late=c['additional'].get('late_scene')
    if late is None:return findings
    ex=max((r for r in late['rows'] if r['delta_db'] is not None),key=lambda r:abs(r['delta_db']))
    refs=[('benchmark/read_scenephysics_0913.py','free[(a.group(1), r["el_deg"])] = r["engine"]'),
          ('benchmark/read_scenephysics_0913.py','fengine = free.get((arm, el))'),
          ('benchmark/read_scenephysics_0913.py','ARMS = {"R0D0E0F1"')]
    sources=[base.source(p,n) for p,n in refs];assert all(s['found'] for s in sources)
    findings.insert(0,dict(title='새 장면 분석이 다른 조건의 빈 하늘을 대조군으로 선택한다',severity='최신 발간 수치와 위·아래 판정에 영향',
        scope=late['scope'],
        evidence=f"조사 중 추가된 장면 원장 {late['n_rows']}행을 재현했다. 그중 {late['selected_wrong']}행은 장면 꼬리표만 제거한 동일 조건의 빈 하늘과 다른 engine을 선택했다. "
          f"올바른 짝의 누락은 {late['missing_matched']}행이며, 대조군만 맞추면 표의 0 dB 초과 표시가 {late['sign_flips']}행에서 바뀐다. "
          f"최대 변화 {late['max_abs_delta_db']:.2f} dB는 {ex['scene']} / {ex['arm']} / el{ex['el']:+g}에서 "
          f"{ex['published_above_db']:+.2f} → {ex['matched_above_db']:+.2f} dB다. "
          'free 사전이 스위치·앙각만 키로 사용해 다른 기체·로터 설정·표집률의 후보가 덮어쓴다. 발간값의 재현만으로는 대조군 선택의 타당성을 검증할 수 없다. '
          '최대 차이가 난 el 0 값은 대조군 오류의 산술적 영향이며 물리 결과의 인용값으로 쓰지 않는다. '
          '이 새 판독기의 ARMS 설명에도 회절을 굴절로, 굴절을 반사로 적은 이름 혼동이 반복된다.',
        fix='장면 요소만 다른 동일 조건의 대조군을 유일하게 선택하고, 기체·PRF·로터 설정·자세 수를 쌍으로 검사한다. 중복 후보는 거절하고 선택 근거를 남긴 뒤 장면 표를 재발간한다. 스위치 이름도 실제 옵션과 맞춘다.',
        sources=sources,result_key='additional.late_scene'))
    return findings

if __name__=='__main__':
    if '--late-scene' in sys.argv:
        c=json.loads(CACHE.read_text());c['additional']['late_scene']=late_scene_check();c['source_hashes'].update(base.HASHES)
        CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n');publish(c)
    elif '--report' in sys.argv:publish(json.loads(CACHE.read_text()))
    else:
        scan();additional_checks(json.loads(CACHE.read_text()));final_probes(json.loads(CACHE.read_text()));scope_summaries(json.loads(CACHE.read_text()))
        c=json.loads(CACHE.read_text());c['additional']['other_arrays']=other_arrays();c['additional']['late_scene']=late_scene_check();publish(c)
