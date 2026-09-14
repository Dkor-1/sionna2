"""Read-only post-upgrade audit. Run with the workspace Python.
CPU one core; production and fault-injection outputs are isolated in temporary directories.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['SIONNA2_ALLOW_CPU']='1'
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import collections,contextlib,copy,hashlib,inspect,io,json,math,re,subprocess,sys,tempfile,time,types
from pathlib import Path
from unittest.mock import patch
import numpy as np
import review_remaining_0914 as before
old=before.old;base=before.base;ROOT=before.ROOT
sys.path.insert(0,str(ROOT/'src'))
import reader_gate as gate
CACHE=ROOT/'work/upgrade_review_0914_cache.json';OUT=ROOT/'outputs/upgrade_review_0914.json';MD=ROOT/'docs/UPGRADE_REVIEW_0914.md';NB=MD.with_suffix('.ipynb')
def read():return json.loads(CACHE.read_text())
def save(c):
 c.setdefault('source_hashes',{}).update(base.HASHES);CACHE.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n')
def runcheck(script,args=[]):
 p=subprocess.run([sys.executable,script,*args],cwd=ROOT,text=True,capture_output=True,timeout=150)
 return dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
def setup():
 from importlib.metadata import version
 c={'_meta':dict(generator='benchmark/review_upgrade_0914.py',started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),versions={p:version(p) for p in ['sionna','sionna-rt','mitsuba','drjit']}),'checks':{}}
 c['initial_status']=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
 c['protected_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for pattern in ['outputs/*.json','docs/*.md','reports/*.ipynb'] for p in ROOT.glob(pattern) if p not in [OUT,MD]}
 c['registry']=base.js('runners/SOLVER_BUILDS.json');save(c)
 c['checks']['solver_gate']=runcheck('benchmark/check_solver_build.py');save(c);print('solver gate',c['checks']['solver_gate']['exit'],flush=True)

def corrected():
 with patch.object(before,'CACHE',CACHE):before.altitude_cases();before.real_readers()
 c=read();alt=old.loadmod('benchmark/read_altitude_0914.py');tone=np.exp(2j*np.pi*np.arange(8192)/4)
 c['checks']['complex_lag_pair']=alt.lag_corr(tone)
 # Reproduce main's handling of a mismatched shard build when the ledger still agrees.
 # Inherited altitude cases isolate all writes and carry complete current-ledger metadata.
 save(c)
 print('prior fixes exercised',flush=True)

def cpu_modes():
 c=read();import mitsuba as mi;import drjit as dr;import sionna.rt as rt
 dr.set_thread_count(1)
 repro=old.loadmod('benchmark/minrepro_hash_0902.py');sc,nf=repro.build(24,.7)
 rows=[];kw=dict(max_depth=2,los=False,specular_reflection=True,diffuse_reflection=True,refraction=False,diffraction=False,edge_diffraction=False,samples_per_src=40000000,max_num_paths_per_src=2000000,seed=42)
 for mode in [False,True]:
  solver=rt.PathSolver(deterministic=mode);observations=[];start=time.monotonic()
  for _ in range(3):
   p=solver(sc,**kw);ar=np.array(p.a[0],copy=True).astype(np.float64);ai=np.array(p.a[1],copy=True).astype(np.float64);a=(ar+1j*ai).reshape(-1,ar.shape[-1])[0];tau=np.array(p.tau,copy=True).astype(np.float64).reshape(-1,a.size)[0];h=np.sum(a*np.exp(-2j*np.pi*repro.FC*tau));order=np.lexsort((a.imag,a.real,tau))
   observations.append(dict(n_paths=len(a),h_real=float(h.real),h_imag=float(h.imag),h_abs=float(abs(h)),sorted_path_sha256=hashlib.sha256(np.column_stack((tau[order],a[order].real,a[order].imag)).tobytes()).hexdigest()))
  rows.append(dict(deterministic=mode,observations=observations,seconds=round(time.monotonic()-start,3)))
  print('CPU mode',mode,[r['n_paths'] for r in observations],flush=True)
 c['checks']['cpu_modes']=dict(variant=mi.variant(),threads=dr.thread_count(),affinity=sorted(os.sched_getaffinity(0)),solver_init_signature=str(inspect.signature(rt.PathSolver)),triangles=nf,n_side=24,scattering=.7,fc_hz=repro.FC,settings=kw,rows=rows,old_saved_one_thread=base.js('outputs/thread_ladder_0903.json')['rows'][0])
 save(c)

def gate_adversaries():
 c=read();checker=old.loadmod('benchmark/check_solver_build.py');rows=[]
 for case,stamp in [('valid','sionna=2.1.0 sionna-rt=2.1.0 mitsuba=3.9.1 drjit=1.5.0'),('wrong_dependency','sionna=2.1.0 sionna-rt=2.1.0 mitsuba=3.9.1 drjit=9.9.9'),('missing_dependency','sionna-rt=2.1.0')]:
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'sionna_p1_r15_n8_rt210_d2_el-60_00.npz';np.savez(p,idx=np.arange(8),E=np.ones(8,complex),meta=[-60,0,1,8,19700,1],solver_build=np.array(stamp));log=io.StringIO()
   with patch.object(checker,'SHD',td),contextlib.redirect_stdout(log):res=checker.check_shards()
   rows.append(dict(case=case,stamp=stamp,errors=res,stdout=log.getvalue()))
 c['checks']['stamp_gate_cases']=rows
 # Order dependence: a rejected control establishes the global PRF before rejection.
 m=old.loadmod('benchmark/read_bandflat_0913.py');arms={f:m.arm_name('free',f) for f in [3450,3500,3550]};rr=[]
 class Arrays(dict):
  @property
  def files(self):return list(self)
 Z=Arrays();N=8192;E=np.exp(2j*np.pi*53*np.arange(N)/N)
 for fc,arm in arms.items():
  f=before.prev.parse(arm)
  for spp in [4000000000,3900000000]:
   a=before.prev.unparse({**f,'spp':str(spp)});Z[a+'/el-30']=E.copy();rr.append(dict(engine=a,el_deg=-30,n_poses=N,n_missing=0,n_zero_field=0,prf_hz=19700.,fc_hz=fc*1e6))
 rejected=copy.deepcopy(rr[1]);rejected.update(n_missing=N//2,prf_hz=10000.);rr2=[r for r in rr if r['engine']!=rejected['engine']]
 first=m.budget_shape_spread_db(arms,-30,[rejected,*rr2],Z);last=m.budget_shape_spread_db(arms,-30,[*rr2,rejected],Z)
 c['checks']['budget_rejected_row_order']=dict(rejected_first=first,rejected_last=last,rejected_row=rejected)
 save(c);print('guard adversaries saved',flush=True)


def extra():
 c=read();m=old.loadmod('runners/worker_supervisor.py');cases=[]
 for name,doc in [('invalid_value',{'gpus':'typo'}),('nan_threshold',{'gpus_if_external':[4],'external_mb':'nan'}),('valid_empty',{'gpus':[]}),('malformed',None)]:
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'hold.json';p.write_text(json.dumps({'gpus':[4]}));logs=[]
   with patch.object(m,'HOLD_JSON',str(p)),patch.object(m,'_hold_last',{'v':None}),patch.object(m,'_hold_warned',{'v':None}):
    initial=m.temp_hold({4:10000},log=logs.append);p.write_text('{' if doc is None else json.dumps(doc));result=m.temp_hold({4:10000},log=logs.append)
   cases.append(dict(case=name,before=sorted(initial),after=sorted(result),logs=logs))
 c['checks']['gpu_hold_cases']=cases
 # Replace the inherited old return-schema assumption with the current cleanup API.
 with tempfile.TemporaryDirectory() as td:
  p=Path(td);a=p/'a.json';b=p/'b.md';a.write_text('{"v":"old"}');b.write_text('old');replace=gate.os.replace;calls=[];sweeps=[]
  def interleave(src,dst):
   replace(src,dst);calls.append(str(dst))
   if len(calls)==1:sweeps.append(gate.sweep_orphans([td]))
  with patch.object(gate.os,'replace',interleave):result=before.attempt(lambda:gate.publish({str(a):{'v':'new'},str(b):'new'}))
  c['checks']['orphan_cleanup_interleaving']=dict(**result,sweeps=sweeps,removed_active_temps=sum(len(s['removed']) for s in sweeps),kept_alive=sum(len(s['kept_alive']) for s in sweeps),json_value=json.loads(a.read_text()),markdown_value=b.read_text())
 m=old.loadmod('benchmark/read_wfsurvive_0912.py');choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation'];esm=types.SimpleNamespace(SHD=str(ROOT/'outputs/elev_sweep_shards'),one_generation=choose);published=base.js('outputs/read_wfsurvive_0912.json')
 with tempfile.TemporaryDirectory() as td,patch.object(m,'OUT',str(Path(td)/'wf.json')),patch.object(m,'MD',str(Path(td)/'wf.md')),patch.object(m,'prod',lambda:esm),contextlib.redirect_stdout(io.StringIO()):
  m.main();fresh=json.loads((Path(td)/'wf.json').read_text())
 by=lambda rows:{(r['engine'],r['el_deg']):r for r in rows};a=by(published['rows']);b=by(fresh['rows'])
 c['checks']['wf_publication']=dict(old_count=len(a),new_count=len(b),old_ledger_rows=published['_meta']['n_ledger_rows'],new_ledger_rows=fresh['_meta']['n_ledger_rows'],added=[b[k] for k in sorted(set(b)-set(a))],removed=[a[k] for k in sorted(set(a)-set(b))],common_changed=[dict(engine=k[0],el=k[1],differences=before.diffs(a[k],b[k])) for k in sorted(set(a)&set(b)) if a[k]!=b[k]])
 c['checks']['existing_gates']={name:runcheck('benchmark/'+name+'.py') for name in ['check_arm_names','check_reader_gate','check_new_file_rules','check_report_links','check_row_pointers']};c['checks']['freeze']=runcheck('benchmark/freeze_0912.py',['--check'])
 mode=c['checks']['cpu_modes']['rows'];u,v=[r['observations'][0] for r in mode];c['checks']['cpu_modes']['amplitude_change_db']=20*math.log10(v['h_abs']/u['h_abs']);c['checks']['cpu_modes']['complex_relative_change']=abs(complex(v['h_real']-u['h_real'],v['h_imag']-u['h_imag']))/u['h_abs']
 save(c);print('extra checks saved',flush=True)

def queue_snapshot():
 import shlex
 c=read();esm=old.loadmod('benchmark/elevation_sweep_md.py');jobs=[]
 lines=base.read('runners/jobs_0931_bridge.txt').splitlines();logp=ROOT/'runners/logs/sup_bridge_0931.log';log=logp.read_text();launched=re.findall(r'띄움 #(\d+) pid=(\d+)',log);finished=re.findall(r'끝 pid=(\d+) gpu=\d+ rc=(\d+) ([\d.]+)분',log)
 for line in lines:
  if not line.strip() or line.startswith('#'):continue
  opts=before.prev.options(line);f=before.prev.parse('sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2');f.update({key:opts[arg] for arg,key in {'--sw':'switches','--spp':'spp','--n-poses':'n_poses','--max-depth':'max_depth','--range-m':'range_m','--env':'env'}.items() if arg in opts});oldarm=before.prev.unparse(f);newarm=before.prev.unparse({**f,'solver_build':'210'});el=float(opts['--els']);sh=int(opts['--shard']);oldpath=ROOT/'outputs/elev_sweep_shards'/f'{oldarm}_el{el:+g}_{sh:02d}.npz';newpath=oldpath.with_name(f'{newarm}_el{el:+g}_{sh:02d}.npz');rec=dict(old_arm=oldarm,new_arm=newarm,el=el,shard=sh,old_exists=oldpath.exists(),new_exists=newpath.exists());errs=[]
  if oldpath.exists():
   with np.load(oldpath,allow_pickle=False) as z:
    ix=z['idx'];N=int(z['meta'][3]);ns=int(z['meta'][2]);rec.update(old_has_dup='n_dup' in z.files,old_seconds=float(z['meta'][5]),old_build=str(z['solver_build']) if 'solver_build' in z else 'unrecorded',old_n=N,old_prf=float(z['meta'][4]))
    if not np.array_equal(ix,np.arange(sh,N,ns)):errs.append('partition')
    if z['E'].shape!=ix.shape or not np.isfinite(z['E']).all():errs.append('E')
    if N!=int(opts['--n-poses']) or int(z['cfg'][1])!=int(opts['--max-depth']) or int(z['cfg'][2])!=int(opts['--spp']):errs.append('settings')
   base.digest(str(oldpath))
  rec['errors']=errs;jobs.append(rec)
 c['checks']['bridge']=dict(checked_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),jobs=jobs,n_jobs=len(jobs),n_cells=len({(r['new_arm'],r['el']) for r in jobs}),n_arms=len({r['new_arm'] for r in jobs}),launched=len(launched),finished=len(finished),failed=sum(int(r[1])!=0 for r in finished),last_status=next(s for s in reversed(log.splitlines()) if ' 상태 ' in s),old_worker_hours=sum(r.get('old_seconds',0) for r in jobs)/3600)
 records=[];counts=collections.Counter();errors=[]
 for p in sorted((ROOT/'outputs/elev_sweep_shards').glob('*.npz')):
  try:
   with np.load(p,allow_pickle=False) as z:
    stamp=str(z['solver_build']) if 'solver_build' in z else 'unrecorded';counts[stamp]+=1
    if '_rt210_' in p.name:
     a={k:z[k] for k in z.files};records.append(dict(file=p.name,keys=list(a),stamp=stamp,n_samples=len(a['idx']),n_poses=int(a['meta'][3]),prf_hz=float(a['meta'][4]),finite=bool(np.isfinite(a['E']).all()),mtime=p.stat().st_mtime,complete=bool(esm.shard_done(str(p)))))
  except Exception as e:errors.append(dict(file=p.name,error=str(e)))
 c['checks']['version_inventory']=dict(stamps=dict(counts),new_shards=records,errors=errors)
 L=base.js('outputs/elevation_sweep_md.json');c['checks']['version_inventory']['ledger_rows']=len(L['rows']);c['checks']['version_inventory']['ledger_new_version_rows']=sum('_rt210_' in r['engine'] for r in L['rows'])
 save(c);print('queue snapshot saved',flush=True)

def collect_findings(c):
 x=c['checks'];out=[]
 def add(title,kind,evidence,fix,key,refs):
  out.append(dict(title=title,kind=kind,evidence=evidence,fix=fix,result_key=key,sources=[base.source(p,t) for p,t in refs]))
 cpu=x['cpu_modes'];f,t=[r['observations'][0] for r in cpu['rows']]
 add('신버전 기본 모드와 결정 모드를 분리해서 읽어야 한다','현재 생산 설정과 새 실험 결과',
  f"생산 코드는 PathSolver()를 생성한다. 설치본의 생성자 서명은 {cpu['solver_init_signature']}이므로 현재 다리 큐는 결정 모드를 켠 시험이 아니다. 기존 --det는 반환된 경로의 합산 순서를 정렬하는 하네스 옵션이다. 실제 CPU {cpu['threads']}스레드·합성 평판 {cpu['n_side']**2}장·광선 {cpu['settings']['samples_per_src']}에서 모드별 반복은 각각 {len(cpu['rows'][0]['observations'])}회 일치했지만, 경로 수는 {f['n_paths']}→{t['n_paths']}, 합산 전계 크기는 {cpu['amplitude_change_db']:+.6f} dB 달랐다. 서로 다른 경로 집합의 물리적 정답을 이 결과로 고르지는 않는다.",
  '버전 비교의 현재 기본 모드는 보존하고 결정 모드를 별도 조건으로 추가한다. 생성자 옵션·샤드 도장·팔 이름·재개 판정을 함께 연결한다. --det의 설명은 합산 순서 정렬로 좁혀 새 생성자 인자와 구별한다. 지금 돌고 있는 큐 중간에 모드를 바꾸지 않는다. 기본 모드는 고정 씨앗에서도 재현성을 보장하지 않으므로, 버전 사이 관측 차이와 실행별 차이를 구별할 동일 버전 반복을 일부 조건에 추가한다.',
  'checks.cpu_modes',[('benchmark/elevation_sweep_md.py','_solver = RP.rt.PathSolver()'),('benchmark/elevation_sweep_md.py','ap.add_argument("--det"')])
 cases=x['stamp_gate_cases']
 add('창고 도장 검사는 전체 패키지 묶음을 대조하지 않는다','합성 입력으로 확인한 검사 범위의 공백',
  f"쓰기 전 build_tag는 장부의 패키지 묶음을 검사하지만 창고 검사 check_shards는 sionna-rt 부분만 읽는다. 정상 도장과 drjit만 다른 도장, 의존성 이름을 생략한 도장 모두 검사 오류 수가 {[r['errors'] for r in cases]}였다. 운영 창고에서 그러한 잘못된 도장을 발견했다는 뜻은 아니다. 정상 작동하는 쓰기 전 관문과 저장된 자료의 사후 검사를 구분해야 한다.",
  '저장 도장을 구조화해 필수 패키지 필드·전체 장부 값과 비교한다. 기록 없는 구세대는 별도 상태로 보존한다. 현재 등록된 묶음과 다른 스탬프를 넣는 사후 검사 반례를 추가한다.',
  'checks.stamp_gate_cases',[('benchmark/check_solver_build.py','want = None if rt == "2.0.1"'),('benchmark/elevation_sweep_md.py','if want != SOLVER_BUILD:')])
 mix=next(r for r in x['altitude_main_cases'] if r['case']=='mixed_solver_builds');pair=next(r for r in x['altitude_main_cases'] if r['case']=='pair_solver_builds_differ')
 add('고도 버전 검사는 원장을 보지만 원자료 도장을 확인하지 않는다','이전 지적이 일부 남은 입력 경로',
  f"원장의 버전 값이 같은 상태에서 같은 칸의 샤드 도장을 서로 다르게 만들면 main이 {mix['accepted_rows']}쌍을 발간했다. 비교 쌍의 실제 도장이 다른 경우도 {pair['accepted_rows']}쌍이 통과했다. 표집률 차이는 이제 거절한다. 따라서 표집률 수정과 실제 도장 검사의 완료 여부는 서로 다르다. 이번 운영 창고의 신버전 자료가 잘못 섞였다고 판정한 것은 아니다.",
  '선택한 샤드의 도장 집합을 반환해 원장과 대조하고, 비교 쌍과 빈 하늘 대조까지 같은 계약을 적용한다. unknown과 known이 함께 있는 상태는 실제 서로 다른 버전이 입증된 상태와 구별한다.',
  'checks.altitude_main_cases',[('benchmark/read_altitude_0914.py','_ba, _bb = r.get("solver_build")'),('benchmark/read_altitude_0914.py','n0, prf, why = check_shards(fs)')])
 b=x['budget_rejected_row_order']
 add('거절할 대조군이 대역 비교의 기준 표집률을 선점한다','새 입력 검사에서 재현한 순서 의존성',
  f"불완전한 대조 행을 먼저 두면 그 행의 {b['rejected_row']['prf_hz']:g} Hz가 ref_prf에 기록된다. 나중에 해당 행을 버리면서도 기준은 남아 정상 행까지 거절한다. 같은 행 집합의 순서를 바꾸자 비교 주파수 수가 {b['rejected_first']['n_fc']}→{b['rejected_last']['n_fc']}개, 대역 모양 변화가 계측 불가→{b['rejected_last']['shape_spread_db']:.1f} dB로 바뀌었다. 현재의 실제 C 자료에서 같은 잘못이 발생했다는 지적은 아니다.",
  '기준 표집률은 선언된 기준 팔의 검증된 행에서 정한다. 후보 행의 모든 검사가 통과하기 전에는 공유 기준을 갱신하지 않는다. 거절된 행의 앞뒤 순서를 바꿔도 결과와 제외 사유가 보존되는 시험을 둔다.',
  'checks.budget_rejected_row_order',[('benchmark/read_bandflat_0913.py','elif ref_prf[0] is None:'),('benchmark/read_bandflat_0913.py','ref_prf[0] = float(_pr)')])
 h=x['gpu_hold_cases']
 add('유효한 JSON 안의 잘못된 값은 GPU 보류를 해제한다','운영 규약의 잠재 결함 · 임시 파일에서 재현',
  f"직전 보류 {h[0]['before']}를 설정한 뒤 gpus 값을 잘못된 문자열로 바꾸면 보류가 {h[0]['after']}로 바뀐다. 조건부 보류의 문턱을 문자열 nan으로 바꿔도 해제된다. JSON 문법 자체가 깨진 경우는 직전 보류를 유지하므로, 파싱 실패와 값 검증 실패가 다르게 처리된다. 실제 운영 설정은 현재 정상이며 GPU 보류가 유지되고 있다.",
  '명시적 빈 목록과 값 오류를 구분한다. GPU 번호·문턱의 유한성·범위를 먼저 검증하고, 유효하지 않은 설정은 마지막 정상 보류를 유지한다. 시험은 임시 설정 경로에서 수행한다.',
  'checks.gpu_hold_cases',[('runners/worker_supervisor.py','out = set(_as_gpu_list'),('runners/worker_supervisor.py','_hold_last["v"] = set(out)'),('runners/worker_supervisor.py','thr = float(str(d.get')])
 wf=x['wf_publication']
 add('마지막 구버전 병합을 파형 발간물이 아직 따라가지 못했다','현재 발간 동기화 문제',
  f"현재 파형 원장은 입력 원장 {wf['old_ledger_rows']}행 기준으로 {wf['old_count']}행을 싣는다. 현재 입력 {wf['new_ledger_rows']}행을 실제 main으로 읽으면 {wf['new_count']}행이다. 공통 행의 값 변화 {len(wf['common_changed'])}개, 새로 들어갈 행 {len(wf['added'])}개이며 모두 구버전 실외 표집률 비교다. 신버전이 들어와서 생긴 차이가 아니다. freeze는 이 차이를 보고하지 않고 신버전 연기 시험 샤드 수 증가만 보고했다.",
  '현재 구버전 원장을 기준으로 파형 판독과 이를 인용하는 산출물을 다시 생성한다. 생성기 해시·입력 원장 해시·행 정체성으로 최신 여부를 확인하고, 동결 통계 통과와 발간 최신성을 별도 조건으로 둔다.',
  'checks.wf_publication',[('benchmark/read_wfsurvive_0912.py','def main()'),('docs/SIONNA_UPGRADE_0914.md','움직였다면 뜻은 하나다')])
 return out

def publish():
 c=read();x=c['checks'];c['findings']=collect_findings(c);q=x['bridge'];v=x['version_inventory'];cpu=x['cpu_modes'];j='outputs/upgrade_review_0914.json'
 assert all(r['error'] is None for r in x['actual_reader_mains'].values())
 assert x['wf_publication']['new_count']>x['wf_publication']['old_count'], 'Waveform publication has caught up; reassess finding.'
 assert x['budget_rejected_row_order']['rejected_first']['n_fc']==0 and x['budget_rejected_row_order']['rejected_last']['n_fc']>0, 'Budget order finding changed; reassess.'
 assert all(r['errors']==0 for r in x['stamp_gate_cases']), 'Stamp validation changed; reassess finding.'
 assert x['gpu_hold_cases'][0]['before'] and not x['gpu_hold_cases'][0]['after'], 'GPU hold finding changed; reassess.'
 c['_meta']['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());c['_meta']['final_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 hashes={**c.get('source_hashes',{}),**base.HASHES};c['checks']['source_changes']=[p for p,h in hashes.items() if (ROOT/p).exists() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
 c['checks']['protected_changes']=[p for p,h in c['protected_hashes'].items() if (ROOT/p).exists() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
 c['_meta']['source_sha256']={p:h for p,h in hashes.items() if (ROOT/p).exists()};c['_meta']['source_sha256']['benchmark/review_upgrade_0914.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();c.pop('source_hashes',None)
 for f in c['findings']:
  for s in f['sources']:
   assert s['found'],s
   assert (ROOT/s['path']).read_text().splitlines()[s['line']-1].strip()==s['quote']
 c['checks']['source_quotes_verified']=sum(len(f['sources']) for f in c['findings'])
 c['external_sources']=[dict(url='https://nvlabs.github.io/sionna/rt/api/paths_solvers.html',checked_on='2026-09-14',finding='설치본과 공식 문서 모두 PathSolver 생성자의 deterministic 기본값을 False로 둔다. 고정 seed만으로 기본 모드의 결정성을 보장하지 않는다.'),dict(url='https://github.com/NVlabs/sionna-rt/releases/tag/v2.1.0',checked_on='2026-09-14',finding='결정 모드 외에도 Mitsuba·Dr.Jit·재료·회절 등 변경을 명시한다. 버전 전환은 스택 묶음의 비교다.')]
 wf=x['wf_publication'];lines=['# Sionna 업그레이드 후 점검','',f"시작 HEAD `{c['_meta']['head']}` · 종료 HEAD `{c['_meta']['final_head']}` · {c['_meta']['finished_utc']}.",'',
 '설치와 버전별 이름 분리는 확인됐다. 현재 다리 큐는 기본 모드끼리의 버전 비교다. 새 결정 모드는 별도 대조가 필요하며, 일부 사후 검사와 구버전 발간 동기화에 보완점이 남았다.','',
 '## 확인된 현재 상태','',f"- 설치 묶음: {c['_meta']['versions']}.",f"- 버전 관문 exit {x['solver_gate']['exit']}. 신규 도장·이름 일치, 등록되지 않은 묶음 차단, 실행 모듈 버전 대조가 실행됐다.",f"- 저장 샤드 {sum(v['stamps'].values())}개 중 새 버전 도장 {len(v['new_shards'])}개. 원장 {v['ledger_rows']}행 중 새 버전 이름은 {v['ledger_new_version_rows']}행.",
 f"- 고도 표집률 반례: {[(r['case'],r['accepted_rows']) for r in x['altitude_main_cases'] if 'prf' in r['case']]}. 정상 합성 쌍은 수용했다.",
 f"- 복소 상관은 실수부·크기를 함께 반환한다. 주기 신호 반례의 결과는 {x['complex_lag_pair']}다. 기존의 신호 부재 결론을 내리는 문구는 내려갔다.",
 f"- 동시 발간 중 정리 함수 호출: 살아 있는 임시 파일 삭제 {x['orphan_cleanup_interleaving']['removed_active_temps']}개, 보존 {x['orphan_cleanup_interleaving']['kept_alive']}개. JSON과 글 모두 새 값으로 발간됐다.",
 f"- 실제 판독기 main {len(x['actual_reader_mains'])}개가 임시 출력에서 완료됐다. 장면·대역·고도는 생성 시각을 제외하고 발간 내용과 일치한다. 파형의 차이는 아래에 별도로 적었다.",
 f"- 추가 관문 종료값: { {k:r['exit'] for k,r in x['existing_gates'].items()} }. freeze 종료값 {x['freeze']['exit']}; 창고 수 증가가 보고됐다.",'',
 '## 새 결정 모드의 실제 CPU 대조','',f"조건: {cpu['variant']} · CPU {cpu['threads']}스레드 · 평판 {cpu['n_side']**2}장/삼각형 {cpu['triangles']}개 · 산란 계수 {cpu['scattering']} · 반송파 {cpu['fc_hz']/1e9:g} GHz. 솔버 입력은 원장 checks.cpu_modes.settings에 보존했다.",'',
 '| 결정 모드 | 반복별 경로 수 | 첫 반복 합산 전계 크기 | 반복별 정렬 경로 배열 해시 일치 |','|---|---|---:|---|']
 for r in cpu['rows']:
  obs=r['observations'];lines.append(f"| {r['deterministic']} | {[a['n_paths'] for a in obs]} | {obs[0]['h_abs']:.12g} | {len({a['sorted_path_sha256'] for a in obs})==1} |")
 lines+=['',f"결정 모드 켜기 전후 합산 전계 크기 차이는 {cpu['amplitude_change_db']:+.6f} dB다. 복소 전계 차이를 기본 모드 크기로 나눈 값은 {cpu['complex_relative_change']:.6f}다. 같은 버전 안에서 옵션만 바꾼 비교이며 드론 다리 큐의 예상 변화량이 아니다.",
 '기존에 저장된 구버전 CPU 결과와 경로 수는 비교할 수 있지만, 그 원장에는 같은 복소 전계 배열이 없어 버전 간 전계의 비트 일치까지 확인한 것은 아니다. 이번 반복은 한 스레드 조건이며 다중 스레드·GPU 재현성을 대신하지 않는다.',
 '공식 근거: [PathSolver API](https://nvlabs.github.io/sionna/rt/api/paths_solvers.html), [릴리스 노트](https://github.com/NVlabs/sionna-rt/releases/tag/v2.1.0).','',
 '## 보완할 점','']
 for i,f in enumerate(c['findings'],1):
  lines += [f"### {i}. {f['title']}",'',f"**분류: {f['kind']}**",'',f['evidence'],'',f"**수정 방향:** {f['fix']}",'',f"원장 키: `{f['result_key']}`",'']
  lines += [f"- [{s['path']}:{s['line']}](../{s['path']}) — `{s['quote']}`" for s in f['sources']];lines.append('')
 if 'mesh_gallery_known_issue' in x:
  g=x['mesh_gallery_known_issue'];bad=[r for r in g['rows'] if r['relative_error']>=g['tolerance']]
  lines+=['## 기존에 알려진 메쉬 갤러리 문제 재확인','',f"현재 메쉬로 다시 계산한 외접반경을 저장된 갤러리와 대조했다. 기체 {len(g['rows'])}종 중 허용 상대차 {g['tolerance']:.1%}를 넘는 것은 {len(bad)}종이다."]
  for r in bad:lines.append(f"- {r['drone']}: 저장 반경 {r['stored_radius_m']:.8f} m · 현재 반경 {r['current_radius_m']:.8f} m · 상대차 {r['relative_error']:.4%}.")
  lines+=['','이 문제는 메쉬 입력·기하 원장·보고서의 일치 문제로 별도 정정해야 한다. 이번 검사만으로 솔버 업그레이드가 원인이라고 판정하지 않는다. 기존 진단과 변경 계획은 [메쉬 갤러리 메모](MESH_GALLERY_STALE_0914.md)에 있다.','']
 lines+=['## 파형 발간에 추가될 구버전 행','',f"기존 {wf['old_count']}행 → 재실행 {wf['new_count']}행. 공통 행 변경 {len(wf['common_changed'])}개. 아래 행은 현재 발간물에 들어갈 자료이며, 이번 감사는 기존 발간물을 덮지 않고 비교 결과를 보존했다.",'','| 팔 | 앙각 | 표집률 Hz |','|---|---:|---:|']
 for r in wf['added']:lines.append(f"| {r['engine']} | {r['el_deg']:g} | {r['prf_hz']:g} |")
 lines+=['','## 다리 큐의 상태와 가치','',f"관측 {q['checked_utc']} (UTC). 발주 {q['n_jobs']}줄 = {q['n_cells']}칸, 팔 {q['n_arms']}개. 시작 {q['launched']}줄, 종료 {q['finished']}줄, 실패 종료 {q['failed']}줄.",q['last_status'],'',
 f"구버전 짝 존재 {sum(r['old_exists'] for r in q['jobs'])}/{q['n_jobs']}, n_dup 계측 존재 {sum(r.get('old_has_dup',False) for r in q['jobs'])}/{q['n_jobs']}. 읽은 구버전 짝의 배열·자세 분할·설정 오류 {sum(bool(r['errors']) for r in q['jobs'])}개. 구버전 짝 소요 합은 {q['old_worker_hours']:.5f} 일꾼시간이며 새 버전의 남은 시간 예측으로 확정하지 않는다.",
 '이 큐는 가치가 있다. 기존 자료를 보존하면서 스택 변경에 따른 차이를 같은 설정의 짝으로 잴 수 있다. 회절 비교를 제외한 것은 사용자가 새 버전에서만 회절을 쓰기로 한 결정과 맞는다. 현재 설계는 선택된 환경·스위치·깊이·앙각 표본이므로 모든 팔이나 회절의 새 모형 정확도로 일반화하지 않는다.',
 '완료 후에는 같은 칸의 복소 전계·DC/AC 전력·반환 경로 수·중복 경로 진단·상한 근접 여부를 함께 비교한다. 평균 크기가 같아도 자세별 위상이나 일부 경로 변화가 남을 수 있다. 결정 모드를 넣을 때는 기존 기본 모드 자료를 별도 이름으로 보존한다. 현재 다리의 단일 실행끼리의 차이에는 기본 모드의 실행별 차이도 포함될 수 있다. 같은 버전의 반복 결과를 함께 보존해 차이의 재현성을 확인한다. 그 반복을 광선 격자 민감도의 신뢰구간으로 부르지는 않는다.','',
 '## 문면에서 함께 낮출 표현','',
 '- 업그레이드 문서의 “동결 값이 움직이면 뜻은 하나, 버전 혼합”은 판정 규칙으로 과하다. 새 구버전 자료 편입·선택 규칙·판독기 수정·미완결 자료 완성도 변화 원인이므로 행과 입력 출처를 추적해야 한다.',
 '- 도장 없음과 알려진 도장이 섞인 것은 출처 기록의 혼합이다. 실제 서로 다른 솔버 판을 사용했다고 입증된 상태와 구별한다.',
 '- 고도 판독기의 “로터 반응이면 두 지연 모두 상관이 서야 한다”는 설명은 신호 모델의 추가 가정을 요구한다. 서로 다른 로터 속도·위상·성분이 섞이는 상황에서는 상관 통계를 관측량으로 기술하는 것이 안전하다.','',
 '## 범위와 재현','',f"운영 입력·발간물 내용 변화 감시: {x['protected_changes']}. 소스 해시 변화: {x['source_changes']}. 인용 {x['source_quotes_verified']}건을 줄과 문자로 확인했다.",
 '운영 큐·설치 환경·생산 코드는 변경하지 않았다. 새 감사 생성기·원장·Markdown·Jupyter를 남겼다. 이번 전체 창고 검사는 버전 도장과 이름에 초점을 뒀으며 모든 과거 배열의 CRC를 다시 전수 검사한 것은 아니다. 새 버전 연기 시험과 구버전 다리 짝은 배열도 확인했다. 실기 정확도의 확인은 이번 범위 밖이다.','',
 '```bash',f'{sys.executable} benchmark/review_upgrade_0914.py','```','',
 '검사 캐시에서 문서만 다시 생성할 때는 --publish를 붙인다. 외부 문서 관측 날짜는 external_sources에 기록했다.']
 OUT.write_text(json.dumps(c,ensure_ascii=False,indent=1,allow_nan=False)+'\n');MD.write_text('\n'.join(lines)+'\n')
 from report_style import header,md,next_steps,build_notebook
 cells=[header(num='업그레이드 점검',title='버전 분리와 결정 모드 대조',did='설치·저장 도장·실제 판독기와 CPU 결정 모드를 대조했다.',results=[f"솔버 관문 종료 {x['solver_gate']['exit']} ⟨{j} : checks.solver_gate⟩.",f"기본 모드·결정 모드 {len(cpu['rows'])}조건 대조 ⟨{j} : checks.cpu_modes⟩.",f"구버전 다리 짝 {q['n_jobs']}개 확인 ⟨{j} : checks.bridge⟩."],method=[('격리','CPU 한 코어·임시 출력의 합성 반례와 실제 main'),('근거','설치 API·소스·원장·샤드와 감독자 로그')],repro=dict(cmd=[f'{sys.executable} benchmark/review_upgrade_0914.py'],out=[j],runtime='CPU 한 코어·저장 자료 읽기'))]
 for i,f in enumerate(c['findings']):cells.append(md(f"## {f['title']}",'',f['kind'],'',f"[재현과 수정 방향](UPGRADE_REVIEW_0914.md) ⟨{j} : findings[{i}]⟩"))
 cells.append(next_steps([('현재 다리 큐 결과를 같은 조건의 구버전 짝과 비교한다','스택 변경에 따른 차이','UPGRADE_REVIEW_0914.md'),('결정 모드를 별도 이름과 도장으로 연결한다','옵션 변경 효과와 버전 효과의 분리','UPGRADE_REVIEW_0914.md'),('사후 도장 검사와 대조군 기준 선택을 보완한다','자료 수용·거절의 일관성','UPGRADE_REVIEW_0914.md')]))
 build_notebook(str(NB),cells,strict=True);print('published',len(c['findings']),flush=True)

def gallery_check():
 c=read();G=base.js('outputs/mesh_gallery.json');target=old.loadmod('src/make_report02_target.py')
 import drones
 rows=[]
 for key in target.DRONE_ORDER:
  mesh=drones.build_drone(drones.DRONES[key]);now=target._enclosing_radius(mesh);stored=G['airframes'][key]['r_encl_m']
  rows.append(dict(drone=key,stored_radius_m=stored,current_radius_m=now,relative_error=abs(stored-now)/now))
 c['checks']['mesh_gallery_known_issue']=dict(rows=rows,tolerance=.005,max_relative_error=max(r['relative_error'] for r in rows))
 save(c)

if __name__=='__main__':
 if '--publish' in sys.argv:publish()
 else:setup();corrected();cpu_modes();gate_adversaries();extra();queue_snapshot();gallery_check();publish()
