"""Current-state and outdoor-kernel audit; CPU one core, own outputs only.
Run: /workspace/.venvs/py312/bin/python benchmark/review_kernel_outdoor_0915.py
The flat-plate test checks the implemented scalar integral, not measured RF truth.
"""
from __future__ import annotations
import os
for k,v in {'CUDA_VISIBLE_DEVICES':'','SIONNA2_ALLOW_CPU':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}.items(): os.environ[k]=v
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import hashlib,json,re,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'benchmark')]
OUT=ROOT/'outputs/kernel_outdoor_review_0915.json'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pack(v):return [float(complex(v).real),float(complex(v).imag)]
def load(p):
 with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main():
 from importlib.metadata import version
 d={'_meta':{'generator':'benchmark/review_kernel_outdoor_0915.py','command':f'{sys.executable} benchmark/review_kernel_outdoor_0915.py','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'versions':{p:version(p) for p in ['sionna','sionna-rt','mitsuba','drjit']},'scope':'Source audit, saved-shard recalculation, CPU synthetic geometry; no RF measurements.'},'checks':{},'source_hashes':{}}
 def checkpoint():OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 sources=['src/rcs_sbr.py','src/materials.py','benchmark/elevation_sweep_md.py','benchmark/report15_probe.py','runners/jobs_0933_repeat.txt','runners/jobs_0934_bridge2.txt','runners/jobs_0935_detmode.txt','runners/jobs_0936_attrib.txt','runners/worker_supervisor.py']
 for p in sources:d['source_hashes'][p]=digest(ROOT/p)
 c=d['checks'];shd=ROOT/'outputs/elev_sweep_shards'
 previous=json.loads((ROOT/'outputs/upgrade_review_0914.json').read_text())['checks']['bridge']['jobs']
 groups={}
 for j in previous:
  key=(j['old_arm'],j['new_arm'],j['el']);groups.setdefault(key,[]).append(j)
 bridge=[]
 for (oa,na,el),jobs in sorted(groups.items()):
  merged=[];builds=[];files=[];errs=[]
  for arm in (oa,na):
   zs=[]
   for j in sorted(jobs,key=lambda j:j['shard']):
    p=shd/f"{arm}_el{el:+g}_{j['shard']:02d}.npz";z=load(p);zs.append(z);files.append(str(p.relative_to(ROOT)));d['source_hashes'][str(p.relative_to(ROOT))]=digest(p)
    if not np.array_equal(z['idx'],np.arange(int(z['meta'][1]),int(z['meta'][3]),int(z['meta'][2]))):errs.append('partition')
   idx=np.concatenate([z['idx'] for z in zs]);order=np.argsort(idx)
   if not np.array_equal(idx[order],np.arange(int(zs[0]['meta'][3]))):errs.append('coverage')
   merged.append({k:np.concatenate([z[k] for z in zs])[order] for k in ['E','E_dedup','n_dup','nret']})
   builds.append(sorted({str(z.get('solver_build','unrecorded')) for z in zs}))
   if arm==oa:oldmeta=[z['meta'][:5] for z in zs];oldcfg=[z['cfg'] for z in zs]
   else:
    for a,b,x,y in zip(oldmeta,[z['meta'][:5] for z in zs],oldcfg,[z['cfg'] for z in zs]):
     if not np.array_equal(a,b) or not np.array_equal(x,y[:len(x)],equal_nan=True):errs.append('settings')
  x,y=merged;row={'old_arm':oa,'new_arm':na,'el_deg':el,'files':files,'builds':builds,'errors':errs}
  for k in ['E','E_dedup']:
   a,b=x[k],y[k];aa=a-a.mean();bb=b-b.mean()
   row[k]={'rms_change_db':float(20*np.log10(np.linalg.norm(b)/np.linalg.norm(a))),'ac_rms_change_db':float(20*np.log10(np.linalg.norm(bb)/np.linalg.norm(aa))),'complex_relative_l2':float(np.linalg.norm(b-a)/np.linalg.norm(a)),'exact_equal':bool(np.array_equal(a,b))}
  row['dup_changed_poses']=int(np.count_nonzero(x['n_dup']!=y['n_dup']));bridge.append(row)
 c['bridge']=bridge
 reps=[]
 for p in sorted(shd.glob('*_rep*_rt210_*.npz')):
  base=p.with_name(re.sub(r'_rep\d+','',p.name));a,b=load(base),load(p)
  reps.append({'file':p.name,'baseline':base.name,'n':len(b['E']),'E_equal':bool(np.array_equal(a['E'],b['E'])),'dedup_equal':bool(np.array_equal(a['E_dedup'],b['E_dedup'])),'idx_equal':bool(np.array_equal(a['idx'],b['idx'])),'cfg_equal':bool(np.array_equal(a['cfg'],b['cfg'],equal_nan=True)),'build_equal':str(a['solver_build'])==str(b['solver_build'])})
  d['source_hashes'][str(p.relative_to(ROOT))]=digest(p)
 c['repeats']=reps
 c['new_shards']=[p.name for p in sorted(shd.glob('*_rt210_*.npz'))]
 c['provenance_files']=[p.name for p in (ROOT/'outputs/path_provenance').glob('*.npz')]
 L=json.loads((ROOT/'outputs/elevation_sweep_md.json').read_text());c['ledger']={'rows':len(L['rows']),'rt210_rows':sum('_rt210_' in r['engine'] for r in L['rows'])}
 procs=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:a=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
  except OSError:continue
  if len(a)>1 and Path(a[0]).name.startswith('python') and Path(a[1]).name in ['worker_supervisor.py','elevation_sweep_md.py']:procs.append({'pid':int(p.name),'args':a})
 c['processes']=procs
 c['queue_logs']={}
 for name in ['bridge_0931','repeat_0933','bridge2_0934','detmode_0935','attrib_0936','canyon_0937']:
  p=ROOT/f'runners/logs/sup_{name}.log'
  if p.exists():
   lines=p.read_text().splitlines();finish=re.findall(r'끝 pid=(\d+) gpu=\d+ rc=(\d+)', '\n'.join(lines))
   c['queue_logs'][name]={'tail':lines[-2:],'completed':len(finish),'failed':sum(rc!='0' for _,rc in finish)}
 n=8192;prf=19700.;selected=[];by=[]
 for sh in range(2):
  idx=np.arange(sh,n,2);sel=np.linspace(0,len(idx)-1,64).round().astype(int);poses=idx[sel];selected.extend(poses.tolist());by.append({'shard':sh,'unique_gaps_poses':np.unique(np.diff(poses)).tolist(),'mean_rate_hz':float(63*prf/(poses[-1]-poses[0]))})
 c['dump_sampling']={'n_poses':n,'prf_hz':prf,'per_shard':by,'combined_count':len(selected),'combined_gaps':np.unique(np.diff(sorted(selected))).tolist(),'uniform_sampling':len(np.unique(np.diff(sorted(selected))))==1,'span_seconds':(max(selected)-min(selected))/prf,'flash_hz':126.66666666666667}
 checkpoint();print('saved shard and queue recalculation',flush=True)
 import mitsuba as mi
 import sionna.rt as rt
 mi.set_variant('llvm_ad_mono_polarized')
 sc=rt.load_scene(rt.scene.simple_street_canyon)
 names=list(sc.objects);ids=[int(sc.objects[n].object_id) for n in names]
 c['object_ids']={'scene':'simple_street_canyon','names':names,'ids':ids,'ids_equal_name_indices':ids==list(range(len(names))),'id_outside_name_array':sum(x>=len(names) for x in ids),'installed_scene_object_sha256':digest(Path(rt.__file__).parent/'scene_object.py')}
 print('object IDs',c['object_ids'],flush=True)
 import rcs_sbr as ks
 from rcs_po import _plate_mesh
 mesh=_plate_mesh(.25);gm={g:1.0 for g in set(mesh.g)};fc=3.5e9;lam=ks.C0/fc
 ui=np.array([0.,0.,1.]);us=np.array([np.sqrt(3)/2,0,.5]);rows=[]
 # A common fixed support per spacing avoids direction-dependent bbox changes.
 for div in [12,24,48,96]:
  spacing=lam/div;grid=ks.grid_ref_from([mesh],fc,spacing=spacing)
  ab=ks.sbr_field_bistatic(mesh,gm,fc,ui,us,spacing=spacing,grid_ref=grid,penetrate=False)
  ba=ks.sbr_field_bistatic(mesh,gm,fc,us,ui,spacing=spacing,grid_ref=grid,penetrate=False)
  integ=.25**2*np.sinc((.25/lam)*(ui[0]+us[0]))
  rows.append({'div':div,'E_ab':pack(ab),'E_ba':pack(ba),'magnitude_ratio':abs(ab)/abs(ba),'relative_symmetric_error':abs(ab-ba)/((abs(ab)+abs(ba))/2),'integral_ab':float(integ*ui[2]),'integral_ba':float(integ*us[2])})
 c['plate_reciprocity']={'side_m':.25,'fc_hz':fc,'theta_i_deg':0,'theta_s_deg':60,'gamma':1.,'ptd':False,'range':'plane wave','rows':rows,'continuum_ratio':2.0,'interpretation':'The current projected-area scalar formula converges to cos(theta_i)/cos(theta_s), not unity in this test. This is an implementation/approximation check, not RF validation.'}
 checkpoint();print('plate reciprocity',rows,flush=True)
 # Execute precisely the production memory-query choice with mocked nvidia-smi output.
 import ast,types
 src=(ROOT/'benchmark/elevation_sweep_md.py').read_text();tree=ast.parse(src)
 target=next(n for n in ast.walk(tree) if isinstance(n,ast.Try) and any(isinstance(t,ast.Constant) and isinstance(t.value,str) and 'nvidia-smi --query-gpu=memory.total,memory.used' in t.value for t in ast.walk(n)))
 from unittest.mock import patch
 fake=types.SimpleNamespace(stdout='97280, 1000\n97280, 92000\n')
 scope={'_free_gib':None}
 with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'1'}),patch('subprocess.run',return_value=fake):exec(compile(ast.Module(body=[target],type_ignores=[]),'<production-memory-query>','exec'),scope)
 c['memory_query']={'mock_cuda_visible_devices':'1','gpu0_free_gib':(97280-1000)/1024,'gpu1_free_gib':(97280-92000)/1024,'selected_by_production_gib':scope['_free_gib'],'note':'Mock output exercises production AST; no live GPU memory fault induced.'}
 d['_meta']['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());checkpoint()
 print('saved',OUT,flush=True)


def supplementary():
 import contextlib,io,tempfile,types
 from unittest.mock import patch
 import review_upgrade_0914 as old
 d=json.loads(OUT.read_text());c=d['checks']
 with patch.object(old,'read',lambda:d),patch.object(old,'save',lambda x:None):old.gate_adversaries()
 # Reuse the real main test but align the synthetic baseline stamp to today's ledger.
 # Its outputs and synthetic shards live in TemporaryDirectory; it never calls a solver.
 import inspect
 text=inspect.getsource(old.before.altitude_cases)
 text=text.replace("build='test-old'", "build=rr.get('solver_build') or 'test-old'")
 ns=dict(old.before.__dict__);ns['read']=lambda:d;ns['save']=lambda x:None
 exec(text,ns);ns['altitude_cases']()
 c.pop('orphan_cleanup_interleaving',None) # Old adapter assumes old cleanup return schema.
 for r in c['bridge']:
  values=[]
  for arm in [r['old_arm'],r['new_arm']]:
   zs=[load(ROOT/f"outputs/elev_sweep_shards/{arm}_el{r['el_deg']:+g}_{i:02d}.npz") for i in range(2)]
   values.append(np.concatenate([z['E'] for z in zs])[np.argsort(np.concatenate([z['idx'] for z in zs]))])
  a,b=values;z=np.vdot(a,b);phase=z/abs(z)
  r['phase_deg']=float(np.degrees(np.angle(z)));r['phase_aligned_relative_l2']=float(np.linalg.norm(b-phase*a)/np.linalg.norm(a))
  r['ac_complex_relative_l2']=float(np.linalg.norm((b-b.mean())-(a-a.mean()))/np.linalg.norm(a-a.mean()))
 for r in c['repeats']:
  a,b=[load(ROOT/'outputs/elev_sweep_shards'/r[k]) for k in ['baseline','file']];x,y=a['E'],b['E']
  r.update(changed_samples=int(np.count_nonzero(x!=y)),complex_relative_l2=float(np.linalg.norm(y-x)/np.linalg.norm(x)),rms_change_db=float(20*np.log10(np.linalg.norm(y)/np.linalg.norm(x))),cfg_lengths=[len(a['cfg']),len(b['cfg'])],cfg_shared_prefix_equal=bool(np.array_equal(a['cfg'][:min(len(a['cfg']),len(b['cfg']))],b['cfg'][:min(len(a['cfg']),len(b['cfg']))],equal_nan=True)))
 c['coherent_attribution_example']={'group_fields':[[1,0],[-.9,0]],'sum_group_powers':1+.9**2,'total_power':abs(1-.9)**2,'cross_term':-1.8,'note':'Algebraic counterexample; not a production measurement.'}
 c['queued_chain_scripts']=[]
 for p in Path('/proc').iterdir():
  try:a=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
  except (OSError,NotADirectoryError):continue
  if len(a)==2 and Path(a[0]).name=='bash' and re.search(r'/chain[234]\.sh$',a[1]):
   f=Path(a[1]);c['queued_chain_scripts'].append({'pid':int(p.name),'observed_path':str(f),'source':f.read_text(),'sha256':digest(f)})
 m=old.old.loadmod('benchmark/read_wfsurvive_0912.py');choose=old.base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation']
 esm=types.SimpleNamespace(SHD=str(ROOT/'outputs/elev_sweep_shards'),one_generation=choose)
 published=json.loads((ROOT/'outputs/read_wfsurvive_0912.json').read_text())
 with tempfile.TemporaryDirectory() as td,patch.object(m,'OUT',str(Path(td)/'out.json')),patch.object(m,'MD',str(Path(td)/'out.md')),patch.object(m,'prod',lambda:esm),contextlib.redirect_stdout(io.StringIO()):
  m.main();fresh=json.loads((Path(td)/'out.json').read_text())
 by=lambda rows:{(r['engine'],r['el_deg']):r for r in rows};a,b=by(published['rows']),by(fresh['rows'])
 c['wf_publication']={'published_rows':len(a),'fresh_rows':len(b),'published_input_rows':published['_meta']['n_ledger_rows'],'fresh_input_rows':fresh['_meta']['n_ledger_rows'],'added':sorted(set(b)-set(a)),'removed':sorted(set(a)-set(b)),'changed_common':sum(a[k]!=b[k] for k in set(a)&set(b))}
 c['gates']={}
 for name in ['check_solver_build','check_reader_gate','check_arm_names','check_new_file_rules','check_report_links','check_row_pointers']:
  p=subprocess.run([sys.executable,f'benchmark/{name}.py'],cwd=ROOT,text=True,capture_output=True,timeout=150)
  c['gates'][name]={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr};print(name,p.returncode,flush=True)
 d['source_hashes']['benchmark/review_kernel_outdoor_0915.py']=digest(__file__)
 d['_meta']['supplementary_finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')



def path_id_probe():
 import mitsuba as mi
 import sionna.rt as rt
 mi.set_variant('llvm_ad_mono_polarized')
 sc=rt.load_scene(rt.scene.simple_street_canyon)
 sc.tx_array=rt.PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
 sc.rx_array=rt.PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
 sc.add(rt.Transmitter('audit_tx',position=[0,0,1]));sc.add(rt.Receiver('audit_rx',position=[2,0,1]))
 p=rt.PathSolver()(sc,max_depth=1,samples_per_src=10000,max_num_paths_per_src=10000,los=True,specular_reflection=True,diffuse_reflection=False,refraction=False,diffraction=False,seed=1)
 ids=np.unique(np.asarray(p.objects));valid=ids[ids!=4294967295]
 mapping={int(o.object_id):name for name,o in sc.objects.items()}
 d=json.loads(OUT.read_text());d['checks']['path_id_probe']={'scene':'simple_street_canyon','tx':[0,0,1],'rx':[2,0,1],'samples_per_src':10000,'max_depth':1,'object_mapping':mapping,'returned_valid_ids':valid.tolist(),'all_map_to_actual_ids':all(int(x) in mapping for x in valid),'naive_name_array_out_of_bounds':sum(int(x)>=len(mapping) for x in valid),'n_paths':int(np.asarray(p.tau).size)}
 OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(d['checks']['path_id_probe'],flush=True)



def publish():
 from report_style import header,md,next_steps,build_notebook
 d=json.loads(OUT.read_text());c=d['checks'];findings=[]
 def src(path,needle):
  p=ROOT/path;lines=p.read_text().splitlines();ix=next(i for i,s in enumerate(lines) if needle in s)
  return {'path':path,'line':ix+1,'quote':lines[ix].strip(),'sha256':digest(p)}
 def add(title,grade,body,fix,key,refs):
  findings.append({'id':len(findings)+1,'title':title,'grade':grade,'observation':body,'suggestion':fix,'evidence_key':key,'sources':[src(*r) for r in refs]})
 oid=c['object_ids'];probe=c['path_id_probe'];sampling=c['dump_sampling'];plate=c['plate_reciprocity'];last=plate['rows'][-1]
 add('경로 출처의 물체 ID와 이름 순번이 다르다','우선 수정 · 실제 설치본 재현',
 f"새 생산 코드는 마지막 장면의 이름 목록만 저장하고 obj가 그 순번이라고 설명한다. CPU 기본 협곡 장면의 이름 {len(oid['names'])}개에 대한 실제 ID는 {oid['ids']}였다. 실제 PathSolver 시험에서도 반환 ID {probe['returned_valid_ids']}가 나왔고, 이름 배열 범위를 넘는 ID가 {probe['naive_name_array_out_of_bounds']}개였다. 범위 안인 ID도 실제 object_id 사전으로 매핑해야 한다. 검사 시점 운영 provenance 파일은 {len(c['provenance_files'])}개였다.",
 '각 자세에서 {int(object.object_id): 안정적인 이름/부위 번호}를 만들어 obj를 변환한 뒤 저장한다. 자세마다 장면이 재생성되는 경우에는 그 자세의 매핑을 보존해야 한다. 무효 ID와 미등록 ID를 구분하고 prim을 못 읽었을 때는 0 대신 누락 상태를 기록한다. 원본 경로와 이름 변환 결과를 함께 대조하는 작은 시험부터 통과시킨다.',
 'checks.object_ids / checks.path_id_probe',[('benchmark/elevation_sweep_md.py','_names = [str(nm)'),('benchmark/elevation_sweep_md.py','object_names 의 번호가 obj 값이다'),('benchmark/report15_probe.py','return {int(o.object_id)')])
 add('경로 저장 간격과 도플러 분석 시간축이 다르다','설계 범위 · 표본 위치 재계산',
 f"현재 발주 조건 n={sampling['n_poses']}·PRF={sampling['prf_hz']:g} Hz·샤드 둘에서 --dump-paths 64는 샤드마다 원래 자세 {sampling['per_shard'][0]['unique_gaps_poses']}개 간격으로 저장한다. 샤드별 유효 표집률은 {sampling['per_shard'][0]['mean_rate_hz']:.6f} Hz, 나이퀴스트는 그 절반이다. 기준 날개 통과율 {sampling['flash_hz']:.6f} Hz도 그 범위를 넘는다. 두 샤드를 합친 {sampling['combined_count']}개 자세의 간격은 {sampling['combined_gaps']}로 불균일하다. 이 자료를 19,700 Hz 연속 시계열로 FFT하면 시간축이 달라진다.",
 '드문 전체 경로 덤프는 선택 자세의 경로 구조를 살피는 용도로 둔다. 부위별 스펙트럼에는 모든 자세의 부위별 복소 합과 경로 개수만 작게 저장한다. 같은 창·같은 시간축에서 부위별 STFT를 계산하고 합한 복소장이 원본 E와 일치하는지 검사한다.',
 'checks.dump_sampling',[('benchmark/elevation_sweep_md.py','_sel = np.linspace(0, idx.size'),('runners/jobs_0936_attrib.txt','스펙트럼의 각 줄')])
 add('반복의 표시값 0을 다른 조건의 재실행 동일성으로 확대했다','해석·덮어쓰기 근거 정정',
 f"같은 버전 반복 샤드 {len(c['repeats'])}개를 원본과 맞대면 E의 배열 동일성은 {sum(r['E_equal'] for r in c['repeats'])}개였다. 빈 하늘·실외 일부의 차이는 부동소수점 마지막 자릿수 수준이다. 지면 반복 두 샤드의 복소 상대 L2 차이는 {max(r['complex_relative_l2'] for r in c['repeats']):.3e}까지였다. RMS dB를 다섯 자리로 반올림하면 0으로 보이는 것과 배열 동일성은 다르다. cfg 길이가 다른 쌍은 새 결정 모드 도장 칸 추가이며, 공통 접두부 값은 모두 같았다.",
 '문구를 “검사한 반복 조건에서 RMS 레벨 차이가 표시 정밀도 아래였다”로 좁힌다. 추가 앙각·건물·협곡의 재현성은 해당 조건의 반복으로 확인해야 한다. --overwrite 대신 별도 재실행 식별자 또는 진단 전용 출력 경로를 마련해 비교 원본을 보존한다.',
 'checks.repeats',[('runners/jobs_0934_bridge2.txt','흔들림이 0 이므로'),('runners/jobs_0936_attrib.txt','E 는 같은 값이 나온다')])
 free=next(r for r in c['bridge'] if '_env' not in r['new_arm'] and r['new_arm'].endswith('_d2'))
 example=next(r for r in c['bridge'] if '_envoutdoor01_mfix' in r['new_arm'] and r['new_arm'].endswith('_d1') and r['el_deg']==-30)
 add('버전 비교의 빈 하늘 설명과 복소장 요약을 보완해야 한다','저장 원자료 독립 재계산',
 f"12쌍의 RMS 레벨 차이 범위 {min(r['E']['rms_change_db'] for r in c['bridge']):+.7f}~{max(r['E']['rms_change_db'] for r in c['bridge']):+.7f} dB는 재현했다. 그러나 빈 하늘 깊이 2·el {free['el_deg']:g}°에서도 {free['E']['rms_change_db']:+.7f} dB였다. “0이 아닌 칸은 환경 장면에만 있었다”는 발주서 설명과 다르다. 실외 outdoor01 깊이 1·el −30°의 레벨 차이는 {example['E']['rms_change_db']:+.7f} dB지만 전체 복소장의 최적 공통 위상차는 {example['phase_deg']:.5f}°였다. 위상을 맞춘 상대 L2 잔차는 {example['phase_aligned_relative_l2']:.6f}, 맞추기 전은 {example['E']['complex_relative_l2']:.6f}다. 이 쌍의 평균 제거 AC도 부호 차이가 나타난다.",
 'RMS 레벨·평균 제거 AC 레벨·복소 위상·위상 정렬 후 잔차를 함께 기록한다. 공통 위상은 단독 파워 스펙트럼에는 영향을 주지 않지만 기준 채널이나 다른 경로와의 결맞은 합에서는 중요하다. 앙각 −30° 해당 조건의 동일 버전 반복과 경로별 계수·지연 비교로 원인을 좁힌다. 현 차이는 패키지 묶음 전환 전후의 관측이다. Sionna 단독 변경이나 물리 개선으로 귀속하려면 별도 대조가 필요하다.',
 'checks.bridge',[('runners/jobs_0934_bridge2.txt','빈 하늘은 6 칸'),('runners/SOLVER_BUILDS.json','_rt210')])
 add('결정 모드 메모리 검사가 할당된 GPU 대신 첫 GPU를 읽는다','잠재 운영 결함 · 생산 구문 반례',
 f"감독자는 CUDA_VISIBLE_DEVICES로 GPU를 지정한다. 새 사전 검사는 nvidia-smi 결과 중 _o[0]을 택한다. 생산 구문에 GPU 0 여유 {c['memory_query']['gpu0_free_gib']:.3f} GiB·GPU 1 여유 {c['memory_query']['gpu1_free_gib']:.3f} GiB인 응답을 넣으면 {c['memory_query']['selected_by_production_gib']:.3f} GiB를 반환했다. 지정 카드가 GPU 1인 상황에서 다른 카드의 여유를 기준으로 삼게 된다. 이는 운영 장애 재현과 구분되는 합성 응답 검사다.",
 '워커가 사용 중인 물리 GPU UUID를 확인한 뒤 nvidia-smi -i로 조회한다. 조회 실패는 계측 불가 상태로 반환해야 한다. 60 byte/원소 추정은 실측 최대 메모리와 안전 여유로 보정하고, 동시 워커의 예약량까지 감독자와 공유한다. 0935의 켬·끔 짝은 같은 광선 예산으로 유지한다.',
 'checks.memory_query',[('benchmark/elevation_sweep_md.py','_t, _u = [int(x) for x in _o[0]'),('runners/worker_supervisor.py','CUDA_VISIBLE_DEVICES=str(gpu)')])
 add('후속 큐 대기 조건에 선행 실행 식별자가 필요하다','운영 경쟁 가능성 · 실행 중 스크립트 확인',
 f"검사 시점 대기 중인 chain2/3/4 스크립트 {len(c['queued_chain_scripts'])}개를 /proc의 실제 bash 인자로 확인했다. chain2는 워커 수 0, chain3와 chain4는 감독자·워커 수 0이 두 번 이어지는 조건을 쓴다. chain3와 chain4의 조건이 같아, 선행 실행 이름과 무관하게 동시에 자격을 얻을 수 있다. 감독자 파일의 단일 실행 잠금도 보완 대상이다. 이 지적의 근거는 현재 대기 조건의 경쟁 가능성까지다.",
 '한 실행기가 0934 완료 → 0935 완료 → 0936 완료 → 0937 완료를 명시적으로 기다리게 한다. rc와 완료 샤드를 확인하고 실패 상태를 전달한다. 잠금은 실제 감독자 시작까지 원자적으로 잡는다. 현재 살아 있는 워커는 유지하면서 다음 실행 예약을 정리하는 순서가 적절하다.',
 'checks.queued_chain_scripts',[('runners/worker_supervisor.py','def launch(self, gpu, line)')])
 add('지면 커널의 비대칭에는 방향 가중치도 관여한다','커널 식·평판 수치 반례',
 f"지면 주석은 “이것은 이산화 오차다 — 격자를 촘촘히 하면 준다”고 적는다. 실제 스칼라 바이스태틱 함수로 정사각 평판 {plate['side_m']:g} m·{plate['fc_hz']/1e9:g} GHz·입사각 {plate['theta_i_deg']}°/출사각 {plate['theta_s_deg']}°·Γ=1·평면파·투과/PTD 끔을 검사했다. 방향을 교환한 크기 비는 div 12/24/48/96에서 {[round(r['magnitude_ratio'],6) for r in plate['rows']]}였다. λ/96에서도 {last['magnitude_ratio']:.6f}배다. 현재 식의 연속 투영면 적분도 cos(0°)/cos(60°)=2를 준다. 이 예에서는 격자 세분 후에도 방향 가중치 차이가 남는다. 기존 드론 사다리에서 오차가 줄어든 관찰 자체와 그 원인·일반화는 구별해야 한다.",
 '지면 합에서 생략한 E(직접,지면)도 계산하여 E_dd + w E_dg + w E_gd + w² E_gg로 비교한다. 이것은 한 방향을 두 배 하는 근사를 제거하는 조치다. 바이스태틱 스칼라/벡터 산란식의 상호성·편파 정의는 별도로 검토한다. 대칭화 조치의 물리 타당성은 별도 기준해와 대조해야 한다.',
 'checks.plate_reciprocity',[('src/rcs_sbr.py','이것은 이산화 오차다'),('src/rcs_sbr.py','Etot = complex(E) * d * d'),('src/rcs_sbr.py','return complex(E_dd) + 2.0')])
 add('부위별 경로 전력과 수신 복소장 기여의 정의가 필요하다','새 분석을 위한 해석 계약',
 '0936의 camera 66.6%라는 “되돌아온 전력” 표기에는 분모·합산 규약을 추가해야 한다. 원본 E는 a·exp(−j2πfcτ)의 결맞은 합이다. 경로별 |a|² 비율은 비결맞은 경로 전력 분율이고, 수신 |Σa·exp(−j2πfcτ)|²의 부위별 가산 분율과 다르다. 합성 예 H1=1, H2=−0.9에서 두 부위 전력 합은 1.81, 총 전력은 0.01, 교차항은 −1.8이다. 원장의 camera 비율을 거짓이라고 재판정한 것이 아니라 아직 확인되지 않은 계산 정의를 지적한 것이다.',
 '기준 출력을 환경만 거친 경로·표적만 거친 경로·환경과 표적을 모두 거친 경로로 중복 없이 분리한다. 각 범주의 복소 시계열을 합하면 원본 E가 되게 한다. 부위 이름을 여러 번 맞은 경로는 접촉 순서 전체를 범주로 두거나 배분 규칙을 명시한다. 스펙트럼 전력 합에는 부위 사이 교차항도 따로 낸다.',
 'checks.coherent_attribution_example',[('runners/jobs_0936_attrib.txt','camera 66.6'),('benchmark/elevation_sweep_md.py','_t = aa[hit] * np.exp')])
 d['findings']=findings
 d['external_sources']=[{'url':'https://nvlabs.github.io/sionna/rt/tech-report/S1.html','checked':'2026-09-15','use':'채널 계수·안테나·편파 행렬·거리 감쇠와 결맞은/비결맞은 합의 정의'},{'url':'https://nvlabs.github.io/sionna/rt/api/paths_solvers.html','checked':'2026-09-15','use':'결정 모드 기본값과 고정 씨앗의 재현성 범위'},{'url':'https://nvlabs.github.io/sionna/rt/api/paths.html','checked':'2026-09-15','use':'경로 객체 ID 및 경로별 정보의 API 계약'}]
 d['checks']['source_changed_during_audit']=[p for p,h in d['source_hashes'].items() if p!='benchmark/review_kernel_outdoor_0915.py' and (ROOT/p).exists() and digest(ROOT/p)!=h]
 d['source_hashes']['benchmark/review_kernel_outdoor_0915.py']=digest(__file__)
 d['_meta']['report_generated_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
 OUT.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
 lines=['# 현재 상태와 커널의 실외 적용 검토','',f"검사 시작 {d['_meta']['started_utc']} · 보고 생성 {d['_meta']['report_generated_utc']} · HEAD `{d['_meta']['head']}`.",'',
 '범위: 최신 버전 전환 비교·반복 원자료, 새 경로 출처 기록, 결정 모드 메모리 검사, 후속 큐 예약, 생산 커널의 바이스태틱·지면 함수. 저장소 전체의 모든 실험을 다시 실행한 감사와는 범위가 다르다. CPU 한 코어로 읽기 전용 검산을 수행했다. 새 감사 코드·원장·문서·노트북을 남겼다.','',
 '실행 중 다른 작업이 환경 이름 사전 검사 35줄을 생산 코드에 추가한 것도 확인했다. 협곡 인자의 콜론 오타 수정은 진행 중인 작업으로 구분한다. 아래 지적의 인용은 보고 생성 시점의 소스 줄과 해시로 다시 연결했다. 원장 source_changed_during_audit가 읽는 도중 바뀐 파일을 기록한다.','',
 '## 확인된 수정과 현재 상태','',
 f"설치 묶음: {d['_meta']['versions']}. 검사한 관문 {len(c['gates'])}개의 종료값은 {[v['exit'] for v in c['gates'].values()]}이다. ⟨outputs/kernel_outdoor_review_0915.json : checks.gates⟩",'',
 '도장 검사에 정상 묶음·틀린 DrJit·필수 의존성 누락을 다시 넣었을 때 오류 수는 0·1·1이었다. 고도 판독기의 실제 main은 정상 합성 비교를 수용하고, 실제 표집률 불일치·원장 표집률 불일치·같은 칸의 버전 혼합·쌍의 버전 차이는 각각 거절했다. 거절 행의 순서를 바꿔도 대역 비교의 기준 PRF와 결과가 같았다. ⟨outputs/kernel_outdoor_review_0915.json : checks.altitude_main_cases⟩','',
 f"파형 실제 main을 임시 출력에서 다시 실행한 결과 {c['wf_publication']['fresh_rows']}행이며 기존 {c['wf_publication']['published_rows']}행과 공통 숫자가 같다. 입력 행 수 메타데이터는 {c['wf_publication']['published_input_rows']}→{c['wf_publication']['fresh_input_rows']}로 갱신 대상이다. 기존 숫자 발간은 이번 재계산과 일치했다. ⟨outputs/kernel_outdoor_review_0915.json : checks.wf_publication⟩",'',
 f"스냅샷에서 rt210 샤드는 {len(c['new_shards'])}개, 주 원장은 {c['ledger']['rows']}행 중 rt210 {c['ledger']['rt210_rows']}행이다. 이 수는 실행 중인 큐의 한 시점 기록이다. ⟨outputs/kernel_outdoor_review_0915.json : checks.ledger⟩",'',
 '## 수정·보완할 항목','']
 for f in findings:
  lines += [f"### {f['id']}. {f['title']}",'',f"**{f['grade']}**",'',f['observation'],'',f"권장 조치: {f['suggestion']}",'',f"검산: ⟨outputs/kernel_outdoor_review_0915.json : {f['evidence_key'].split(' / ')[0]}⟩",'',
   '근거: '+' · '.join(f"[{s['path']}:{s['line']}](../{s['path']}#L{s['line']})" for s in f['sources']), '']
 lines += ['## 우리 커널을 실외에 적용하는 방법','',
 '현재 생산 ours는 드론 메쉬에 sbr_field를 호출한다. 첫 충돌의 가림을 반영한 투영면 적분에 재질별 실수 진폭과 기하 위상을 합한다. 유전체 셸을 뺀 별도 장면으로 내부 산란을 근사한다. 파일 안의 다중 반사 RCS 함수와 생산 복소 시계열 함수의 지원 범위는 구별해야 한다. 생산 sbr_field는 첫 충돌과 셸 제거 장면을 계산한다. 근거: src/rcs_sbr.py:sbr_field, benchmark/elevation_sweep_md.py:run.','',
 '공통 반송파·재질 표와 각 솔버의 산란 법칙은 구분해야 한다. gamma_po는 재질에 따라 실효 |Γ|를 쓰고 gamma_shape는 TE/TM 전력 평균의 각도 모양을 쓴다. 현재 표적 함수는 실수 재질 진폭을 사용하며, 복소 반사 위상·편파 산란 행렬은 확장 대상으로 남아 있다. “Sionna와 같은 재질 표”는 데이터 출처 설명으로 좁히는 편이 정확하다. 근거: src/materials.py:gamma_po, src/rcs_sbr.py:sbr_field_bistatic.','',
 'range_m을 준 갈래는 평행 입사 광선과 면적 가중치를 유지하면서 표적 내부의 실제 송수신 거리로 위상을 보정한다. 모든 표면점에서 구면파 입사 방향·진폭까지 다시 계산한 모델이라는 표현은 범위를 넘는다. 따라서 가까운 벽·낮은 비행 고도에 적용할 때는 유한 거리의 조명·그림자·반사점 변화도 별도 오차 축으로 둔다.','',
 '**먼저 평평한 지면에서 경로 네 개를 분리해 쓰는 편을 권한다.** 현재 거울상 모델은 균질한 무한 평면의 정반사와 상대 거리 감쇠·행로차를 넣는다. E_dd, E_dg, E_gd, E_gg를 각각 저장하고 w=Γ(R/R_img)exp(−jkΔ)로 합한다. 지면 반사계수 0에서 자유공간으로 돌아오는지, 점 산란 응답에서 (1+w)²가 되는지, 방향 교환과 격자 간격·원점을 바꿀 때 결과가 어떻게 변하는지 확인한다. 대칭화 전후 수치 변화와 물리 모델의 타당성 검사는 각각 남긴다.','',
 '**건물이 있는 장면은 환경 전파와 표적 산란의 결합을 별도 구현하는 방식이 적절하다.** 환경 경로가 표적에 도달하는 방향·거리·복소 진폭을 구하고, 각 입사/출사 경로 쌍마다 표적의 바이스태틱 복소 응답을 평가한다. 목표 형태는 h_target=Σ(q,p) G_out(q)·S_target(u_in(p),u_out(q),t)·G_in(p)다. 이 식은 앞으로 구현하고 대조할 구조 제안이다.','',
 '결합 전에 S_target의 단위를 정해야 한다. 현재 ours의 E는 m² 단위 면적 적분이고 PathSolver의 H는 안테나·거리 감쇠를 포함한 채널 전달함수다. 양쪽 E를 바로 더하거나 완성된 안테나-안테나 H 두 개를 무조건 곱하면 단위와 안테나·거리 감쇠가 중복될 수 있다. 공통 위상 원점, 시간 기준, 길이 지연, 자유공간 정규화를 한 평판/점 산란 예로 먼저 고정한다. NVIDIA의 채널 정의도 안테나 응답·편파 변환 행렬·거리 확산을 구분한다. [공식 기술 보고서](https://nvlabs.github.io/sionna/rt/tech-report/S1.html).','',
 '우선 단일 편파의 명시된 스칼라 근사로 시작할 수 있다. VV/HH·교차편파·건물 반사 뒤의 편파 회전을 해석하려면 표적 응답도 그에 맞게 확장해야 한다. 중심점에 송수신기를 놓아 얻은 환경 경로는 표적 전체에 대한 평면파 근사이므로, 환경 가림이 기체를 가로지르는 근거리 벽에서는 표면점별 가시성 검사 또는 표적 영역별 계산이 추가로 필요하다.','',
 '총 에코는 환경만의 경로와 표적을 포함한 경로를 구분해 합한다. 표적을 Sionna 메쉬와 우리 산란 함수 양쪽에 동시에 계산해 더하는 중복을 피한다. 환경만 장면과 표적을 포함한 장면의 차이는 가림·경로 탐색 변화까지 포함하므로 순수한 표적의 직접 산란으로 부르기 전에 경로 장부로 확인한다. 평균 제거 AC의 표적 귀속도 경로 장부와 대조해야 한다.','',
 '**큐 우선순위는 출처 기록의 수리 → 같은 조건의 반복 → 실외 경로 확장 순서를 권한다.** 지금 돌아가는 0934의 지면·건물·깊이 확장은 계속 읽을 가치가 있다. 다만 이를 “환경이 있을 때만 버전 차이가 난다”는 가설의 확증으로 시작하면 빈 하늘 깊이 2 반례를 놓친다. 0935는 메모리 조회를 맞춘 후 같은 낮은 광선 예산의 켬/끔 비교로 읽는다. 0936은 부위별 메커니즘을 볼 가치가 크지만 ID와 시간축을 고치고 비교 원본을 보존한 뒤 실행할 것을 권한다. 0937은 협곡 오타 복구로 구분해 실행 이력을 관리한다.','',
 '현재 동작하는 후속 큐 예약은 특정 선행 큐 이름을 기다리는 방식으로 정리할 필요가 있다. 기록된 0934의 협곡 실패는 --env 인자의 철자 오류로 분류한다. 실제 큐 상태·시각·PID는 검산 원장 checks.queue_logs와 checks.processes에 남겼다.','',
 '평면 지면 다음에는 벽 하나의 정반사 경로, 이후 지면+벽, 이후 실제 실외 장면으로 넓힌다. 각 단계에서 표적만·환경만·결합·해당 경로 비활성화 대조를 두고, 같은 조건의 반복과 수치 수렴을 따로 잰다. 거칠기·확산·회절을 추가할 때는 해당 손잡이의 경로 수와 포화 진단을 함께 저장한다. 현실성 평가는 실외 RF 계측과의 대조 단계로 남아 있다.','',
 '## 재현','',
 '```bash','/workspace/.venvs/py312/bin/python benchmark/review_kernel_outdoor_0915.py','```','',
 '생성기: [review_kernel_outdoor_0915.py](../benchmark/review_kernel_outdoor_0915.py) · 원장: [kernel_outdoor_review_0915.json](../outputs/kernel_outdoor_review_0915.json). 재실행은 그때의 큐·파일 상태를 새로 기록하므로 시각과 파일 수가 달라질 수 있다.']
 text='\n'.join(lines)+'\n';mdpath=ROOT/'docs/KERNEL_OUTDOOR_REVIEW_0915.md';mdpath.write_text(text)
 blocks=[header('점검 0915','현재 상태와 커널의 실외 적용',did='최신 원자료와 생산 함수를 대조하고 경로 출처·실외 커널의 추가 반례를 확인했다.',results=[f"기존 관문 {len(c['gates'])}개가 통과했다. ⟨outputs/kernel_outdoor_review_0915.json : checks.gates⟩",f"평판 {plate['side_m']} m·3.5 GHz·입출사 0°/60°의 λ/96 결과에서 방향 교환 크기 비가 {last['magnitude_ratio']:.6f}다. ⟨outputs/kernel_outdoor_review_0915.json : checks.plate_reciprocity⟩",f"기본 협곡 CPU 경로 시험에서 이름 배열 범위 밖 물체 ID {probe['naive_name_array_out_of_bounds']}개를 확인했다. ⟨outputs/kernel_outdoor_review_0915.json : checks.path_id_probe⟩"],method=[('원자료','버전 비교 쌍과 반복 샤드의 복소 배열을 직접 재계산'),('구현','생산 구문·실제 CPU PathSolver·평판 커널 대조')],repro={'cmd':d['_meta']['command'],'out':str(OUT),'runtime':'CPU 한 코어; 실행 시각은 원장 참조'})]
 for paragraph in text.split('\n\n'):
  if paragraph.startswith('# 현재 상태'):continue
  ls=paragraph.splitlines()
  for i in range(0,len(ls),10):blocks.append(md('\n'.join(ls[i:i+10])))
 blocks.append(next_steps([('출처 ID와 연속 시계열 저장을 보완','0936의 부위별 스펙트럼 계산 범위','benchmark/elevation_sweep_md.py'),('지면 혼합 경로 두 방향을 모두 계산','지면의 한쪽 두 배 근사가 결과에 미치는 변화','src/rcs_sbr.py'),('위상차가 큰 조건을 반복','버전 전환과 실행별 변화의 구분','runners/jobs_0933_repeat.txt')]))
 result=build_notebook(str(mdpath.with_suffix('.ipynb')),blocks,strict=True)
 print('report built',{'ok':result['ok'],'advisories':len(result['advisories'])},flush=True)

if __name__=='__main__':
 main()
 supplementary()
 path_id_probe()
 publish()
