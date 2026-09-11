"""Repository-wide inventory plus targeted production-path audit.
Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_repository_0911.py
CPU only. Existing publications and running workers are not modified.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast,collections,contextlib,hashlib,importlib,io,json,math,re,subprocess,sys,tempfile,time,types,warnings,zipfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import review_current_state_0911 as base
import review_extended_0911 as previous
ROOT=base.ROOT
OUT=ROOT/'outputs/repository_review_0911.json'
MD=ROOT/'docs/REPOSITORY_REVIEW_0911.md'
NB=MD.with_suffix('.ipynb')


def walk_files():
    """Enumerate working-tree files without depending on an external binary.

    The earlier version shelled out to `rg`. That binary is not on PATH on this host
    (the only copies live inside a VS Code extension directory), so the builder died
    with FileNotFoundError before writing anything. House rule: do not pin a path that
    can disappear. This walk applies the same two exclusions rg was given.
    """
    out=[]
    for base_dir,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in ('.git','__pycache__')]
        for n in names:
            out.append(os.path.relpath(os.path.join(base_dir,n),ROOT))
    return out


def inventory():
    # Tracked files are added even when ignored; the walk covers untracked ones.
    tool='rg' if __import__('shutil').which('rg') else None
    if tool:
        listed=[p.decode() for p in subprocess.check_output([tool,'--files','--hidden','-0','-g','!.git','-g','!__pycache__'],cwd=ROOT).split(b'\0') if p]
        how='rg --files (repository ignore rules honoured)'
    else:
        listed=walk_files()
        how='os.walk (no ignore rules; .git and __pycache__ excluded)'
    tracked=[p.decode() for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if p]
    paths=sorted({p for p in listed+tracked if p and (ROOT/p).is_file()})
    roots=collections.Counter(p.split('/')[0] if '/' in p else '(root)' for p in paths)
    source=[];syntax=[];patterns=collections.defaultdict(list)
    for name in paths:
        if not name.endswith('.py'):continue
        p=ROOT/name
        try:
            text=p.read_text();source.append(dict(path=name,lines=len(text.splitlines()),sha256=hashlib.sha256(text.encode()).hexdigest()))
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');ast.parse(text)
        except Exception as e:syntax.append(dict(path=name,error=f'{type(e).__name__}: {e}'));continue
        for category,regex in [('array_save',r'np\.savez'),('json_save',r'json\.dump'),('exists_skip',r'os\.path\.exists'),('nan_fill',r'nan_to_num'),('silent_exception',r'except Exception')]:
            if re.search(regex,text):patterns[category].append(name)
    ledgers=[];badjson=[]
    for p in sorted((ROOT/'outputs').glob('*.json')):
        if p==OUT:continue
        try:
            anomalies=[]
            def constant(s):anomalies.append(s);return None
            j=json.loads(p.read_text(),parse_constant=constant)
            meta=j.get('_meta',{}) if isinstance(j,dict) else {}
            ledgers.append(dict(path=str(p.relative_to(ROOT)),generator=meta.get('generator'),nonstandard_constants=len(anomalies)))
        except Exception as e:badjson.append(dict(path=str(p.relative_to(ROOT)),error=repr(e)))
    return dict(scope='Tracked files plus working-tree files. Enumeration used '+how+'. Ignore rules differ between the two, so file_count is not comparable across runs that used different enumerators.',enumerator=how,
        file_count=len(paths),root_counts=dict(roots),python_files=source,syntax_errors=syntax,static_candidate_files=dict(patterns),
        root_output_ledgers=ledgers,json_parse_errors=badjson)


def shards():
    groups={};errors=[];recent=[];manifest=[];cutoff=time.time()-120
    files=sorted(base.SHD.glob('*.npz'))
    for count,p in enumerate(files):
        st=p.stat()
        if st.st_mtime>cutoff:recent.append(p.name);continue
        match=re.match(r'^(.*)_el([+-]\d+(?:\.\d+)?)_\d+\.npz$',p.name)
        if not match:continue
        key=(match[1],float(match[2]));g=groups.setdefault(key,dict(files=[],idx=[],expected=set(),prfs=set(),zero=0,nonfinite=0,shape_errors=[],meta_els=set()))
        try:
            with np.load(p,allow_pickle=False) as z:
                idx=np.asarray(z['idx']);E=np.asarray(z['E']);meta=np.asarray(z['meta']).ravel() if 'meta' in z else np.array([])
                n=int(meta[3]) if meta.size>3 else None;prf=float(meta[4]) if meta.size>4 else None
                shape=[]
                for k in ['E','npaths','nret','n_dup']:
                    if k in z and (z[k].ndim!=1 or z[k].size!=idx.size):shape.append(k)
                if idx.ndim!=1:shape.append('idx')
                g['idx'].append(idx.ravel());g['files'].append(p.name);g['expected'].add(n);g['prfs'].add(prf)
                if meta.size:g['meta_els'].add(float(meta[0]))
                g['zero']+=int((E==0).sum());g['nonfinite']+=int((~np.isfinite(E)).sum())
                if shape:g['shape_errors'].append(dict(file=p.name,fields=shape))
                manifest.append(dict(file=p.name,size=st.st_size,mtime_ns=st.st_mtime_ns,n_rows=idx.size,declared_n=n,prf=prf,keys=z.files))
        except Exception as e:errors.append(dict(file=p.name,error=repr(e)))
        if count and count%2000==0:print(f'shard inventory {count}/{len(files)}',flush=True)
    rows=[]
    for (eng,el),g in sorted(groups.items()):
        if not g['idx']:continue
        idx=np.concatenate(g.pop('idx'));unique=np.unique(idx);n=next(iter(g['expected'])) if len(g['expected'])==1 else None
        complete=n is not None and np.array_equal(unique,np.arange(n))
        rows.append(dict(engine=eng,el_deg=el,files=g['files'],n_rows=int(idx.size),n_unique=int(unique.size),declared_n=sorted(g['expected'],key=str),
            prfs=sorted(g['prfs'],key=str),duplicate_rows=int(idx.size-unique.size),index_covers_declared=complete,
            nonfinite=g['nonfinite'],stored_zero_samples=g['zero'],shape_errors=g['shape_errors'],meta_els=sorted(g['meta_els']),
            metadata_consistent=len(g['expected'])==1 and len(g['prfs'])==1 and None not in g['expected'] and None not in g['prfs']))
    ledger=base.js('outputs/elevation_sweep_md.json');pub={(r['engine'],r['el_deg']):r for r in ledger['rows']}
    overlaps=[];zero_full=[]
    for r in rows:
        hit=pub.get((r['engine'],r['el_deg']))
        if hit:r['published']=dict(n_poses=hit['n_poses'],n_missing=hit['n_missing'],level_db=hit['level_db'])
        if r['duplicate_rows']:overlaps.append(r)
        if r['index_covers_declared'] and not r['duplicate_rows'] and r['stored_zero_samples']:zero_full.append(r)
    return dict(files_discovered=len(files),files_read=len(manifest),recent_skipped=recent,errors=errors,groups=rows,manifest=manifest,
        duplicate_groups=overlaps,complete_groups_with_zero=zero_full,n_incomplete_groups=sum(not r['index_covers_declared'] for r in rows),
        n_metadata_inconsistent=sum(not r['metadata_consistent'] for r in rows),n_nonfinite_groups=sum(bool(r['nonfinite']) for r in rows),
        n_shape_error_groups=sum(bool(r['shape_errors']) for r in rows))


def raw_merge(files):
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'));code=None
    for loop in ast.walk(tree):
        if not isinstance(loop,ast.For):continue
        start=next((i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Tuple)
            and [getattr(t,'id','') for t in n.targets[0].elts][:2]==['n_tr','n_seen']),None)
        if start is None:continue
        end=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='miss')
        code=loop.body[start:end+1]
    assert code is not None
    ns=dict(np=np,os=os,fs=files,E=None,secs=0.,npa=[],cfg=None)
    exec(compile(ast.Module(body=code,type_ignores=[]),'production merge block','exec'),ns)
    return ns


def zero_and_overlap(s):
    zrows=[];over=[];atlas=base.js('outputs/md_atlas_index.json');ac={}
    for topic in atlas['topics'].values():
        for arm,info in topic['arms'].items():
            for el,row in info['cells'].items():ac[(arm,float(row['el_deg']))]=row
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'))
    level=next(k.value for n in ast.walk(tree) if isinstance(n,ast.Call) for k in n.keywords if k.arg=='level_db')
    for r in s['complete_groups_with_zero']:
        fs=[base.digest(base.SHD/f) for f in r['files']];ns=raw_merge(fs);E=ns['E'];m=ns['miss']
        # The production level expression grew a `seen` mask on 2026-09-11 (stored zero
        # fields are data, not gaps). Evaluate it in the merge block's own namespace so
        # this probe keeps tracking production instead of a frozen copy of its variables.
        current=eval(compile(ast.Expression(level),'production level_db','eval'),dict(ns,np=np,E=E,miss=m))
        ordinary=round(float(20*np.log10(np.abs(E).mean()+1e-300)),2)
        a=ac.get((r['engine'],r['el_deg']))
        zero_paths=[]
        for f in fs:
            with np.load(f) as z:
                if 'npaths' in z:zero_paths.append(int(((z['E']==0)&(z['npaths']==0)).sum()))
        zrows.append(dict(engine=r['engine'],el=r['el_deg'],files=r['files'],n=len(E),stored_zero=r['stored_zero_samples'],
            actual_missing_indices=len(E)-r['n_unique'],reported_missing=m,published=r.get('published'),
            current_level_db=current,mean_including_stored_zero_db=ordinary,conditional_mean_difference_db=(round(float(20*np.log10(np.abs(E[E!=0]).mean()/np.abs(E).mean())),2) if (E!=0).any() else 0.),
            n_zero_with_zero_kept_paths=sum(zero_paths) if zero_paths else None,
            atlas=dict(incomplete=a.get('incomplete'),no_return=a.get('no_return')) if a else None))
    for r in s['duplicate_groups']:
        files=[base.digest(base.SHD/f) for f in r['files']];ns=raw_merge(files);seen={};diff=0;coh=collections.defaultdict(list)
        for f in files:
            with np.load(f) as z:
                coh[int(z['meta'][2])].append(dict(file=f.name,n_rows=len(z['idx']),idx=z['idx'].tolist()))
                for i,e in zip(z['idx'],z['E']):
                    if int(i) in seen:diff+=int(e!=seen[int(i)])
                    seen[int(i)]=e
        reverse=raw_merge(files[::-1]);complete=[]
        for n,vals in coh.items():
            ii=np.concatenate([v['idx'] for v in vals]);complete.append(dict(nshards=n,files=[v['file'] for v in vals],
                complete=bool(np.array_equal(np.sort(ii),np.arange(len(ns['E']))))))
        over.append(dict(engine=r['engine'],el=r['el_deg'],files=r['files'],n_rows=r['n_rows'],n_unique=r['n_unique'],
            n_conflicting_overlap=diff,n_changed_by_file_order=int((ns['E']!=reverse['E']).sum()),reported_missing=ns['miss'],
            diagnostic_rows=ns['n_seen'],cohorts=complete,published=r.get('published')))
    return dict(zero=zrows,overlap=over,partial_zero=[r for r in zrows if 0<r['stored_zero']<r['n']],
        conflicting=[r for r in over if r['n_conflicting_overlap']])


def save_interruption():
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'))
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and n.func.attr=='savez_compressed' and any(k.arg=='nret' for k in n.keywords))
    # The resume gate moved from `os.path.exists(f)` to `shard_done(f)` on 2026-09-11.
    # Accept either shape so this probe keeps measuring the production condition instead
    # of failing with StopIteration when the condition is repaired.
    gate=next(n.test for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp)
        and ('os.path.exists(f)' in ast.unparse(n.test) or 'shard_done(f)' in ast.unparse(n.test))
        and 'a.overwrite' in ast.unparse(n.test))
    gate_src=ast.unparse(gate)
    # Any helper the gate calls is taken from production source, never reimplemented here.
    helpers=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name+'(' in gate_src]
    with tempfile.TemporaryDirectory() as td:
        target=Path(td)/'probe.npz';N=8
        ns=dict(np=np,f=str(target),idx=np.arange(N),E=np.ones(N,complex),npaths=np.ones(N),nret=np.ones(N),E_dedup=np.ones(N,complex),n_dup=np.zeros(N),
            _ntr=0,RP=types.SimpleNamespace(MAX_PATHS=2000000),a=types.SimpleNamespace(shard=0,nshards=1,physics=False,det=False,overwrite=False),
            el=0,n=N,prf=19700,time=time,t0=time.time(),spp=4000000000,rng_m=15,mdep=2,sw=dict(refraction=False,diffraction=False,edge_diffraction=False),os=os)
        real=np.lib.format.write_array;count=[0]
        def interrupted(*args,**kw):
            count[0]+=1
            if count[0]==2:raise OSError('synthetic interruption while saving E')
            return real(*args,**kw)
        try:
            np.lib.format.write_array=interrupted
            try:exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.Expr(value=call)],type_ignores=[])),'production save call','exec'),ns)
            except Exception as e:failure=type(e).__name__
        finally:np.lib.format.write_array=real
        assert failure=='OSError',failure
        try:
            with np.load(target) as z:arr=z['E']
            readable=isinstance(arr,np.ndarray) and arr.shape==(N,) and np.isfinite(arr).all()
            error=None if readable else 'Invalid E payload: '+type(arr).__name__
        except Exception as e:readable=False;error=type(e).__name__
        for h in helpers:
            exec(compile(ast.fix_missing_locations(ast.Module(body=[h],type_ignores=[])),'production gate helper','exec'),ns)
        return dict(injected_exception=failure,file_left=target.exists(),E_valid=bool(readable),read_error=error,
            resume_gate_source=gate_src,resume_gate_helpers=[h.name for h in helpers],
            production_resume_would_skip=bool(eval(compile(ast.Expression(gate),'production resume gate','eval'),ns)),
            scope='Production save call and resume condition only; no solver runs or live worker interruption.')


def dsp_checks():
    sys.path.insert(0,str(ROOT/'src'))
    # Importing these modules has no solver/GPU execution.
    pp=importlib.import_module('passive_process');mp=importlib.import_module('microdoppler_proc')
    for f in ['src/passive_process.py','src/microdoppler_proc.py','outputs/verify_cfar.json']:base.digest(f)
    calibration=[]
    with contextlib.redirect_stdout(io.StringIO()):
        for name in ['wifi','lte','nr']:
            tab=pp.PFA_CALIBRATION.get(name);lo,hi=min(tab),max(tab)
            values=[lo/10,lo,hi,hi*10]
            # The API now refuses uncalibrated targets (2026-09-11). Probing out-of-range
            # values is the point of this check, so record the refusal as the expected
            # outcome instead of letting it abort the whole audit. Also record what the
            # unchecked path would have returned, so the saturation stays visible.
            def _probe(std,x):
                d=pp.pfa_nominal_detail(std,x)
                try:
                    return dict(target=x,nominal=pp.pfa_nominal_for(std,x),refused=False,
                        source=d['source'],calibrated=d['calibrated'])
                except pp.PfaOutOfRange as e:
                    return dict(target=x,nominal=None,refused=True,source=d['source'],
                        calibrated=d['calibrated'],would_have_returned=d['nominal'],
                        error=type(e).__name__)
            calibration.append(dict(waveform=name,calibration_min=lo,calibration_max=hi,
                calls=[_probe(name,x) for x in values]))
    periods=[]
    for N in [512,8192]:
        f,t,S,info=mp.periodogram_spec(np.ones(N,complex),19700.,126.7,min_periods=8)
        periods.append(dict(N=N,prf_hz=19700.,f_flash_hz=126.7,requested_min_periods=8,info=info))
    return dict(pfa=calibration,periodogram=periods)


def verify_previous():
    p=previous.prior
    with contextlib.redirect_stdout(io.StringIO()):h=p.harness_checks()
    actual=previous.production_merge([[base.SHD/f for f in sorted(x.name for x in base.SHD.glob('*n8192_envoutdoor01_S0.3_mfixbatteryi5_blperairframe_d2_el-30_*.npz'))]])[0]
    assert sum(actual['by'].values())==actual['n_seen']==8192
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);kw=dict(idx=np.arange(4),E=np.ones(4,complex),meta=[0,0,1,4,19700,0],nret=np.full(4,1999980))
        one=td/'one.npz';two=td/'two.npz';six=td/'six.npz'
        np.savez(one,**kw,n_trunc=[0]);np.savez(two,**kw,n_trunc=[0,2000000]);np.savez(six,**kw,n_trunc=[0,6000000])
        first=previous.production_merge([[one]])[0]
        after_two=previous.production_merge([[two],[one,two]])[-1]
        after_six=previous.production_merge([[six],[one,two]])[-1]
        assert after_two==after_six
        cap_order=dict(first=first,after_two=after_two,after_six=after_six)
    # New loader rejects the previously accepted pairs; output is isolated for each case.
    loader=importlib.import_module('read_0918B_0909');body=importlib.import_module('read_bodyladder_0910')
    old=(loader.SHD,body.OUT,body.LADDER,body.GRID);checks=[]
    try:
        with tempfile.TemporaryDirectory() as td:
            loader.SHD=td;body.LADDER=[(1.,'')];body.GRID=[]
            for case in ['valid','duplicate','prf','half','nan']:
                body.OUT=str(Path(td)/(case+'.json'));N=4096 if case=='half' else 8192
                for scene in [False,True]:
                    for sh in range(2):
                        idx=np.arange(0,N,2) if case=='duplicate' and scene else np.arange(sh,N,2)
                        E=np.full(len(idx),2.+0j if scene else 1.+0j)
                        if scene:E[idx==100]=4.
                        if case=='nan' and scene and sh==0:E[0]=np.nan
                        meta=[-60,sh,2,8192,10000 if case=='prf' and scene else 19700,0]
                        np.savez(Path(td)/f'{loader.stem(env="outdoor01_ground" if scene else "")}_el-60_{sh:02d}.npz',idx=idx,E=E,meta=meta,npaths=np.ones(len(idx)),n_dup=np.zeros(len(idx)))
                with contextlib.redirect_stdout(io.StringIO()):rc=body.main()
                checks.append(dict(case=case,exit=rc,output_created=Path(body.OUT).exists()))
        assert checks[0]['exit']==0 and all(x['exit']!=0 for x in checks[1:])
    finally:loader.SHD,body.OUT,body.LADDER,body.GRID=old
    module=p.previous.old_module();builder={}
    with tempfile.TemporaryDirectory(prefix='.repository-review-',dir=ROOT/'work') as td:
        module.OUT=Path(td)/'out.json';module.MEMO=Path(td)/'out.md';module.NB=Path(td)/'out.ipynb'
        try:
            with contextlib.redirect_stdout(io.StringIO()):module.main()
            builder['completed']=True
        except Exception as e:builder.update(completed=False,error_type=type(e).__name__,error=str(e))
        builder.update(json_written=module.OUT.exists(),markdown_written=module.MEMO.exists(),notebook_written=module.NB.exists())
        if module.OUT.exists():
            r=json.loads(module.OUT.read_text());builder['atlas_mode']=r['checks']['atlas']['mode']
            builder['current_replacement']=r['findings'][0]['replacement']
        for f in module.HASHES:
            if not f.startswith('git:'):base.digest(f)
    return dict(harness=h,merge=actual,cap_order=cap_order,body_inputs=checks,builder=builder,
        body_rename_remaining='expected_jaccard_if_unrelated' in base.read('benchmark/read_bodyladder_0910.py'),
        canyon_renamed='approx_jaccard_if_unrelated' in base.read('benchmark/read_canyonnull_0910.py'))


def generation_selection(agg):
    """Measure the production generation chooser on the conflicting cells.

    The merge loop itself still assigns with E[ii] = z["E"], so the loop alone remains
    order dependent. What removes the dependence is the file selection that runs before
    it. This probe loads the production function from source and checks two things:
    the same files are chosen when the input order is reversed, and the published ledger
    records what was dropped.
    """
    tree = ast.parse(base.read('benchmark/elevation_sweep_md.py'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'one_generation')
    ns = dict(np=np, os=os)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 'production generation chooser', 'exec'), ns)
    choose = ns['one_generation']
    ledger = base.js('outputs/elevation_sweep_md.json')
    pub = {(r['engine'], r['el_deg']): r for r in ledger['rows']}
    rows = []
    for r in agg['conflicting']:
        fs = [str(base.SHD / f) for f in r['files']]
        with contextlib.redirect_stdout(io.StringIO()):
            keep_a, note_a = choose(sorted(fs), 'forward')
            keep_b, _ = choose(sorted(fs, reverse=True), 'reverse')
        hit = pub.get((r['engine'], r['el'])) or {}
        rows.append(dict(engine=r['engine'], el_deg=r['el'],
            n_changed_by_file_order_in_loop=r['n_changed_by_file_order'],
            chosen=[os.path.basename(x) for x in keep_a],
            same_under_reversed_input=sorted(keep_a) == sorted(keep_b),
            kept_poses=note_a['kept_poses'], n_poses=note_a['n_poses'],
            dropped_files=note_a['dropped_files'],
            n_poses_differing=note_a['n_poses_differing'],
            n_poses_rel_diff_over_5e_6=note_a['n_poses_rel_diff_over_5e_6'],
            rel_diff_max=note_a['rel_diff_max'],
            ledger_records_choice=bool(hit.get('mixed_generations')),
            published_level_db=hit.get('level_db')))
    return dict(cells=rows, scope='Production chooser run on the conflicting cells only; '
        'shards on disk are not modified and no solver runs.',
        all_order_independent=all(x['same_under_reversed_input'] for x in rows),
        all_recorded=all(x['ledger_records_choice'] for x in rows))


def findings(c):
    fs=[]
    def add(title,kind,evidence,fix,refs):fs.append(dict(title=title,kind=kind,evidence=evidence,fix=fix,sources=[base.source(*r) for r in refs]))
    a=c['aggregation'];z=max(a['partial_zero'],key=lambda r:r['conditional_mean_difference_db']);s=c['shards'];v=c['previous'];d=c['dsp']
    agree=[r for r in a['partial_zero'] if r['published']['level_db']==r['mean_including_stored_zero_db'] and r['reported_missing']==r['actual_missing_indices']]
    atlas_flag=sorted({bool(r['atlas']['incomplete']) for r in a['partial_zero']})
    add('수집 마스크로 결측을 가르고 저장된 영 전계를 평균에 포함한다','2026-09-11 정정(R31) 뒤 현재 상태',
        f"인덱스가 완결된 {len(a['zero'])}칸에 영 전계가 있고, 그중 일부 표본만 영인 칸은 {len(a['partial_zero'])}개다. "
        f"이 {len(a['partial_zero'])}칸 모두에서 발간 level_db가 영 표본을 포함한 평균과 같고 n_missing이 실제 빠진 인덱스 수와 같다(일치 {len(agree)}칸). "
        f"예: {z['engine']}, el {z['el']:g}°, 저장 {z['n']}표본 중 영 전계 {z['stored_zero']}개, 실제 빠진 인덱스 {z['actual_missing_indices']}개, n_missing={z['reported_missing']}, 발간 레벨 {z['published']['level_db']} dB다. "
        f"옛 규칙(영 표본 제외)과의 차이는 이 칸에서 {z['conditional_mean_difference_db']} dB였다. "
        f"저장된 영 값은 물리적으로 신호가 없다는 증명도 아니며 표본을 저장하지 않았다는 증명도 아니므로, 두 수를 따로 싣는다. "
        f"같은 칸들의 아틀라스 incomplete 값은 {atlas_flag}이며, 이 값은 아틀라스를 다시 구운 뒤에 의미가 있다.",
        '남은 일은 아틀라스 색인을 정정된 원장으로 다시 굽고 incomplete와 zero_field가 갈라져 실리는지 확인하는 것이다. 원장 쪽 규칙은 idx 기반 수집 마스크로 고정됐다.',
        [('benchmark/elevation_sweep_md.py','miss = int((~seen).sum())'),('benchmark/elevation_sweep_md.py','(np.abs(E[seen]).mean() if seen.any()'),('benchmark/build_md_atlas.py','incomplete = (not empty) and')])
    conflict=a['conflicting']
    g=c['generation'];cover=[str(x['kept_poses'])+'/'+str(x['n_poses']) for x in g['cells']]
    add('한 칸에 두 세대가 있으면 한 세대를 골라 파일 순서에서 결과를 떼어 놓는다','2026-09-11 정정(R32) 뒤 현재 상태',
        f"중복 인덱스가 있는 {len(a['overlap'])}칸 중 {len(conflict)}칸은 겹친 전계가 달랐고, 나머지 {len(a['overlap'])-len(conflict)}칸은 겹친 값이 같았다. "
        f"병합 고리만 놓고 보면 이 {len(conflict)}칸은 파일 순서를 뒤집을 때 {[r['n_changed_by_file_order'] for r in conflict]}개의 자세가 바뀐다. "
        f"고리 앞에서 세대를 고르는 생산 함수를 정·역 두 순서로 돌린 결과 선택이 같은 칸은 {sum(x['same_under_reversed_input'] for x in g['cells'])}/{len(g['cells'])}이고, "
        f"고른 세대가 덮는 자세는 {cover}다. "
        f"무엇을 버렸는지 원장 행이 적은 칸은 {sum(x['ledger_records_choice'] for x in g['cells'])}/{len(g['cells'])}다. "
        f"겹친 자세 중 값이 다른 수는 {[x['n_poses_differing'] for x in g['cells']]}이고 그중 상대차 5e-6을 넘는 수는 {[x['n_poses_rel_diff_over_5e_6'] for x in g['cells']]}, 최대 상대차는 {[round(x['rel_diff_max'],4) for x in g['cells']]}다. "
        f"충돌한 조건 중 현재 발간 주 원장에 들어 있는 수는 {sum(r['published'] is not None for r in conflict)}칸이다.",
        '남은 일은 겹친 파일을 창고에서 정리할지 그대로 둘지 정하는 것이다. 선택 규칙은 최신 파일 우선이 아니라 자세를 가장 많이 덮는 세대이며, 고른 세대가 부분 자료면 그 칸은 미완으로 남는다.',
        [('benchmark/elevation_sweep_md.py','def one_generation('),('benchmark/elevation_sweep_md.py','fs, mixed_gen = one_generation('),('benchmark/elevation_sweep_md.py','E[ii] = z["E"]')])
    q=c['save']
    add('재개가 파일 이름 대신 내용으로 완료를 판정한다','2026-09-11 정정 뒤 현재 상태 · 합성 장애 시험',
        f"실제 저장 호출에서 E를 쓰는 중 예외를 주입했다. 파일 잔존={q['file_left']}, E 배열 유효={q['E_valid']}, "
        f"재개 조건 원문은 «{q['resume_gate_source']}»이고 그 조건이 이 파일을 건너뛸지는 {q['production_resume_would_skip']}다. "
        f"조건이 부르는 생산 함수 {q['resume_gate_helpers']}를 원본 그대로 실행해 판정했다. "
        f"이번 전수 판독 {s['files_read']}개에서 읽기 실패는 {len(s['errors'])}개이므로, 현재 재고가 손상됐다는 주장이 아니라 저장 중단에 대한 내성을 잰 것이다.",
        '남은 일은 저장 자체를 같은 디렉토리의 임시 파일에 쓰고 최종 이름으로 교체하는 것이다. 지금은 재개 쪽만 내용을 확인하므로, 끊긴 파일은 남아 있다가 다시 구워질 때 덮인다.',
        [('benchmark/elevation_sweep_md.py','np.savez_compressed(f, idx=idx, E=E, npaths=npaths, nret=nret,'),('benchmark/elevation_sweep_md.py','def shard_done('),('benchmark/elevation_sweep_md.py','if shard_done(f) and not a.overwrite:')])
    b=v['builder']
    add('검토 빌더가 형식 관문까지 통과해 끝난다','2026-09-11 정정 뒤 현재 상태',
        f"직전 라운드 빌더의 main을 임시 출력 경로에서 실행하면 완료={b['completed']}, 오류 종류={b.get('error_type')}로 끝난다. "
        f"JSON 작성={b['json_written']}, 마크다운 작성={b['markdown_written']}, 노트북 작성={b['notebook_written']}다. "
        f"아틀라스 점검 방식은 {b['atlas_mode']}이고 첫 소견의 처방줄은 «{b['current_replacement'][:60]}…»로 끝난다. "
        '전에는 내용 수정이 노트북의 부정문 개수 제한을 넘겨 strict 관문이 거절했다. 원장 계산 성공과 보고서 생성 완료는 여전히 따로 센다. 실행 전문은 checks.previous.builder에 보존했다.',
        '남은 일은 산출물 묶음을 검사까지 통과한 뒤 공개하는 순서를 지키는 것이다. 관문을 통과하려면 처방줄을 긍정형의 구체적인 상태 설명으로 쓴다.',
        [('benchmark/review_latest_readers_0910.py','build_notebook(str(NB),blocks,strict=True)'),('src/report_style.py','raise ContractError(')])
    p=d['pfa'][0]
    _ref=[c for c in p['calls'] if c['refused']];_ok=[c for c in p['calls'] if not c['refused']]
    add('교정 범위 밖 목표 오경보율을 거절하고 범위 안에서만 교정값을 준다','2026-09-11 정정 뒤 현재 상태',
        f"{p['waveform']} 교정 범위 {p['calibration_min']}~{p['calibration_max']}에서 네 값을 넣었다. "
        f"범위 밖 {len(_ref)}개는 거절됐고({[c['target'] for c in _ref]}), 범위 안 {len(_ok)}개는 교정값을 돌려줬다. "
        f"거절된 값이 옛 동작에서 돌려줬을 수는 {[c['would_have_returned'] for c in _ref]}인데, 이는 경계값이지 그 목표의 값이 아니다. "
        '옛 코드는 np.interp가 구간 밖에서 외삽한다고 주석에 적었으나 실제로는 끝점에 붙는다. 세 파형 모두 같다. 범위 밖 설정으로 생성된 발간 결과를 특정한 것은 아니다.',
        '남은 일은 표를 넓혀 더 엄격한 목표까지 교정하는 것이다. 그전까지 범위 밖이 필요하면 strict=False로 부르고 pfa_nominal_detail의 source를 결과에 함께 적는다.',
        [('src/passive_process.py','def pfa_nominal_detail('),('src/passive_process.py','raise PfaOutOfRange('),('src/passive_process.py','val = float(10 ** np.interp(np.log10(pfa_target), lx, ly))')])
    add('두 판독 빌더가 근사 자카드를 근사라고 이름 붙인다','2026-09-11 정정 뒤 현재 상태',
        f"협곡의 approx_jaccard 명칭 반영={v['canyon_renamed']}이고, 동체 생산 빌더에 남아 있던 expected_jaccard 명칭 잔존={v['body_rename_remaining']}다. "
        '두 빌더 모두 기대 교집합을 비율식에 넣은 값을 근사로 이름 붙이므로, 정확한 기대 자카드와 이름이 갈린다. 이전 감사의 수치적 차이 설명은 그대로 유지한다.',
        '남은 일은 옛 키를 읽던 소비자가 있으면 함께 갱신하는 것이다. 두 원장은 새 이름으로 다시 구웠다.',
        [('benchmark/read_bodyladder_0910.py','approx_jaccard_if_unrelated'),('benchmark/read_canyonnull_0910.py','approx_jaccard_if_unrelated')])
    assert all(s['found'] for f in fs for s in f['sources'])
    return fs


def render(o):
    c=o['checks'];i=c['inventory'];s=c['shards'];p=c['publications'];j=str(OUT.relative_to(ROOT))
    lines=['# 시오나 저장소 전체 재고와 주요 실행 경로 점검','',f"기준 `{o['_meta']['head']}` · {o['_meta']['checked_at_utc']}",'',
        '[주피터 보고서](REPOSITORY_REVIEW_0911.ipynb) · [전수 목록·실행 원장](../outputs/repository_review_0911.json) · [재현 생성기](../benchmark/review_repository_0911.py)','',
        '## 조사 범위','',
        f"추적 파일과 작업 트리 파일 {i['file_count']}개를 목록화하고, 파이썬 {len(i['python_files'])}개를 구문 검사했다. 열거에 쓴 방법은 {i['enumerator']}다. "
        f"outputs 바로 아래 JSON {len(i['root_output_ledgers'])}개를 구문 확인했다. 저장 샤드 {s['files_read']}개를 실제로 읽어 {len(s['groups'])}조건의 idx·선언 길이·시간축·전계 유한값·배열 길이를 집계했다.",'',
        '파일 목록·구문 검사는 모든 코드의 의미를 정독하거나 모든 실험을 재실행한 것과 다르다. 의미와 반례를 깊게 확인한 범위는 '
        '주 병합·샤드 저장·재개 조건·협곡/낙차/동체 판독·아틀라스 완전성·검토 보고서 빌더·신호처리 교정이다. '
        'refs·prior_work의 논문 근거 재독, GPU 커널 재실행, 모든 보고서의 과학적 결론 검증은 이번 범위 밖이다. '
        '저장소 무시 규칙에 걸리는 미추적 파일은 일반 목록 밖이며 샤드 폴더는 별도로 직접 열거했다.','',
        f"샤드 읽기 오류 {len(s['errors'])}개·비유한 전계 조건 {s['n_nonfinite_groups']}개·배열 길이 오류 조건 {s['n_shape_error_groups']}개다. "
        f"인덱스가 선언 길이를 덮지 않는 조건은 {s['n_incomplete_groups']}개로, 진행 중 자료와 구별해 다뤄야 한다. "
        '완전성 부족을 곧바로 솔버 결함으로 부르지 않는다.','',
        '## 이전 지적의 현재 상태','',
        '- 보류 진단의 분류 합계와 초기화 전 상한 사용은 지정 반례에서 수정됐다. 함수 범위를 유지한 실행으로 확인했다.',
        '- 동체 입력의 NaN·중복·시간축 불일치·절반 자료는 생산 main에서 거절됐다. 회귀 검사의 일부 오집계·행 누락도 정상적으로 구분됐다.',
        '- 보고서 수정은 노트북 형식 관문 실패로 이어졌고, 자카드 근사 명칭은 동체 빌더에 남았다. 아래에 구체적으로 적었다.',
        f"- 기존 발간 대조는 원본 {p['union_shards']}개·협곡 {p['canyon_drop']['n_canyon_cells']}칸·낙차 {p['canyon_drop']['n_drop_cells']}칸·동체 {p['body_cells']}칸이다. 이 범위의 관측 사건 수는 일치했다.",'',
        '## 재현한 보완점','']
    for n,f in enumerate(o['findings']):
        lines += [f"### {n+1}. {f['title']}",'',f"**범위:** {f['kind']}",'',f['evidence'],'','**수정 방향:** '+f['fix'],'',f"⟨{j} : findings[{n}]⟩",'']
        for q in f['sources']:lines += [f"- [{Path(q['path']).name}:{q['line']}](../{q['path']}#L{q['line']})",'```python',q['quote'],'```','']
    per=c['dsp']['periodogram'][0]
    lines += ['## 추가 관찰과 미확정 범위','',
        f"microdoppler_proc.periodogram_spec는 min_periods={per['requested_min_periods']} 요청을 입력 길이 제한으로 줄인다. "
        f"N={per['N']}·PRF={per['prf_hz']}·f_flash={per['f_flash_hz']}에서 실제 seg_periods={per['info']['seg_periods']:.4f}다. "
        '정보에는 실제 주기가 기록되지만 함수 설명의 최소 주기 보장은 성립하지 않는다. 짧은 입력을 거절할지 요청 미충족 상태로 내보낼지 정해야 한다. '
        '외부 호출 경로의 발간 영향을 이번에 특정하지 못했으므로 주요 결함 수에는 넣지 않았다.','',
        '구문 검사에서 outputs의 코드 발췌 파일이 들여쓰기로 걸렸다. 실행 엔트리의 오류로 분류하지 않았다. '
        '정적 패턴 후보는 checks.inventory.static_candidate_files에 목록으로 보존했고, 자동 검색 결과만으로 결함 판정을 내리지 않았다.','',
        '운영 코드·기존 원장·GPU 큐를 변경하지 않았다. 저장 장애는 임시 파일에만 주입했다. '
        '권장 순서는 수집 마스크 정의와 혼합 세대 선택을 정한 뒤 병합·아틀라스 정정 범위를 계산하고, 저장/재개 및 보고서 생성 경로를 보강하는 것이다.','',
        '```bash',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_repository_0911.py",'```','']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='저장소 점검',title='전체 재고와 주요 병합·판독·저장 경로',did='파일 재고를 전수 확인하고 주요 경로를 실제 자료와 반례로 대조했다.',
        results=[f"저장 샤드 {s['files_read']}개를 읽었다 ⟨{j} : checks.shards⟩.",f"파이썬 {len(i['python_files'])}개를 구문 검사했다 ⟨{j} : checks.inventory⟩.",
                 f"재현한 보완점 {len(o['findings'])}건의 영향 범위를 기록했다 ⟨{j} : findings⟩."],
        method=[('전체 재고','파일·구문·샤드 구조를 열거하고 검사'),('주요 경로','현재 생산 코드의 집계·저장·판독과 보고서 생성을 실행')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_repository_0911.py"],out=[j],runtime='CPU 한 코어, 원본 샤드 전수 판독'))]
    for n,f in enumerate(o['findings']):blocks.append(md(f"## {n+1}. {f['title']}",'',f['fix'],'',f"[원본·수치·범위](REPOSITORY_REVIEW_0911.md) ⟨{j} : findings[{n}]⟩"))
    blocks.append(next_steps([('수집 마스크와 세대 선택을 명시한다','영 전계의 결측 오분류와 혼합 병합','REPOSITORY_REVIEW_0911.md'),('저장·재개와 발간 빌드를 보강한다','불완전 산출물의 재사용과 보고서 생성 실패','REPOSITORY_REVIEW_0911.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    for p in [__file__,'benchmark/review_extended_0911.py','benchmark/review_postfix_0911.py','benchmark/review_current_state_0911.py','benchmark/review_fix_verification_0911.py']:base.digest(p)
    c={}
    for name,fn in [('inventory',inventory),('shards',shards),('previous',verify_previous),('save',save_interruption),('dsp',dsp_checks),('publications',previous.actual_publications)]:
        c[name]=fn();print('completed '+name,flush=True)
    c['aggregation']=zero_and_overlap(c['shards'])
    c['generation']=generation_selection(c['aggregation']);print('completed generation',flush=True)
    fs=findings(c)
    o=dict(_meta=dict(generator='benchmark/review_repository_0911.py',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        checked_at_utc=datetime.now(timezone.utc).isoformat(),source_sha256=base.HASHES),checks=c,findings=fs)
    OUT.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n');render(o)
    print(json.dumps(dict(findings=len(fs),files=c['inventory']['file_count'],shards=c['shards']['files_read']),ensure_ascii=False))

if __name__=='__main__':main()
