"""Check reported reader fixes against production entry points and stored shards.
Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_postfix_0911.py
Only this audit's artifacts are written; mutations operate in memory.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast, contextlib, importlib, io, json, subprocess, sys, tempfile, types
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import review_current_state_0911 as base
import review_fix_verification_0911 as previous
ROOT=base.ROOT
OUT=ROOT/'outputs/postfix_review_0911.json'
MD=ROOT/'docs/POSTFIX_REVIEW_0911.md'
NB=MD.with_suffix('.ipynb')


def merge_block(files):
    tree=ast.parse(base.read('benchmark/elevation_sweep_md.py'))
    blocks=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.For):continue
        start=next((i for i,x in enumerate(node.body) if isinstance(x,ast.Assign)
            and isinstance(x.targets[0],ast.Tuple)
            and [getattr(n,'id','') for n in x.targets[0].elts][:2]==['n_tr','n_seen']),None)
        if start is None:continue
        end=next(i for i,x in enumerate(node.body) if isinstance(x,ast.Assign)
                 and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='miss')
        blocks.append(node.body[start:end])
    assert len(blocks)==1
    ns=dict(np=np,os=os,fs=files,E=None,secs=0.,npa=[],cfg=None)
    exec(compile(ast.Module(body=blocks[0],type_ignores=[]),'production merge diagnostic block','exec'),ns)
    return dict(n_trunc=ns['n_tr'],n_trunc_stored=ns['n_tr_stored'],n_seen=ns['n_seen'],
                cap_seen=ns['cap_seen'],cap_for_old=ns['_cap_for_old'],n_pending=len(ns['_pend']))


def merge_checks():
    name='sionna_p4000000000_swR0D0E0F1_r15_n256_envoutdoor01_S0.3_mfixbatteryi5_blperairframe_d2_el-30_*.npz'
    files=sorted(base.SHD.glob(name));assert len(files)==2
    for f in files:base.digest(f)
    actual=merge_block(files)
    direct=0
    for f in files:
        with np.load(f) as z:direct+=int((z['nret']>=.99*z['n_trunc'][1]).sum())
    assert actual['n_trunc']==direct and actual['n_trunc_stored']==0 and direct==256
    result=dict(real_legacy=dict(files=[f.name for f in files],actual=actual,independent_count=direct))
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'shard.npz';kw=dict(idx=np.arange(4),E=np.ones(4,complex),meta=[0,0,1,4,19700,0])
        np.savez(p,**kw,n_trunc=[0,2000000])
        result['missing_nret']=merge_block([p])
        np.savez(p,**kw,nret=np.full(4,1999980))
        old=os.environ.get('SIONNA2_MAX_PATHS')
        try:
            rows=[]
            for cap in [2000000,6000000]:
                os.environ['SIONNA2_MAX_PATHS']=str(cap)
                rows.append(dict(environment_cap=cap,result=merge_block([p])))
            result['missing_cap']=rows
        finally:
            if old is None:os.environ.pop('SIONNA2_MAX_PATHS',None)
            else:os.environ['SIONNA2_MAX_PATHS']=old
    return result


def harness_checks():
    m=previous.old_module();rd=importlib.import_module('read_dropladder_0910')
    reload_real=importlib.reload;results={}
    for mode in ['baseline','old_bug','partial_bug','missing_row','main_raises']:
        def hooked(module):
            module=reload_real(module)
            if module.__name__!='read_dropladder_0910':return module
            if mode in ['old_bug','partial_bug']:
                tree=ast.parse(base.read('benchmark/read_dropladder_0910.py'))
                fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
                hits=0
                for n in ast.walk(fn):
                    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='short' for t in n.targets):
                        n.value=ast.parse('D < 2' if mode=='old_bug' else '(D < 0) & (np.arange(D.size) == 1)',mode='eval').body;hits+=1
                assert hits==1
                exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),mode,'exec'),module.__dict__)
            elif mode=='missing_row':
                def empty_main():
                    Path(module.OUT).write_text(json.dumps({'rows':[],'_meta':{'skipped':[{'why':'synthetic missing target'}]}}))
                    return 0
                module.main=empty_main
            elif mode=='main_raises':
                def raising_main():raise RuntimeError('synthetic execution failure')
                module.main=raising_main
            return module
        try:
            importlib.reload=hooked
            with contextlib.redirect_stdout(io.StringIO()):v=m.adversarial_check()
            results[mode]={k:v[k] for k in ['production_main_ran','mixed_dup_counted_short_fixed',
                'defects_still_present','n_unknown','status_ko','production_skipped']}
        finally:
            importlib.reload=reload_real;reload_real(rd)
    assert results['old_bug']['defects_still_present']['unknown_dup_counted_as_short'] is True
    assert results['main_raises']['defects_still_present']['unknown_dup_counted_as_short'] is None
    return results


def reader_checks():
    with contextlib.redirect_stdout(io.StringIO()):r=previous.tests()
    r.pop('test_mutation') # Obsolete interception in that historical helper is not evidence.
    rd=importlib.import_module('read_dropladder_0910');importlib.reload(rd)
    with tempfile.TemporaryDirectory() as td:
        rd.SHD=td;rd.OUT=str(Path(td)/'out.json');rd.ARMS=['R0D0E0F1'];rd.SPPS=[4000000000]
        try:
            for case in ['zero_amplitude','half_without_meta']:
                N=8192 if case=='zero_amplitude' else 4096
                for sh in range(2):
                    idx=np.arange(sh,N,2);kw=dict(idx=idx,E=np.zeros(idx.size,complex) if case=='zero_amplitude' else np.ones(idx.size,complex),n_dup=np.full(idx.size,2),npaths=np.ones(idx.size))
                    if case=='zero_amplitude':kw['meta']=[0,sh,2,N,19700,0]
                    np.savez(Path(td)/f'sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2_el+0_{sh:02d}.npz',**kw)
                with contextlib.redirect_stdout(io.StringIO()),np.errstate(invalid='ignore'):rd.main()
                j=json.loads(Path(rd.OUT).read_text());r[case]=dict(rows=j['rows'],skipped=j['_meta']['skipped'],declared_name_n=8192,actual_n=N)
        finally:importlib.reload(rd)
    cn=importlib.import_module('read_canyonnull_0910')
    fn=base.funcs(ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py',['hampel_mask'],dict(np=np))['hampel_mask']
    fake=types.ModuleType('bake_outdoor');fake.hampel_mask=fn
    prior=sys.modules.get('bake_outdoor');sys.modules['bake_outdoor']=fake
    try:
        E=np.ones(8192,complex);E[100]=2
        def loader(name,el):
            return dict(E=E,idx_ok=True,n_rows=E.size,n_unique=E.size,n_expected=E.size,prf_hz=19700 if name==0 else 10000),2
        r['hampel_prf']=dict(base_prf_hz=19700,candidate_prf_hz=10000,
            table=cn._deck_mask_table(loader,lambda spp,rep,env:rep,[-60],[('candidate',4000000000,1)]))
    finally:
        if prior is None:sys.modules.pop('bake_outdoor',None)
        else:sys.modules['bake_outdoor']=prior
    return r


def builder_check():
    m=previous.old_module()
    with tempfile.TemporaryDirectory(dir=ROOT/'work',prefix='.postfix-') as td:
        m.OUT=Path(td)/'out.json';m.MEMO=Path(td)/'out.md';m.NB=Path(td)/'out.ipynb'
        with contextlib.redirect_stdout(io.StringIO()):m.main()
        j=json.loads(m.OUT.read_text());a=j['checks']['atlas'];s=a['sample']
        text=m.MEMO.read_text();nb=json.loads(m.NB.read_text())
        cells=[''.join(c['source']) for c in nb['cells']]
        return dict(completed=True,mode=a['mode'],current_tip_hz=s['current_tip_hz'],scaled_tip_hz=s['scaled_tip_hz'],
            finding=j['findings'][0],tail=text[text.index('## 수정 순서'):],
            notebook_obsolete_proposal_present=any(j['findings'][0]['replacement'] in c for c in cells),
            notebook_obsolete_next_step_present=any('아틀라스 대역과 관련 산출물을 정정한다' in c for c in cells))


def findings(c):
    fs=[]
    def add(title,kind,evidence,fix,refs):
        fs.append(dict(title=title,kind=kind,evidence=evidence,fix=fix,sources=[base.source(*r) for r in refs]))
    h=c['harness'];m=c['merge'];t=c['readers'];b=c['builder']
    add('회귀 검사에서 결과 행 누락과 일부 오집계를 통과시킨다','새 합성 반례 · 검사 판정',
        f"실제 main을 메모리에서 옛 식으로 되돌리면 n_short={h['old_bug']['mixed_dup_counted_short_fixed']}로 잡힌다. "
        f"하지만 일부 미계측만 잘못 세는 변형은 n_short={h['partial_bug']['mixed_dup_counted_short_fixed']}인데 결함 판정이 {h['partial_bug']['defects_still_present']['unknown_dup_counted_as_short']}다. "
        f"main이 빈 rows를 쓰고 정상 종료하는 변형도 n_short={h['missing_row']['mixed_dup_counted_short_fixed']}인데 동일하게 통과한다. "
        '이는 실제 운영 자료의 오집계 발견이 아니라 검사 자체의 탐지 범위 반례다.',
        '정상 종료와 목표 행 존재·유일성·필드 유효성을 따로 확인한다. 이 합성 입력의 기대값과 결과값을 직접 비교하고, 행 누락은 미확인으로 남긴다. 검사에는 생산식과 별도로 정한 기대 결과를 둔다.',
        [('benchmark/review_latest_readers_0910.py',"short_fixed = _row['n_short'] if _row else None"),('benchmark/review_latest_readers_0910.py',"bool(result['mixed_dup_counted_short_fixed']==unknown")])
    add('시간축·표본수 검사가 낙차 판독과 Hampel 비교에는 덜 연결됐다','남은 입력 검증 · 합성 입력',
        f"서로 다른 선언 표본수·PRF를 섞은 낙차 입력이 {t['drop_metadata']['n_rows']}행으로 발행됐다. "
        f"파일명은 n={t['half_without_meta']['declared_name_n']}인데 메타데이터 없이 앞쪽 {t['half_without_meta']['actual_n']}개 표본만 넣은 입력도 {len(t['half_without_meta']['rows'])}행으로 발행됐다. "
        f"Hampel 표는 기준 PRF={t['hampel_prf']['base_prf_hz']} Hz, 비교 PRF={t['hampel_prf']['candidate_prf_hz']} Hz인데 candidate 행을 냈다. "
        '장면과 빈하늘 쌍의 PRF 불일치 거절은 이번 수정으로 통과했다. 같은 인덱스가 같은 시각을 뜻한다는 해석은 별도 조건이다.',
        '샤드별 선언 N·PRF와 파일명/요청 N을 대조하고, 메타데이터가 없으면 검증 불가 사유를 남긴다. Hampel 쌍도 시간축을 확인한다. 세대 선택은 인덱스와 선언 길이의 완전성을 확인한 뒤 수행한다.',
        [('benchmark/read_dropladder_0910.py','n_expected = int(_m[3])'),('benchmark/read_canyonnull_0910.py','if c is None or n < 2 or c["E"].size != mb.size')])
    add('주 원장 상한 진단의 예외 분기와 설명이 어긋난다','남은 예외 처리·해석',
        f"실제 옛 샤드 묶음은 저장 {m['real_legacy']['actual']['n_trunc_stored']}에서 현재 규칙 {m['real_legacy']['actual']['n_trunc']}으로 수정됐다. "
        f"그러나 nret이 빠진 합성 입력은 저장값 {m['missing_nret']['n_trunc_stored']}을 현재 n_trunc={m['missing_nret']['n_trunc']}으로 사용하고 n_seen={m['missing_nret']['n_seen']}으로 센다. "
        f"상한이 없는 동일 입력은 실행 환경 상한 {[x['environment_cap'] for x in m['missing_cap']]}에서 경고 수 {[x['result']['n_trunc'] for x in m['missing_cap']]}로 달라진다. "
        '상한 가정은 max_paths_cap_assumed로 표시되므로 숨겼다고 하지는 않는다. 다만 모든 n_trunc가 저장 상한 재계산이라는 설명과는 다르다. '
        '저장값과 재계산값이 다르다는 사실은 판정 규칙 차이로도 생기므로, 한 칸 내부의 세대 혼합을 증명하지 않는다.',
        '확정 재계산·옛 저장값·상한 가정 계산을 분리하고 각 범위와 미확인 표본수를 기록한다. nret/저장 상한이 빠진 경우에는 현재 규칙의 확정값을 미확인으로 둔다. 차이는 우선 저장 당시 규칙과 현재 규칙의 차이로 설명한다.',
        [('benchmark/elevation_sweep_md.py','n_tr += int(_nt[0])'),('benchmark/elevation_sweep_md.py','_cap_default = int(os.environ.get'),('benchmark/elevation_sweep_md.py','있다). 둘이 다르면 그 칸은 세대가 섞였다는 뜻이다.')])
    z=t['zero_amplitude'];row=z['rows'][0]
    add('유한한 전계라도 중앙값이 영이면 낙차 판정이 정의되지 않는다','새 합성 반례 · 분모 검사',
        f"전계가 모두 영인 합성 입력 n={z['actual_n']}에서 n_dip={row['n_dip']}, dip_equals_short={row['dip_equals_short']}가 발행됐다. "
        '이 입력의 전계는 유한하지만 중앙값으로 나눈 비율은 정의되지 않는다. 이 결과를 정상 판정으로 읽으면 무응답과 낙차 부재가 섞인다. 실제 발간 칸에서 이 상황을 발견했다는 뜻은 아니다.',
        '비율 계산 전 중앙값의 양수·유한 여부를 확인하고, 실패하면 원장에 사유와 미정 판정을 남긴다. 임의의 작은 상수를 더하려면 그에 따른 낙차 정의 변경을 별도로 정해야 한다.',
        [('benchmark/read_dropladder_0910.py','a = np.abs(E); med = float(np.median(a))'),('benchmark/read_dropladder_0910.py','dip = (a / med) < DIP')])
    add('고쳐짐 제목 아래의 수정 제안과 마지막 작업 순서는 과거 상태다','현재 생성 보고서 문면',
        f"검토 빌더는 mode={b['mode']}로 끝났고 기준 대역 {b['current_tip_hz']}와 {b['scaled_tip_hz']}가 같다. "
        f"제목은 {b['finding']['title']}로 바뀌었다. 하지만 노트북의 옛 replacement 문장 재출력={b['notebook_obsolete_proposal_present']}, "
        f"옛 아틀라스 정정 작업 재출력={b['notebook_obsolete_next_step_present']}다. 마크다운 마지막 수정 순서도 아틀라스를 먼저 고치고 다시 굽으라고 지시한다.",
        'fixed 상태에서 replacement와 최종 작업 목록도 함께 분기한다. 완료 항목은 정정 기록과 유지할 검사로 안내하고, 과거 제안에는 과거 기록임을 명시한다. 아틀라스는 완료 기록으로 안내하고 문면을 정정한다.',
        [('benchmark/review_latest_readers_0910.py','replacement=replacement,followup=followup'),('benchmark/review_latest_readers_0910.py',"'발간 숫자에 영향이 확인된 아틀라스의 대역 정의를 먼저 고치고")])
    assert all(s['found'] for f in fs for s in f['sources'])
    return fs


def render(o):
    c=o['checks'];p=c['published'];t=c['readers'];j=str(OUT.relative_to(ROOT))
    statements=[
        f"실제 주 원장 병합 진단 블록: 옛 샤드 묶음 저장 {c['merge']['real_legacy']['actual']['n_trunc_stored']} → 현재 규칙 {c['merge']['real_legacy']['actual']['n_trunc']}로 재계산됐다.",
        f"complex64 NaN 검출 {t['nan64']['reported_nonfinite']}, idx_ok={t['nan64']['idx_ok']}; 서로 다른 PRF의 장면/빈하늘 쌍 채택 {len(t['cross_record_prf']['accepted_cells'])}칸이다.",
        f"전부 n_dup 미계측 입력의 skipped는 {len(t['drop_all_unmeasured']['skipped'])}건이다. 부분 미계측의 일치 판정은 {t['drop_partial']['rows'][0]['dip_equals_short']}다.",
        f"옛 short 식을 복원한 main의 오류를 탐지했다. main 예외 때 n_unknown={c['harness']['main_raises']['n_unknown']}으로 남긴다.",
        f"협곡 {p['n_canyon_cells']}칸·낙차 {p['n_drop_cells']}칸을 원본 샤드 {p['n_unique_shards']}개에서 재계산했고 발간값과 일치했다."]
    lines=['# 후속 수정 재확인과 남은 보완점','',f"기준 커밋 `{o['_meta']['head']}` · {o['_meta']['checked_at_utc']}",'',
        '[주피터 보고서](POSTFIX_REVIEW_0911.ipynb) · [재계산 원장](../outputs/postfix_review_0911.json) · [생성기](../benchmark/review_postfix_0911.py)','',
        '## 확인된 수정','']+['- '+s for s in statements]+['',
        '위 수의 조건·파일 목록은 원장의 checks에 있다. 원본 샤드의 인덱스·유한값·비교 시간축을 대조했다. '
        '이 확인은 지정한 경로와 자료의 범위이며, GPU 워커의 과거 생존 상태나 물리적 정확성까지 확인한 뜻은 아니다.','',
        '## 추가 수정 제안','']
    for i,f in enumerate(o['findings']):
        lines += [f"### {i+1}. {f['title']}",'',f"**범위:** {f['kind']}",'',f['evidence'],'','**권장 수정:** '+f['fix'],'',f"원장: `{j}` → `findings[{i}]`.",'']
        for s in f['sources']:
            lines += [f"- [{Path(s['path']).name}:{s['line']}](../{s['path']}#L{s['line']})",'```python',s['quote'],'```','']
    lines += ['## 실행 범위','',
        '운영 코드·기존 원장·발표 파일을 바꾸지 않았다. 실제 판독 main은 임시 샤드를 읽고 임시 원장을 쓰게 실행했다. '
        '주 병합기는 GPU 의존부를 실행하지 않고 해당 함수의 진단 블록을 AST로 추출해 실제 저장 샤드에 적용했다. '
        '회귀 반례는 importlib.reload 직후 메모리에서만 main을 바꾸었으며 각 시험 뒤 원래 모듈로 복구했다. '
        '과거 감사의 시험 도우미를 재사용하되 옛 방식의 mutation 결과는 이번 근거에서 제외했다.','',
        '상한 진단 설명과 보고서 수정 제안은 현재 코드의 문제다. 나머지 추가 오동작은 합성 입력으로 재현한 것이며, 이번에 대조한 발간 칸이 손상됐다고 소급하지 않는다.','',
        '```bash',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_postfix_0911.py",'```','']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='후속 재확인',title='지정 수정은 재현되고 예외 경로는 남아 있다',
        did='현재 생산 경로와 원본 샤드로 전달된 수정 내역을 확인했다.',
        results=[f"원본 샤드 {p['n_unique_shards']}개에서 발간 수를 재계산했다 ⟨{j} : checks.published⟩.",
            f"옛 오류 복원 시험을 포함한 회귀 조건 {len(c['harness'])}개를 확인했다 ⟨{j} : checks.harness⟩.",
            f"남은 보완점 {len(o['findings'])}건을 근거·범위와 함께 적었다 ⟨{j} : findings⟩."],
        method=[('운영 경로','생산 main과 실제 병합 진단 블록을 임시 환경에서 실행'),('추가 반례','입력 결측과 메모리 내 오류 복원으로 거절 조건을 확인')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_postfix_0911.py"],out=[j],runtime='CPU 한 코어, 저장 자료 판독'))]
    for i,f in enumerate(o['findings']):
        blocks.append(md(f"## {i+1}. {f['title']}",'',f['fix'],'',f"[실행 근거와 범위](POSTFIX_REVIEW_0911.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([('결과 행·기대값·시간축·분모 검사를 보완한다','합성 입력에서 확인된 예외 처리','POSTFIX_REVIEW_0911.md'),('상한 진단과 보고서 문면을 현재 상태에 맞춘다','실행 결과보다 넓은 완료 표현','POSTFIX_REVIEW_0911.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    base.digest(__file__);base.digest('benchmark/review_current_state_0911.py');base.digest('benchmark/review_fix_verification_0911.py')
    c={}
    for name,fn in [('merge',merge_checks),('readers',reader_checks),('harness',harness_checks),('builder',builder_check),('published',base.published)]:
        c[name]=fn();print('completed '+name,flush=True)
    fs=findings(c)
    o=dict(_meta=dict(generator='benchmark/review_postfix_0911.py',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        checked_at_utc=datetime.now(timezone.utc).isoformat(),source_sha256=base.HASHES,
        scope='Production readers and extracted merge diagnostic block; synthetic cases are not corpus corruption.'),checks=c,findings=fs)
    OUT.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n');render(o)
    print(json.dumps(dict(findings=len(fs),published_shards=c['published']['n_unique_shards']),ensure_ascii=False))

if __name__=='__main__':main()
