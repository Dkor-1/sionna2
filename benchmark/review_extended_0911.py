"""Review the follow-up fixes and adjacent aggregation/statistical paths.
Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_extended_0911.py
One CPU; production files and earlier review artifacts are read only.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast,contextlib,importlib,io,itertools,json,math,subprocess,sys,tempfile,time,zipfile
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import review_current_state_0911 as base
import review_postfix_0911 as prior
ROOT=base.ROOT
OUT=ROOT/'outputs/extended_review_0911.json'
MD=ROOT/'docs/EXTENDED_REVIEW_0911.md'
NB=MD.with_suffix('.ipynb')


def production_merge(groups):
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'));blocks=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.For):continue
        start=next((i for i,x in enumerate(node.body) if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Tuple)
            and [getattr(n,'id','') for n in x.targets[0].elts][:2]==['n_tr','n_seen']),None)
        if start is None:continue
        end=next(i for i,x in enumerate(node.body) if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='miss')
        blocks.append(node.body[start:end])
    assert len(blocks)==1
    wrapper=ast.parse('def run(groups):\n results=[]\n for fs in groups:\n  E=None; secs=0.; npa=[]; cfg=None\n return results')
    loop=wrapper.body[0].body[1]
    loop.body+=blocks[0]+ast.parse("results.append(dict(n_trunc=n_tr,n_seen=n_seen,n_trunc_stored=n_tr_stored,by=dict(recomputed=n_tr_recomputed,from_stored=n_tr_from_stored,assumed_cap=n_tr_assumed),cap=cap_seen,cap_for_old=_cap_for_old))").body
    ns=dict(np=np,os=os)
    exec(compile(ast.fix_missing_locations(wrapper),'current merge diagnostic block','exec'),ns)
    return ns['run'](groups)


def merge_checks():
    result={}
    for label,pat in [('stored_cap','*n256_envoutdoor01_S0.3_mfixbatteryi5_blperairframe_d2_el-30_*.npz'),
                      ('missing_cap','*n8192_envoutdoor01_S0.3_mfixbatteryi5_blperairframe_d2_el-30_*.npz')]:
        files=sorted(base.SHD.glob(pat));assert len(files)==2
        for f in files:base.digest(f)
        result[label]=dict(files=[f.name for f in files],result=production_merge([files])[0])
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);kw=dict(idx=np.arange(4),E=np.ones(4,complex),meta=[0,0,1,4,19700,0],nret=np.full(4,1999980))
        short=td/'short.npz';six=td/'six.npz';two=td/'two.npz'
        np.savez(short,**kw,n_trunc=[0]);np.savez(six,**kw,n_trunc=[0,6000000]);np.savez(two,**kw,n_trunc=[0,2000000])
        try:result['short_first']=dict(result=production_merge([[short]]))
        except Exception as e:result['short_first']=dict(error=type(e).__name__,message=str(e))
        result['preceding_caps']=[6000000,2000000]
        result['short_after_six']=production_merge([[six],[short,two]])[-1]
        result['short_after_two']=production_merge([[two],[short,two]])[-1]
    # Inventory records, excluding recently written queue output; no solver execution.
    scan=dict(files_checked=0,recent_skipped=0,read_errors=[],nret_without_nt=[],nt_length_one_with_nret=[])
    cutoff=time.time()-120
    for f in sorted(base.SHD.glob('*.npz')):
        if f.stat().st_mtime>cutoff:scan['recent_skipped']+=1;continue
        try:
            with zipfile.ZipFile(f) as z:
                names=set(z.namelist());scan['files_checked']+=1
                if 'nret.npy' not in names:continue
                if 'n_trunc.npy' not in names:scan['nret_without_nt'].append(f.name)
                else:
                    nt=np.load(io.BytesIO(z.read('n_trunc.npy')),allow_pickle=False)
                    if nt.size==1:scan['nt_length_one_with_nret'].append(f.name)
        except Exception as e:scan['read_errors'].append(dict(file=f.name,error=repr(e)))
    result['inventory']=scan
    ledger=base.js('outputs/elevation_sweep_md.json')
    result['published_classification']=dict(n_rows=len(ledger['rows']),with_by=sum('n_trunc_by' in r for r in ledger['rows']))
    return result


def body_inputs():
    bm=importlib.import_module('read_bodyladder_0910');loader=importlib.import_module('read_0918B_0909')
    old=(loader.SHD,bm.OUT,bm.LADDER,bm.GRID)
    results={}
    try:
        with tempfile.TemporaryDirectory() as td:
            loader.SHD=td;bm.OUT=str(Path(td)/'body.json');bm.LADDER=[(1.,'')];bm.GRID=[]
            for case in ['valid','duplicate_scene','prf_mismatch','half','nan_scene']:
                N=4096 if case=='half' else 8192
                config=[]
                for scene in [False,True]:
                    name=loader.stem(env='outdoor01_ground' if scene else '')
                    allidx=[]
                    for sh in range(2):
                        idx=np.arange(0,N,2) if case=='duplicate_scene' and scene else np.arange(sh,N,2)
                        E=np.full(idx.size,2.+0j if scene else 1.+0j)
                        if scene:E[idx==100]=4.+0j
                        if case=='nan_scene' and scene and sh==0:E[0]=np.nan
                        prf=10000 if case=='prf_mismatch' and scene else 19700
                        np.savez(Path(td)/f'{name}_el-60_{sh:02d}.npz',idx=idx,E=E,meta=[-60,sh,2,8192,prf,0],npaths=np.ones(idx.size),n_dup=np.zeros(idx.size))
                        allidx.extend(idx.tolist())
                    config.append(dict(scene=scene,rows=len(allidx),unique=len(set(allidx)),declared_n=8192,prf_hz=prf))
                with contextlib.redirect_stdout(io.StringIO()),np.errstate(invalid='ignore'):status=bm.main()
                text=Path(bm.OUT).read_text();j=json.loads(text)
                results[case]=dict(input=config,exit=status,n_rows=len(j['rows']),n_poses=j['_meta']['n_poses'],
                    baseline_events=j['_meta']['baseline_events'],monotonic=j['monotonic_in_body_scale'],
                    first_row=j['rows'][0],nonstandard_nan_in_json='NaN' in text)
    finally:loader.SHD,bm.OUT,bm.LADDER,bm.GRID=old
    return results


def exact_jaccard(N,a,b):
    # Uniform independent sets with fixed cardinalities; exact hypergeometric sum.
    lo,hi=max(0,a+b-N),min(a,b)
    def logc(n,k):return math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
    vals=np.arange(lo,hi+1,dtype=int)
    w=np.array([math.exp(logc(a,int(x))+logc(N-a,b-int(x))-logc(N,b)) for x in vals]);w/=w.sum()
    return float(np.dot(w,vals/(a+b-vals))) if a+b else None


def statistical_check():
    bj=base.js('outputs/read_bodyladder_0910.json');cj=base.js('outputs/read_canyonnull_0910.json');rows=[]
    N=bj['_meta']['n_poses'];b=bj['_meta']['baseline_events']
    for r in bj['rows']:
        a=r['n_events'];exact=exact_jaccard(N,a,b)
        rows.append(dict(reader='body',cell=r['cell'],N=N,a=a,b=b,published=r['expected_jaccard_if_unrelated'],exact=exact,exact_rounded=round(exact,5)))
    for el,g in cj['by_el'].items():
        for name,r in g['pairs'].items():
            N=g['cells'][name]['n_poses'];a=r['n_a'];b=r['n_b'];exact=exact_jaccard(N,a,b)
            rows.append(dict(reader='canyon',el=el,cell=name,N=N,a=a,b=b,published=r['expected_jaccard_if_unrelated'],exact=exact,exact_rounded=round(exact,5)))
    changed=[r for r in rows if r['published']!=r['exact_rounded']]
    sets=[set(x) for x in itertools.combinations(range(4),2)]
    enumerated=sum(len(a&b)/len(a|b) for a in sets for b in sets)/(len(sets)**2)
    assert abs(enumerated-exact_jaccard(4,2,2))<1e-12
    return dict(assumption='Fixed-size uniformly and independently drawn sets; a mathematical reference, not a physical null.',
        toy=dict(N=4,a=2,b=2,ratio_of_expected_counts=1/3,expected_ratio=exact_jaccard(4,2,2),enumerated_expected_ratio=enumerated),
        rows=rows,n_rounding_changes=len(changed),max_absolute_error=max(abs(r['published']-r['exact']) for r in rows),changed=changed)


def current_checks():
    with contextlib.redirect_stdout(io.StringIO()):
        readers=prior.reader_checks();h=prior.harness_checks();builder=prior.builder_check()
    assert h['partial_bug']['defects_still_present']['unknown_dup_counted_as_short'] is True
    assert h['missing_row']['defects_still_present']['unknown_dup_counted_as_short'] is None
    assert not readers['zero_amplitude']['rows'] and not readers['half_without_meta']['rows']
    assert readers['drop_metadata']['n_rows']==0 and not readers['hampel_prf']['table']['-60']
    return dict(readers=readers,harness=h,builder=builder)


def actual_publications():
    c=base.published();m=prior.previous.old_module();body=m.body_check()
    for p,h in m.HASHES.items():
        if not p.startswith('git:'):base.digest(p)
    fs=set()
    for r in body['files'].values():fs.update(r['files_free']);fs.update(r['files_scene'])
    return dict(canyon_drop=c,body=body,body_shards=len(fs),body_cells=len(body['pairs_to_base']),
        union_shards=len(base.READ_FILES|fs),drop_skipped=len(base.js('outputs/read_dropladder_0910.json')['_meta']['skipped']))


def findings(c):
    out=[]
    def add(title,kind,obs,fix,refs):out.append(dict(title=title,kind=kind,observation=obs,fix=fix,sources=[base.source(*r) for r in refs]))
    m=c['merge'];inv=m['inventory'];r=m['missing_cap']['result'];s=c['statistics'];b=c['current']['builder']
    add('상한 없는 n_trunc 분기에서 초기화 전 변수 또는 앞 칸의 상한을 쓴다','이번 수정에서 생긴 실행 오류 · 합성 반례',
        f"nret과 길이 하나의 n_trunc를 가진 합성 입력이 첫 칸이면 {m['short_first']['error']}가 난다. "
        f"앞 칸 상한을 {m['preceding_caps']}으로 바꾸자, 동일한 다음 칸의 경고 수가 "
        f"{m['short_after_six']['n_trunc']}와 {m['short_after_two']['n_trunc']}로 달라졌다. 다음 칸에는 자체 저장 상한이 있는 샤드도 함께 넣었다. "
        f"재고 {inv['files_checked']}개 파일 중 이 길이 하나 형식은 {len(inv['nt_length_one_with_nret'])}개였다. 최근 파일 {inv['recent_skipped']}개와 읽기 오류 {len(inv['read_errors'])}개는 범위 밖이다. 현재 큐에서 이 예외가 발생했다는 주장은 아니다.",
        '상한 없는 진단은 같은 칸의 보류 목록에 넣고, 그 칸의 상한·가정 정책을 결정한 뒤 처리한다. 첫 칸과 뒤 칸, 앞 칸 상한을 바꾼 순서 시험을 함께 둔다.',
        [('benchmark/elevation_sweep_md.py','n_tr += int(np.count_nonzero(_nr >= 0.99 * _cap_for_old))'),('benchmark/elevation_sweep_md.py','_cap_for_old = cap_seen if cap_seen else _cap_default')])
    add('보류한 진단은 경고 수에 들어가지만 분류별 표본수에서 빠진다','이번 수정의 집계 누락 · 실제 저장 샤드 재현',
        f"실제 S0.3·el −30·n8192 묶음의 현재 병합 블록은 n_trunc={r['n_trunc']}, n_seen={r['n_seen']}인데 n_trunc_by={r['by']}다. "
        f"진단 분류의 표본수 합이 {sum(r['by'].values())}라 처리된 표본수를 설명하지 못한다. 재고에서 nret만 있고 n_trunc가 없는 파일은 {len(inv['nret_without_nt'])}개다. "
        f"현재 발간 주 원장 {m['published_classification']['n_rows']}행의 n_trunc_by 필드 보유는 {m['published_classification']['with_by']}행이므로, 이 새 필드가 이미 발간됐다고 하지는 않는다.",
        '보류 목록을 처리하는 루프에서도 실제 적용한 정책의 분류를 올린다. 다른 샤드의 상한을 빌린 경우와 실행 환경 기본값을 쓴 경우의 출처를 기록하고, 분류 합계와 진단 대상 표본수를 대조한다.',
        [('benchmark/elevation_sweep_md.py','for _nr, _n in _pend:'),('benchmark/elevation_sweep_md.py','prov["n_trunc_by"] = dict')])
    d=c['body_inputs']
    add('동체 사다리의 생산 로더에는 입력 검증이 연결되지 않았다','추가 조사 범위 · 합성 입력 거절 실패',
        f"read_bodyladder.main에 실제 파일을 넣었다. 중복 장면 인덱스는 고유 {d['duplicate_scene']['input'][1]['unique']}/행 {d['duplicate_scene']['input'][1]['rows']}인데 결과 {d['duplicate_scene']['n_rows']}행을 발행했다. "
        f"장면·빈하늘 PRF 불일치도 {d['prf_mismatch']['n_rows']}행, 선언 길이보다 짧은 입력도 n_poses={d['half']['n_poses']}로 발행됐다. "
        f"정상 대조의 기준 사건은 {d['valid']['baseline_events']}인데, 별도 자세에 NaN을 넣자 기준 사건 {d['nan_scene']['baseline_events']}으로 발행됐다. 현재 발간 동체 칸은 별도 엄격 로더로 재계산해 일치했으므로 합성 반례를 발간 자료 손상으로 소급하지 않는다.",
        '동체 판독기가 실제로 가져오는 read_0918B.load/measure에 인덱스·길이·샤드 메타데이터·유한값·비교 시간축 검사를 연결한다. 각 입력 거절 사유를 원장에 남기고, 기준선 실패 때 전체 결과의 상태를 명시한다.',
        [('benchmark/read_bodyladder_0910.py','from read_0918B_0909 import load'),('benchmark/read_0918B_0909.py','o = np.argsort(np.concatenate(I))'),('benchmark/read_0918B_0909.py','if F.size != O.size:')])
    add('기대 자카드는 기대 교집합을 대입한 근삿값이다','추가 발견 · 현재 발간 참고값의 이름과 계산',
        f"균일·독립이며 집합 크기를 고정한 가정에서도 E[I]/(a+b−E[I])와 E[I/(a+b−I)]는 다르다. "
        f"작은 전수 계산 N={s['toy']['N']}, a=b={s['toy']['a']}에서 각각 {s['toy']['ratio_of_expected_counts']:.6f}와 {s['toy']['expected_ratio']:.6f}다. "
        f"현재 동체·협곡 참고값 {len(s['rows'])}행 중 소수점 표시가 달라지는 것은 {s['n_rounding_changes']}행이며, 발간값과 정확한 기대값의 최대 절대 차이는 {s['max_absolute_error']:.8f}다. "
        '관측 자카드·사건 수는 이 지적의 변경 대상이 아니다. 정확한 기댓값으로 바꾸어도 물리적 널이나 유의성 검정이 생기는 것은 아니다.',
        '현 식을 유지하면 기대 교집합을 대입한 자카드 근사라고 이름과 식을 함께 적는다. 정확한 기대값이 필요하면 고정 크기 집합의 교집합 분포에 대해 비율 자체를 평균한다.',
        [('benchmark/read_bodyladder_0910.py','row["expected_jaccard_if_unrelated"] = round'),('benchmark/read_canyonnull_0910.py','expected_jaccard_if_unrelated=round')])
    add('마크다운 정정이 노트북 작업 지시까지 전달되지 않았다','남은 이전 지적 · 실제 재생성 결과',
        f"검토 빌더는 {b['mode']}로 정상 완료한다. 마크다운 마지막 순서는 아틀라스가 이미 고쳐졌다고 수정됐다. "
        f"하지만 노트북은 옛 replacement 문장 포함={b['notebook_obsolete_proposal_present']}, 아틀라스 정정 작업 포함={b['notebook_obsolete_next_step_present']}다. "
        '확인 범위는 이번에 임시 경로로 실제 재생성한 문서와 노트북이다.',
        '노트북의 항목별 replacement와 next_steps도 fixed 상태에서 생성한다. 마크다운과 노트북이 같은 현재 권고 필드를 읽도록 묶는다.',
        [('benchmark/review_latest_readers_0910.py',"blocks.append(md(f\"## {i+1}. {f['title']}\""),('benchmark/review_latest_readers_0910.py',"('아틀라스 대역과 관련 산출물을 정정한다'")])
    assert all(s['found'] for f in out for s in f['sources'])
    return out


def render(o):
    c=o['checks'];p=c['publications'];h=c['current']['harness'];j=str(OUT.relative_to(ROOT))
    good=[f"기존 회귀 반례: 일부 오집계 탐지={h['partial_bug']['defects_still_present']['unknown_dup_counted_as_short']}, 결과 행 누락은 미확인 {h['missing_row']['n_unknown']}건으로 분류했다.",
          '낙차 판독기의 기존 메타데이터 누락·불일치·영 중앙값 반례와 Hampel의 서로 다른 PRF 반례를 거절했다.',
          f"협곡 {p['canyon_drop']['n_canyon_cells']}칸·낙차 {p['canyon_drop']['n_drop_cells']}칸과 동체 {p['body_cells']}칸을 원본에서 재계산했다. 합친 원본 파일은 {p['union_shards']}개다."]
    lines=['# 현재 수정 상태와 인접 경로 추가 점검','',f"기준 `{o['_meta']['head']}` · {o['_meta']['checked_at_utc']}",'',
        '[주피터 보고서](EXTENDED_REVIEW_0911.ipynb) · [실행 원장](../outputs/extended_review_0911.json) · [재현 생성기](../benchmark/review_extended_0911.py)','',
        '## 확인된 수정','']+['- '+s for s in good]+['',
        '이전 반례의 수정과 추가 입력의 거절 범위를 따로 판단했다. 운영 코드·GPU 큐·기존 발간물은 변경하지 않았다. '
        '주 병합기는 현재 함수의 진단 블록을 추출해 함수 범위와 칸 반복을 유지하며 실행했다. 물리적 정확성이나 GPU 재현성을 새로 판정한 보고서는 아니다.','',
        '## 남은 문제와 추가 발견','']
    for i,f in enumerate(o['findings']):
        lines += [f"### {i+1}. {f['title']}",'',f"**범위:** {f['kind']}",'',f['observation'],'','**권장 수정:** '+f['fix'],'',f"⟨{j} : findings[{i}]⟩",'']
        for s in f['sources']:lines += [f"- [{Path(s['path']).name}:{s['line']}](../{s['path']}#L{s['line']})",'```python',s['quote'],'```','']
    lines += ['## 해석 범위와 순서','',
        '먼저 새 병합 분기의 변수 범위와 분류 합계를 고친다. 이어 동체 판독기의 실제 진입점까지 입력 검증을 연결한다. '
        '참고 기댓값의 명칭과 보고서 지시는 그다음 문면에서 정리한다. 분류 필드의 발간은 병합 검사를 통과한 산출물로 진행한다.','',
        '추가 확인 범위에 있는 진단 요약도 주의가 필요하다. read_0918B.measure는 npaths가 없는 경우 상한 근접 요약 필드를 생략한다. '
        '원시 trunc 기록은 보존하므로 진단 전체 유실로 부르지 않는다. 이 항목은 이전 감사에서 확인한 잔여 범위이며 새 발견 수에 합치지 않았다.','',
        '```bash',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_extended_0911.py",'```','']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='현재·확장 점검',title='이전 반례 수정과 새 병합·비교 경로의 보완점',did='기존 수정과 인접 판독 경로를 실제 입력으로 대조했다.',
        results=[f"원본 파일 {p['union_shards']}개로 발간 수를 재계산했다 ⟨{j} : checks.publications⟩.",
                 f"남은 보완점 {len(o['findings'])}건의 재현 조건을 적었다 ⟨{j} : findings⟩.",
                 f"회귀 검사 조건 {len(h)}개에서 판정 변화를 확인했다 ⟨{j} : checks.current.harness⟩."],
        method=[('생산 경로','현재 main과 함수 범위를 유지한 병합 블록을 실행'),('범위 확장','동체 판독·진단 분류·참고 기댓값을 추가 대조')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_extended_0911.py"],out=[j],runtime='CPU 한 코어, 저장 자료 판독'))]
    for i,f in enumerate(o['findings']):blocks.append(md(f"## {i+1}. {f['title']}",'',f['fix'],'',f"[조건·실행 결과·소스](EXTENDED_REVIEW_0911.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([('병합 분기와 분류 합계를 바로잡는다','새 진단 필드의 실행·집계 일관성','EXTENDED_REVIEW_0911.md'),('동체 판독과 보고 문면에 현재 규칙을 연결한다','입력 거절 범위와 발간 해석','EXTENDED_REVIEW_0911.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    for p in [__file__,'benchmark/review_postfix_0911.py','benchmark/review_fix_verification_0911.py','benchmark/review_current_state_0911.py']:base.digest(p)
    checks={}
    for name,fn in [('current',current_checks),('merge',merge_checks),('body_inputs',body_inputs),('statistics',statistical_check),('publications',actual_publications)]:
        checks[name]=fn();print('completed '+name,flush=True)
    fs=findings(checks)
    o=dict(_meta=dict(generator='benchmark/review_extended_0911.py',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        checked_at_utc=datetime.now(timezone.utc).isoformat(),source_sha256=base.HASHES),checks=checks,findings=fs)
    OUT.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n');render(o)
    print(json.dumps(dict(findings=len(fs),published_files=checks['publications']['union_shards']),ensure_ascii=False))

if __name__=='__main__':main()
