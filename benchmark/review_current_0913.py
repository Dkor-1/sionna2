"""Read-only current audit. Run: python benchmark/review_current_0913.py
Production files and queues are read only; audit outputs are generated separately.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast, collections, contextlib, copy, io, json, re, subprocess, sys, tempfile, time, types
from pathlib import Path
import numpy as np
import review_full_0912 as old
base=old.base; repo=old.repo; ROOT=old.ROOT
OUT=ROOT/'outputs/current_review_0913.json'
MD=ROOT/'docs/CURRENT_REVIEW_0913.md'
NB=MD.with_suffix('.ipynb')
CACHE=ROOT/'work/current_review_0913_cache.json'

def save(c):
    CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')

def scope():
    c={'_meta':{'generator':'benchmark/review_current_0913.py','checked_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},'checks':{}}
    x=c['checks'];x['queue']=old.prev.queue()
    x['wide']=old.wide_artifact_check();print('wide',x['wide']['file_count'],flush=True)
    x['shards']=repo.shards();x['arrays']=old.full_arrays(x['shards']);print('arrays',x['arrays']['files'],flush=True)
    x['other_arrays']=old.other_arrays();print('other arrays',x['other_arrays']['n_files'],flush=True)
    save(c)
    x['boundaries']=old.boundary_checks();print('boundaries',flush=True)
    x['resume']=old.prev.resume_checks()
    try:x['generation']=old.prev.generation_checks(x['shards'])
    except Exception as e:x['generation']={'error':type(e).__name__,'message':str(e)}
    save(c)
    x['publications']=repo.previous.actual_publications();print('publications',flush=True)
    x['gates']=old.gates()
    p=subprocess.run([sys.executable,'benchmark/check_arm_names.py','--shards'],cwd=ROOT,text=True,capture_output=True,timeout=120)
    x['gates']['check_arm_names']={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    c['source_hashes']=dict(base.HASHES);save(c)
    print('scope saved',flush=True)



def numeric_checks():
    sys.path.insert(0,str(ROOT/'src'))
    import md_mapstyle as mp
    from arm_grammar import parse,unparse
    atlas=old.loadmod('benchmark/build_md_atlas.py')
    wf=old.loadmod('benchmark/read_wfsurvive_0912.py')
    band=old.loadmod('benchmark/read_bandflat_0913.py')
    led=base.js('outputs/elevation_sweep_md.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz',allow_pickle=False)
    meta=led['_meta'];default=float(meta['f_flash_hz'])
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'))
    ana=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='analyse')
    defs=[n for n in ana.body if isinstance(n,ast.FunctionDef) and n.name in ['_stft','band_metrics']]
    tipfn=base.funcs('benchmark/elevation_sweep_md.py',['f_tip_at','carrier_of'],dict(np=np,re=re,ROOT=str(ROOT),TJ=meta,FC=meta['fc_hz']))['f_tip_at']
    def track(E,r,ff):
        prf=r['prf_hz'];ns=dict(np=np,prf=prf,ffl=ff,per=mp.auto_periods(prf,ff),flash_spec=mp.flash_spec,auto_periods=mp.auto_periods,_stft_cache={})
        exec(compile(ast.Module(body=defs,type_ignores=[]),'production metrics','exec'),ns)
        ft=tipfn(r['el_deg'],r['engine'])
        return ns['band_metrics'](E,.35*ft,max(ft,1e-6),prf)
    drone=[];prf=[]
    for r in led['rows']:
        rates=atlas.arm_rates(r['engine']);ff=rates['f_flash_hz']
        varied=abs(ff-default)>1e-6
        if not varied and r.get('prf_hz')==meta['prf_hz']:continue
        E=np.asarray(Z[f"{r['engine']}/el{r['el_deg']:+g}"],complex)
        v=track(E,r,default)
        if r.get('prf_hz')!=meta['prf_hz']:prf.append({'engine':r['engine'],'el':r['el_deg'],'published':r['track'],'recomputed':v})
        if varied:
            after=track(E,r,ff)
            drone.append({'engine':r['engine'],'el':r['el_deg'],'drone':rates['drone'],'default_flash_hz':default,'correct_flash_hz':ff,'published':r['track'],'current':v,'with_drone_flash':after,'n_missing':r.get('n_missing')})
    ai=base.js('outputs/md_atlas_index.json');ac=[]
    for t in ai['topics'].values():
        for arm,r in t['arms'].items():
            rt=atlas.arm_rates(arm)
            for el,c in r['cells'].items():
                e=float(el);E=np.asarray(Z[f'{arm}/el{e:+g}'],complex);pr=atlas.prf_of(arm,e);ft=atlas.f_tip_at(rt,e)
                share,null,abv,deg=atlas.rhythm_share(E,rt['f_flash_hz'],ft,prf=pr)
                if c.get('rhythm_share_pct') is not None:
                    ac.append({'engine':arm,'el':e,'fc':rt['fc_hz'],'prf':pr,'published':c['rhythm_share_pct'],'recomputed':share,'delta':abs(c['rhythm_share_pct']-share) if share is not None else None})
    published=base.js('outputs/read_wfsurvive_0912.json');rates=wf.net_rates();waves=[]
    for r in published['rows']:
        E=np.asarray(Z[f"{r['engine']}/el{r['el_deg']:+g}"],complex)
        now=wf.survive(E,r['prf_hz'],rates,r['f_tip_hz']);rr=next(v for v in rates if v['std']=='wifi')
        x=E-E.mean();L=round(r['prf_hz']*rr['frame_ms']/1000);st=np.round(np.arange(0,len(x)-L,r['prf_hz']/rr['frame_rate_hz'])).astype(int)
        cs=np.r_[0j,np.cumsum(x)];y=(cs[st+L]-cs[st])/L
        independent=round(float(20*np.log10(np.std(y)/(np.std(x)+1e-300)+1e-300)),2)
        waves.append({'engine':r['engine'],'el':r['el_deg'],'matches':now['wifi']==r['wifi'],'independent_db':independent,'published_db':r['wifi']['rms_keep_db']})
    # Fix verification of the previous alias counterexample.
    fs=19700.;N=8192;f0=1550.;ft=1102.
    tone=wf.survive(np.exp(2j*np.pi*f0*np.arange(N)/fs),fs,[dict(std='nr',frame_rate_hz=2000.,frame_ms=.5)],ft)
    # New feature: an output band receives energy from outside the input band.
    fs=20000.;N=8000;tt=np.arange(N)/fs
    offband=[]
    for amp in [0.,.1,1.]:
        x=.01*np.exp(2j*np.pi*400*tt)+amp*np.exp(2j*np.pi*1600*tt)
        got=wf.survive(x,fs,[dict(std='nr',frame_rate_hz=2000.,frame_ms=.5)],400.)
        offband.append({'offband_amplitude':amp,'input_tip_amplitude':.01,'input_tip_hz':400.,'offband_hz':1600.,'output':got['nr']})
    # Band reader reports power summaries; phase rotations per carrier leave all of them invariant.
    bj=base.js('outputs/bandflat_0913.json');halves=[]
    for c in bj['cells']:
        E=np.asarray(Z[f"{c['engine']}/el{c['el_deg']:+g}"],complex)
        total=abs(np.subtract(*band.halves_level_db(E)))
        ac_half=abs(np.subtract(*band.halves_level_db(E-E.mean())))
        halves.append({'engine':c['engine'],'env':c['env'],'el':c['el_deg'],'fc':c['fc_mhz'],'published_half_db':c['half_spread_db'],'total_half_db':float(total),'ac_half_db':float(ac_half)})
    # No physical noise in this deterministic single line, but the structure gate rejects it.
    ffl=default;ft=1102.;fs=19700.;N=8192
    pure=np.exp(2j*np.pi*501.*np.arange(N)/fs)
    sh,nul,_,_=atlas.rhythm_share(pure,ffl,ft,prf=fs);cb=atlas.comb_contrast_db(pure,ffl,ft,prf=fs)
    has=bool(sh-nul>5. and cb>3.)
    # Boundary branch returns two values although production main unpacks three.
    ret=band.modspec_norm(pure,fs,ffl,0.)
    # The round-trip guarantee alone cannot validate field meaning for unknown envs.
    strange='sionna_p4000000000_swR0D0E0F1_r15_n8192_envnewcity_bldg'
    fields=parse(strange)
    return {'prf':{'rows':prf,'n':len(prf),'mismatch':sum(v['published']!=v['recomputed'] for v in prf)},
      'drone_flash':{'rows':drone,'n':len(drone),'current_mismatch':sum(v['published']!=v['current'] for v in drone),'changed':sum(v['current']!=v['with_drone_flash'] for v in drone)},
      'atlas':{'rows':ac,'n':len(ac),'mismatch_over_rounding':sum(v['delta'] is None or v['delta']>.051 for v in ac)},
      'wifi':{'rates':rates,'rows':waves,'mismatch':sum(not v['matches'] for v in waves),'independent_mismatch':sum(v['published_db']!=v['independent_db'] for v in waves)},
      'alias_fixed':{'input_hz':f0,'expected_hz':450.,'got':tone['nr']},'offband_survival':offband,
      'band_halves':halves,'structure_counterexample':{'n':N,'tone_hz':501.,'noise_power':0.,'rhythm_pct':sh,'rhythm_null_pct':nul,'comb_db':cb,'production_gate':has,'current_false_verdict':'움직이는 몫이 백색잡음 널과 구별되지 않는다'},
      'band_empty_return':{'arity':len(ret),'caller_expected':3},'grammar_unknown':{'name':strange,'fields':fields,'roundtrip_equal':unparse(fields)==strange}}

def probes():
    c=json.loads(CACHE.read_text());x=c['checks'];x['numeric']=numeric_checks();save(c)
    print(json.dumps({k:{a:v for a,v in d.items() if a not in ['rows']} if isinstance(d,dict) else {'n':len(d)} for k,d in x['numeric'].items()},ensure_ascii=False,indent=1),flush=True)

def reader_checks():
    from unittest.mock import patch
    band=old.loadmod('benchmark/read_bandflat_0913.py');wf=old.loadmod('benchmark/read_wfsurvive_0912.py');sc=old.loadmod('benchmark/read_scenephysics_0913.py');freeze=old.loadmod('benchmark/freeze_0912.py')
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation']
    result={'scene_reproduction':old.late_scene_check()}
    bd=base.js('outputs/bandflat_0913.json');ledger=base.js('outputs/elevation_sweep_md.json')
    real=np.load(ROOT/'outputs/elevation_sweep_md.npz',allow_pickle=False)
    data={f"{r['engine']}/el{r['el_deg']:+g}":np.asarray(real[f"{r['engine']}/el{r['el_deg']:+g}"],complex) for r in bd['cells']}
    runs={}
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for case in ['baseline','phase_rotated','nan_input']:
            arr={k:v.copy() for k,v in data.items()}
            if case=='phase_rotated':
                for c in bd['cells']:
                    k=f"{c['engine']}/el{c['el_deg']:+g}";arr[k]*=np.exp(1j*(c['fc_mhz']-3500)/25*1.1)
            if case=='nan_input':arr[next(iter(arr))][123]=complex(float('nan'),0)
            inp=td/'input.npz';out=td/'output.json';doc=td/'output.md';np.savez(inp,**arr)
            try:
                with patch.object(band,'LED_N',str(inp)),patch.object(band,'OUT_J',str(out)),patch.object(band,'OUT_MD',str(doc)),contextlib.redirect_stdout(io.StringIO()),np.errstate(all='ignore'):
                    rc=band.main()
                runs[case]={'exit':rc,'output':json.loads(out.read_text()),'error':None}
            except Exception as e:runs[case]={'error':type(e).__name__+': '+str(e)}
        a=freeze.scrape_numbers(runs['baseline']['output']);b=freeze.scrape_numbers(runs['phase_rotated']['output'])
        diffs=[{'key':k,'baseline':a.get(k),'rotated':b.get(k)} for k in set(a)|set(b) if a.get(k)!=b.get(k)]
        result['band_runs']={'baseline_error':runs['baseline']['error'],'phase_error':runs['phase_rotated']['error'],'phase_numeric_changes':diffs,'phase_step_rad':1.1,'phase_span_rad':4.4}
        for case in ['nan_input']:
            d=runs[case];num=freeze.scrape_numbers(d.get('output',{}));bad=[k for k,v in num.items() if isinstance(v,float) and not np.isfinite(v)]
            result['band_runs'][case]={'error':d['error'],'nonfinite_numeric_fields':bad,'n_cells':d.get('output',{}).get('_meta',{}).get('n_cells'),'skipped':d.get('output',{}).get('skipped')}
    # Input quality checks exercise both readers, including loss of generation diagnostics.
    rr=[]
    for case in ['different_prf','unresolved_generation','nan_complex64']:
        with tempfile.TemporaryDirectory() as td:
            N=8;files=[]
            for k in range(4 if case=='unresolved_generation' else 2):
                idx=np.arange(k%2,N,2);E=np.full(idx.size,1+0j if k<2 else 2+0j,dtype=np.complex64)
                if case=='nan_complex64' and k==0:E[1]=complex(float('nan'),0)
                p=Path(td)/f'arm_el+0_{k:02d}.npz';np.savez(p,idx=idx,E=E,meta=[0,k%2,2,N,10000 if case=='different_prf' and k==1 else 19700,0],t_start=[1700000000.]);files.append(str(p))
            esm=types.SimpleNamespace(SHD=td,one_generation=choose)
            row={'case':case}
            for name,fn in [('waveform',wf.cell_series),('scene',sc.series)]:
                try:
                    with contextlib.redirect_stdout(io.StringIO()):v=fn(esm,'arm',0.)
                    E=v[0] if name=='waveform' and v is not None else v
                    row[name]={'accepted':v is not None,'nonfinite_E':int((~np.isfinite(E)).sum()) if E is not None else None}
                except Exception as e:row[name]={'accepted':False,'error':type(e).__name__}
            rr.append(row)
    result['reader_input_probes']=rr
    # The current semantic freeze detects numeric mutation and ignores order changes.
    j=base.js('outputs/read_canyonnull_0910.json');nums=freeze.scrape_numbers(j)
    def mutate(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in ['n_static_changed','n_hampel','n_changed','n_mask'] and isinstance(x,int):v[k]=x+17
                else:mutate(x)
        elif isinstance(v,list):
            for x in v:mutate(x)
    mutant=copy.deepcopy(j);mutate(mutant);n2=freeze.scrape_numbers(mutant)
    result['freeze']={'fields_changed':sum(nums.get(k)!=n2.get(k) for k in set(nums)|set(n2)),'event_ledgers':['canyonnull','dropladder','scenephysics','wfsurvive']}
    # Library source unchanged: metadata coverage, not full-paper verification.
    result['literature']=old.design_and_literature()['literature']
    return result

def refine():
    c=json.loads(CACHE.read_text());n=c['checks']['numeric'];c['checks']['readers']=json.loads((ROOT/'work/current_review_0913_readers.json').read_text())
    atlas=old.loadmod('benchmark/build_md_atlas.py');wf=old.loadmod('benchmark/read_wfsurvive_0912.py')
    ai=base.js('outputs/md_atlas_index.json');Z=np.load(ROOT/'outputs/elevation_sweep_md.npz',allow_pickle=False);ac=[]
    for t in ai['topics'].values():
        for arm,r in t['arms'].items():
            rt=atlas.arm_rates(arm)
            for el,v in r['cells'].items():
                if v.get('rhythm_share_pct') is None:continue
                e=float(el);E=np.asarray(Z[f'{arm}/el{e:+g}'],complex);pr=atlas.prf_of(arm,e);ft=atlas.f_tip_at(rt,e)
                share,_,_,_=atlas.rhythm_share(E,rt['f_flash_hz'],ft,prf=pr)
                ac.append({'engine':arm,'el':e,'fc':rt['fc_hz'],'prf':pr,'published':v['rhythm_share_pct'],'recomputed':share,'delta':abs(v['rhythm_share_pct']-share) if share is not None else None})
    assert ac
    n['atlas']={'rows':ac,'n':len(ac),'mismatch_over_rounding':sum(v['delta'] is None or v['delta']>.051 for v in ac),'nondefault_fc':sum(v['fc']!=atlas.FC for v in ac),'nondefault_prf':sum(v['prf']!=atlas.PRF for v in ac)}
    tt=np.arange(8000)/20000;n['offband_survival']=[]
    for amp in [0.,.1,1.]:
        got=wf.survive(.01*np.exp(2j*np.pi*400*tt)+amp*np.exp(2j*np.pi*1600*tt),20000.,[dict(std='nr',frame_rate_hz=2000.,frame_ms=.5)],400.)
        n['offband_survival'].append({'offband_amplitude':amp,'input_tip_amplitude':.01,'input_tip_hz':400.,'offband_hz':1600.,'output':got['nr']})
    for v in n['offband_survival']:
        def box_gain(f):
            return abs(np.sin(np.pi*10*f/20000)/(10*np.sin(np.pi*f/20000)))
        predicted=20*np.log10(np.hypot(v['input_tip_amplitude']*box_gain(v['input_tip_hz']),v['offband_amplitude']*box_gain(v['offband_hz']))/v['input_tip_amplitude'])
        v['independent_box_filter_db']=float(predicted)
        v['finite_record_difference_db']=v['output']['rms_keep_tipband_db']-float(predicted)
        assert abs(v['finite_record_difference_db'])<.02
    bj=base.js('outputs/bandflat_0913.json');summ=[]
    for s in bj['series']:
        rows=[r for r in n['band_halves'] if r['env']==s['env'] and r['el']==s['el_deg']]
        half=float(np.median([r['ac_half_db'] for r in rows]))
        summ.append({'env':s['env'],'el':s['el_deg'],'moving_spread_db':s['moving_band_spread_db'],'published_half_db':s['within_cell_spread_db'],'matching_ac_half_db':half,'published_reading':s['reading_ko'],'with_ac_exceeds_double':s['moving_band_spread_db']>=2*half})
    n['band_half_summary']=summ
    pub=base.js('outputs/read_wfsurvive_0912.json')['rows'];grp=collections.defaultdict(list)
    for r in pub:grp[(r['scene'],r['el_deg'],r['arm'])].append(r['engine'])
    n['waveform_scope']={'rows':len(pub),'negative_az':sum('_az-' in r['engine'] for r in pub),'rotor':sum('_rot' in r['engine'] for r in pub),'prf':sum('_prf' in r['engine'] for r in pub),'ambiguous_groups':[{'scene':k[0],'el':k[1],'arm':k[2],'engines':v} for k,v in grp.items() if len(v)>1]}
    d=n['drone_flash'];clean=[r for r in d['rows'] if r['n_missing']==0];d['complete_rows']=len(clean);d['complete_changed']=sum(r['current']!=r['with_drone_flash'] for r in clean)
    ex=max((r for r in clean if r['el']!=0 and r['current']['h1_over_h2_db'] is not None and r['with_drone_flash']['h1_over_h2_db'] is not None),key=lambda r:abs(r['current']['h1_over_h2_db']-r['with_drone_flash']['h1_over_h2_db']))
    d['example']=ex
    c['source_hashes'].update(base.HASHES);save(c)
    print('refine saved',n['atlas']['n'],n['atlas']['mismatch_over_rounding'],flush=True)

def findings(c):
    x=c['checks'];n=x['numeric'];r=x['readers'];out=[]
    def add(title,status,key,evidence,fix,refs):
        sources=[base.source(p,s) for p,s in refs];assert all(s['found'] for s in sources),sources
        out.append(dict(title=title,status=status,result_key=key,evidence=evidence,fix=fix,sources=sources))
    d=n['drone_flash'];e=d['example']
    add('주 집계가 다른 기체에도 기본 기체의 날개 통과율을 쓴다','새 확인 · 발간 수치 영향','checks.numeric.drone_flash',
        f"다른 기체 {d['n']}칸의 현재 track은 발간값과 {d['current_mismatch']}칸 불일치다. 날개 통과율을 기체 제원으로 바꾸면 {d['changed']}칸이 변하며, 완전한 {d['complete_rows']}칸 중 {d['complete_changed']}칸도 변한다. "
        f"예: {e['engine']} / el{e['el']:+g}, h1_over_h2_db가 {e['current']['h1_over_h2_db']:+.2f} → {e['with_drone_flash']['h1_over_h2_db']:+.2f} dB다. "
        f"기준 날개 통과율은 {e['default_flash_hz']:.5g} → {e['correct_flash_hz']:.5g} Hz다. STFT 창과 배음 측정 위치가 함께 달라진다. 기체 제원에 맞춘 잣대의 보정이며 실측 검증이 아니다.",
        '칸별 날개 통과율을 원장에 기록하고 STFT 창·캐시 키·배음 비교·fixed 지표에 함께 전달한다. 기체가 다른 팔의 track과 fixed를 재생성한다. 아틀라스의 기체별 계산과 주 집계를 함께 대조한다.',
        [('benchmark/elevation_sweep_md.py','prf, ffl = float(TJ["prf_hz"])'),('benchmark/elevation_sweep_md.py','h1_over_h2_db=round(float(pkdb(ffl)'),('benchmark/build_md_atlas.py','f_flash_hz=int(s.prop_blades) * f_rev')])
    h=[v for v in n['band_half_summary'] if v['env']=='outdoor01']
    add('움직이는 전력의 대역 퍼짐을 전체 전력의 짝·홀 차이와 비교한다','새 확인 · 발간 해석 영향','checks.numeric.band_half_summary',
        '대역 퍼짐은 E의 평균을 뺀 전력인데 half_spread는 평균을 포함한 전력이다. '+ ' '.join(f"실외 el{v['el']:+g}: 움직이는 몫의 대역 퍼짐 {v['moving_spread_db']:.3f} dB, 발간 짝·홀 차이 {v['published_half_db']:.3f} dB, 같은 AC 전력으로 계산한 차이 {v['matching_ac_half_db']:.3f} dB." for v in h)+
        ' 두 실외 줄 모두 기존의 «흔들림보다 크다» 문장이 같은 통계로 맞추면 성립하지 않는다. AC 계산은 전체 자세 평균을 한 번 제거한 뒤 같은 짝·홀 분할을 적용했다. 이 분할 차이는 결정적 표본 분할의 민감도이며 신뢰구간이 아니다.',
        '전체 전력과 AC 전력 각각에 대응하는 짝·홀 차이를 계산한다. 표 제목은 «짝·홀 분할 차이»로 쓰고, 재실행 산포·광선 격자 민감도와 별도로 기록한다. 비교 문장은 동일한 통계끼리 만든다.',
        [('benchmark/read_bandflat_0913.py','a, b = halves_level_db(E)'),('benchmark/read_bandflat_0913.py','mv_band < 2.0 * half'),('benchmark/read_bandflat_0913.py','half = float(np.median')])
    vals=n['offband_survival']
    add('새 띠 생존 지표도 띠 밖에서 접혀 온 성분을 센다','새 확인 · 합성 반례','checks.numeric.offband_survival',
        f"입력 {vals[0]['input_tip_hz']:g} Hz 성분의 진폭을 {vals[0]['input_tip_amplitude']:g}로 고정했다. 띠 밖 {vals[0]['offband_hz']:g} Hz 성분의 진폭만 "+' → '.join(str(v['offband_amplitude']) for v in vals)+'로 키우면 rms_keep_tipband_db는 '+ ' → '.join(f"{v['output']['rms_keep_tipband_db']:+.2f}" for v in vals)+' dB로 오른다. '+
        f"접힌 띠는 {vals[0]['output']['tipband_lo_hz']:g}~{vals[0]['output']['tipband_hi_hz']:g} Hz이며, 세 경우 모두 tipband_discriminates=true다. 현재의 좁은 띠 허용 조건도 통과한다. 입력의 관심 성분은 불변인데 출력 분자는 다른 성분까지 받아들인다.",
        '관심 띠와 그 밖을 입력에서 분리하고 같은 평균·표본화 연산을 각각 적용해 출력 기여를 나란히 낸다. 전체 혼합 신호에서 잰 값은 «접힌 띠의 총 RMS / 입력 관심 띠 RMS»로 정의한다. 이를 회전자 성분의 생존율로 단독 인용하는 문구를 고친다.',
        [('benchmark/read_wfsurvive_0912.py','_ref_tb = bandpow(x, prf, lo0, hi0)'),('benchmark/read_wfsurvive_0912.py','_post_tb = bandpow(y2, fr, lo, hi)'),('benchmark/read_wfsurvive_0912.py','그쪽은 rms_keep_tipband_db')])
    phase=r['band_runs']
    add('대역 판독 결과가 복소 반사율의 위상 평탄성을 다루지 않는다','설계 질문의 미해결 부분','checks.readers.band_runs',
        f"실제 판독기 main을 임시 입력·출력으로 실행했다. 반송파 사이 위상을 {phase['phase_step_rad']:g} rad씩, 전체 {phase['phase_span_rad']:g} rad 범위로 바꿔도 출력 수치 변화는 {len(phase['phase_numeric_changes'])}건이다. 레벨·변동 전력·스펙트럼 전력은 반송파별 상수 위상 회전에 불변이다. 현재 표가 재는 크기와 전력 구조의 변화는 유효하지만, 발주서가 요구한 «크기·위상 모두»에는 답하지 않는다.",
        '현 판독의 제목과 질문을 «대역 내 전력·변조 구조의 변화»로 맞춘다. 복소 평탄성은 알려진 전파 지연을 제거하고 같은 자세의 복소 응답을 비교하는 별도 항목으로 둔다. 성긴 반송파 표본 사이의 지연 모호성과 미관측 구간도 함께 기록한다.',
        [('runners/make_jobs_0929.py','네 점의 복소 반사율이 크기·위상 모두'),('benchmark/read_bandflat_0913.py','p = float(np.mean(np.abs(E) ** 2))'),('benchmark/read_bandflat_0913.py','Y = np.abs(np.fft.rfft')])
    q=n['structure_counterexample']
    add('구조 문턱 미통과를 백색잡음과 구별 불가로 확정한다','새 확인 · 판정 문구 과잉','checks.numeric.structure_counterexample',
        f"판정은 리듬 몫 초과와 빗살 대비의 고정 문턱을 AND로 묶는다. 잡음을 넣지 않은 {q['tone_hz']:g} Hz 단일 복소 정현파에서도 리듬 몫 {q['rhythm_pct']:.2f} %, 빈 수 비율 {q['rhythm_null_pct']:.2f} %, 빗살 대비 {q['comb_db']:.2f} dB가 나오지만 관문은 false다. 이때 출력 문장은 «백색잡음 널과 구별되지 않는다»가 된다. 단일 선의 통계와 백색잡음의 동등성을 검정한 결과가 아니다. 실외 원장에 실제 백색잡음이 있다는 판정도 이 두 요약치만으로는 성립하지 않는다.",
        'false 문장을 «설정한 두 구조 지표의 공동 문턱 미충족»으로 바꾼다. 두 지표를 개별적으로 보여주고, 잡음 모형과의 구별을 주장할 때는 명시한 널 분포·오류율·검정력을 별도 검사한다. 관문 미통과를 날개 신호의 부재로 해석하는 문장도 관찰 수준으로 고친다.',
        [('benchmark/read_bandflat_0913.py','has = bool(over_null is not None and over_null > 5.0'),('benchmark/read_bandflat_0913.py','움직이는 몫이 백색잡음 널과 구별되지 않는다')])
    add('공통 입력 검증이 새 판독 경로에 전파되지 않았다','기존 미해결 + 새 경로 · 잠재 결함','checks.readers.reader_input_probes',
        '파형·장면 두 판독기는 서로 다른 PRF의 샤드, 선택 후에도 값이 충돌하는 중복 세대, complex64 NaN을 각각 통과시켰다. one_generation의 진단을 버리고 전계·seen만 조립한다. 새 대역 판독기에 NaN을 넣으면 사유를 적고 거절하는 대신 '+str(phase['nan_input']['error'])+'로 중단됐다. '+
        f"대역 판독기의 빈 띠 분기는 반환값 {n['band_empty_return']['arity']}개인데 호출자는 {n['band_empty_return']['caller_expected']}개를 받는다. 현재 검사한 안정된 샤드의 비정상 전계는 없으며, 이 항목은 합성 입력에서 확인한 실패 처리 결함이다.",
        '공통 로더가 E·N·PRF·idx·비유한 값과 세대 선택 진단을 함께 반환하게 한다. 미완 입력과 미해결 충돌은 사유와 함께 기록한다. 세대는 완전성을 우선하고 저장 진단은 현재 규칙과 구분하며, 빈 띠의 반환 형식도 호출부와 맞춘다.',
        [('benchmark/read_wfsurvive_0912.py','fs, _ = esm.one_generation'),('benchmark/read_scenephysics_0913.py','fs, _ = esm.one_generation'),('benchmark/read_bandflat_0913.py','return None, None')])
    s=n['waveform_scope']
    add('파형 표의 조건 선택과 표시가 여전히 다른 팔들을 한 이름으로 묶는다','기존 미해결 · 발간 식별 문제','checks.numeric.waveform_scope',
        f"현재 {s['rows']}행에 음의 방위 태그 {s['negative_az']}행, 로터 변경 {s['rotor']}행, PRF 변경 {s['prf']}행이 들어 있다. 이 집단은 서로 겹칠 수 있다. 표에 쓰는 장면·앙각·스위치 이름 조합 중 {len(s['ambiguous_groups'])}개는 서로 다른 engine을 같은 이름으로 표시한다. 새 문법은 scene 이름에 적용됐지만 want의 옛 정규식과 표 라벨은 남아 있다. 원장에는 전체 engine이 있어 숫자 자체가 사라진 것은 아니다.",
        '연구 범위를 허용할 필드 목록으로 명시하고, 포함한 변화축은 표에 열로 표시한다. 전체 engine을 각 행의 근거로 연결하고 제외·미완 칸의 사유를 기록한다.',
        [('benchmark/read_wfsurvive_0912.py','and not re.search(r"_(ps|fs|bs|az|rot|shell|S0|rep|div|onlyrefr|phys|alt|fc)'),('benchmark/read_wfsurvive_0912.py','f"| {r[\'scene\']} | {r[\'el_deg\']:+g} | {r[\'arm\']}')])
    add('기존 감사 생성기가 현재 생산 의존성을 따라가지 못한다','기존 미해결 + 새 실행 오류','checks.boundaries.old_audit_failure',
        f"저장 중단 반례는 {x['boundaries']['old_audit_failure']['type']}: {x['boundaries']['old_audit_failure']['message']}로 중단된다. 추출한 저장 호출이 요구하는 bake_stamp를 시험 입력이 제공하지 않는다. 세대 재현 검사는 {x['generation']['error']}: {x['generation']['message']}로 중단된다. 새 _prfs 수집이 추출 병합 코드에 들어왔지만 시험 namespace에는 빠졌다. 이들은 생산 워커 장애의 증거가 아니라 감사의 재현성 결함이다.",
        '감사 어댑터에 생산 함수가 요구하는 의존성을 명시하고 추출 경계도 검사한다. 각 반례 결과를 성공·실패·실행 불가로 기록해 한 검사 실패가 나머지 검사의 저장을 막는 경로를 고친다. 기존 결함을 되돌린 변이 시험도 함께 확인한다.',
        [('benchmark/review_repository_0911.py','assert failure==\'OSError\',failure'),('benchmark/review_repository_0911.py',"'production merge block'"),('benchmark/elevation_sweep_md.py','_prfs.add(float(_m4[4]))')])
    lit=r['literature']
    add('선행연구 안내의 수집량과 재현율 분모가 현재 원장과 다르다','기존 미해결 · 안내 문면','checks.readers.literature',
        f"로컬 소장 원장은 {lit['n_rows']}행, 초록 {lit['n_abstracts']}행이다. README의 수집량·닻 분모가 이 원장과 다르다. 현재 재현율은 DOI와 구간 조건으로 셀 수 있는 {lit['stored_recall']['total']}개 중 {lit['stored_recall']['found']}개이며, 전체 닻 목록의 수와 구분해야 한다. 이번에는 로컬 메타데이터와 닻 조회를 검산했고 논문 전체 본문을 재독하지 않았다.",
        '안내의 수집량과 재현율을 현재 원장 키에서 생성한다. 전체 닻 수와 확인 가능한 분모, 초록 읽기와 본문 읽기 범위를 각각 표시한다.',
        [('prior_work/README.md','2025-01 이후 **275 편**'),('prior_work/README.md','재현율(아는 6 편)')])
    return out

def publish():
    import hashlib
    c=json.loads(CACHE.read_text());fs=findings(c);c['findings']=fs
    c['_meta']['finished_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    c['_meta']['final_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    c['checks']['queue_final']=old.prev.queue()
    sources=dict(c.get('source_hashes',{}));sources.update(base.HASHES)
    for p in ['benchmark/review_current_0913.py','src/arm_grammar.py','src/drones.py','outputs/elevation_sweep_md.npz']:
        with (ROOT/p).open('rb') as f:sources[p]=hashlib.file_digest(f,'sha256').hexdigest()
    c['_meta']['source_sha256']=sources;c.pop('source_hashes',None)
    c['checks']['snapshot_changes']=[]
    for p,d in sources.items():
        path=Path(p) if Path(p).is_absolute() else ROOT/p
        with path.open('rb') as f:now=hashlib.file_digest(f,'sha256').hexdigest()
        if d!=now:c['checks']['snapshot_changes'].append(p)
    for f in fs:
        for s in f['sources']:
            assert (ROOT/s['path']).read_text().splitlines()[s['line']-1].strip()==s['quote']
    c['checks']['source_quotes_verified']=sum(len(f['sources']) for f in fs)
    OUT.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')
    render(c)
    print('published',len(fs),'findings',flush=True)

def render(c):
    x=c['checks'];n=x['numeric'];r=x['readers'];j='outputs/current_review_0913.json';wide=x['wide']
    lines=['# 현재 상태와 추가 계산·판독 경로 점검','',f"점검 시각: {c['_meta']['checked_at_utc']} → {c['_meta']['finished_at_utc']}",f"커밋: {c['_meta']['head']} → {c['_meta']['final_head']}",'',
      '## 확인된 수정','',
      f"- 장면 분석 {r['scene_reproduction']['n_rows']}행의 대조군 오류 {r['scene_reproduction']['selected_wrong']}건. 필터 수치도 현재 발간값을 재현했다.",
      f"- 비기본 PRF {n['prf']['n']}칸의 track 재계산 불일치 {n['prf']['mismatch']}건.",
      f"- 아틀라스 리듬 몫 {n['atlas']['n']}칸 재계산의 반올림 범위 밖 불일치 {n['atlas']['mismatch_over_rounding']}건. 다른 반송파 {n['atlas']['nondefault_fc']}칸과 다른 PRF {n['atlas']['nondefault_prf']}칸을 포함한다. 그림을 전부 재렌더링한 검사는 아니다.",
      f"- Wi-Fi {len(n['wifi']['rows'])}행의 생산 함수 재현 불일치 {n['wifi']['mismatch']}건, 독립 누적합 계산 불일치 {n['wifi']['independent_mismatch']}건. 프레임 길이는 {next(v['frame_ms'] for v in n['wifi']['rates'] if v['std']=='wifi'):g} ms다.",
      f"- 이전 접힘 반례의 예상 {n['alias_fixed']['expected_hz']:g} Hz를 현재 판독기가 {n['alias_fixed']['got']['peak_frameavg_in_tipband_hz']:.2f} Hz로 찾는다.",
      f"- 기준선 수치 추출은 바꾼 사건 필드 {r['freeze']['fields_changed']}개를 감지한다.",'',
      '## 조사 범위와 남은 범위','',
      f"전체 파일 {wide['file_count']}개를 열거했다(.git·__pycache__ 제외, ignored 포함). JSON {wide['parsed']['.json']}개와 노트북 {wide['parsed']['.ipynb']}개를 파싱했고 각각 오류 {len(wide['json_parse_errors'])}·{len(wide['notebook_errors'])}건이다.",
      f"Python 구문 파싱 성공 {wide['parsed']['python']}개. 구문 오류 항목은 {wide['syntax_errors']}이며 기존 자료 추출 조각으로 확인했다. 파일 전부의 모든 줄을 의미 검증했다는 뜻은 아니다.",
      f"안정된 생산 샤드 {x['arrays']['files']}개는 모든 배열의 CRC·길이·idx 분할·비유한 값을 확인했고 오류 {len(x['arrays']['errors'])}건, 검사 중 변경 {len(x['arrays']['changed_during_read'])}건이다. ours의 cfg에 명시적으로 저장된 미적용 NaN은 결함에서 제외했다.",
      f"그 밖의 NPZ {x['other_arrays']['n_files']}개는 CRC와 NPY 헤더를 검사했다. 객체 배열은 역직렬화하지 않았다. 이미지·PDF·메쉬는 열거했으며 전부의 내용·기하 타당성을 재검증하지 않았다.",
      f"감사 종료 시 워커 {x['queue_final']['workers']}개. 실행 상태는 원장 checks.queue_final에 시각과 로그를 함께 남겼다. 조사 중 새로 쓰인 파일은 안정된 샤드 모집단과 분리했다.",
      '검사기는 기준선 이후 새 문제를 검출하는 범위를 가진다. 통과를 전체 과학적 타당성의 인증으로 해석하지 않는다. 검사별 원문은 checks.gates에 있다.','',
      '## 보완점','']
    for i,f in enumerate(c['findings'],1):
        lines += [f"### {i}. {f['title']}",'',f"**등급:** {f['status']}",'',f['evidence'],'',f"**수정 권고:** {f['fix']}",'',f"근거 원장: `{j}` → `{f['result_key']}`",'']
        for s in f['sources']:lines += [f"- [{s['path']}:{s['line']}](../{s['path']}#L{s['line']}) — `{s['quote']}`"]
        lines += ['']
    g=n['grammar_unknown']
    lines += ['## 별도 주의: 이름 왕복 검사의 범위','',f"현재 문법 검사에서는 원장과 창고의 이름이 통과했다. 다만 합성 이름 `{g['name']}`는 env={g['fields']['env']}, blade_law={g['fields']['blade_law']}로 나뉘고도 왕복 일치한다. 새 환경의 뜻까지 왕복 검사 하나로 보증하는 표현은 좁혀야 한다. 현재 알려진 환경에서 발생한 오류로 분류하지 않았다.",'',
      '## 재현과 변경 범위','',f"검증한 코드 인용 {c['checks']['source_quotes_verified']}개. 해시 확인 중 달라진 입력: {c['checks']['snapshot_changes']}.",
      '생산 코드·발간 원장·워커·큐는 수정하지 않았다. 이번 감사 생성기와 새 감사 JSON·Markdown·Jupyter 노트북을 작성했고 work에는 검사 캐시를 남겼다.','',
      '```bash',f'{sys.executable} benchmark/review_current_0913.py','```','']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'));from report_style import header,md,next_steps,build_notebook
    cells=[header(num='현재 점검',title='기존 수정 재검증과 새 판독의 계산·해석 점검',did='저장 자료를 검사하고 현재 생산 함수와 발간 수치를 대조했다.',
      results=[f"생산 샤드 {x['arrays']['files']}개 검사 ⟨{j} : checks.arrays⟩.",f"기체별 날개 통과율 적용 시 {n['drone_flash']['changed']}칸 변화 ⟨{j} : checks.numeric.drone_flash⟩.",f"아틀라스 {n['atlas']['n']}칸의 리듬 몫 재계산 ⟨{j} : checks.numeric.atlas⟩.",f"수정 권고 {len(c['findings'])}건 기록 ⟨{j} : findings⟩."],
      method=[('자료','전체 파일 열거·안정된 샤드 전체 배열 검사'),('판독','생산 함수 재계산·임시 입력으로 main 실행·독립 누적합 검산')],repro=dict(cmd=[f'{sys.executable} benchmark/review_current_0913.py'],out=[j],runtime='CPU 한 코어, 저장 자료 읽기'))]
    cells.append(md('## 확인된 수정과 조사 범위','',f"[자세한 점검 기록](CURRENT_REVIEW_0913.md)에 현재 통과한 항목과 검사 범위를 적었다. ⟨{j} : checks⟩"))
    for i,f in enumerate(c['findings']):
        cells.append(md(f"## {i+1}. {f['title']}",'',f"등급: {f['status']}",'',f['fix'],'',f"[재현 수치·원문 인용](CURRENT_REVIEW_0913.md) ⟨{j} : findings[{i}]⟩"))
    cells.append(next_steps([('기체별 잣대와 같은 통계의 대조를 적용한다','발간 수치와 비교 문장의 보정 범위','CURRENT_REVIEW_0913.md'),('공통 입력 검증과 감사 어댑터를 정비한다','잘못된 입력과 실행 불가의 식별','CURRENT_REVIEW_0913.md'),('파형·대역 표의 질문과 지표 정의를 맞춘다','수치로 뒷받침되는 해석 범위','CURRENT_REVIEW_0913.md')]))
    build_notebook(str(NB),cells,strict=True)

if __name__=='__main__':
    if '--publish' in sys.argv:publish()
    else:
        scope();probes()
        rr=reader_checks();(ROOT/'work/current_review_0913_readers.json').write_text(json.dumps(rr,ensure_ascii=False,indent=1,allow_nan=False))
        refine();publish()
