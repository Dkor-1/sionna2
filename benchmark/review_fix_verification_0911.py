"""Verify the reported fixes against actual reader entry points and stored data.

Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_fix_verification_0911.py
One CPU, no solver runs. Existing publications and production code are read only.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import ast
import contextlib
from datetime import datetime,timezone
import glob
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import types
import numpy as np
import review_current_state_0911 as base

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/fix_verification_0911.json'
MD=ROOT/'docs/FIX_VERIFICATION_0911.md'
NB=MD.with_suffix('.ipynb')


def old_module():
    p=base.digest('benchmark/review_latest_readers_0910.py')
    s=importlib.util.spec_from_file_location('review_0910_verification',p)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m


def verify_builder():
    m=old_module()
    with tempfile.TemporaryDirectory(prefix='.fix-verification-',dir=ROOT/'work') as td:
        m.OUT=Path(td)/'out.json';m.MEMO=Path(td)/'out.md';m.NB=Path(td)/'out.ipynb'
        with contextlib.redirect_stdout(io.StringIO()):m.main()
        j=json.loads(m.OUT.read_text());a=j['checks']['atlas'];s=a['sample']
        return dict(completed=True,mode=a['mode'],current_tip_hz=s['current_tip_hz'],
                    scaled_tip_hz=s['scaled_tip_hz'],no_double_scale=s['current_tip_hz']==s['scaled_tip_hz'],
                    advertised_verdict=j['checks']['adversarial']['status_ko'],
                    current_atlas_finding=j['findings'][0],current_trunc_finding=j['findings'][4],
                    generated_markdown_keeps_atlas_failure=j['findings'][0]['title'] in m.MEMO.read_text())


def tests():
    ms=base.funcs('benchmark/read_0918B_0909.py',['load','db','measure'],
                  dict(np=np,glob=glob,os=os,DEV=.5,CAP=2000000,EL=-60))
    ns=base.funcs('benchmark/read_canyonnull_0910.py',['load','_trunc_of','stem','main','_deck_mask_table'],
                  dict(np=np,glob=glob,os=os,json=json,sys=sys,measure=ms['measure'],DEV=.5,CAP=2000000,
                       ARM='R0D0E0F1',ENV='synthetic',ENVTAG='envsionna-simple_street_canyon',
                       MESH='mfixbatteryi5_blperairframe',ELS=[-60],CELLS=[('기준선 (4e9)',4000000000,0)],
                       ROOT=str(ROOT),DECK=''))
    real_table=ns['_deck_mask_table'];ns['_deck_mask_table']=lambda *a:{}
    ds=base.funcs('benchmark/read_dropladder_0910.py',['cell','_copies_txt','main'],
                  dict(np=np,glob=glob,os=os,json=json,EL=0,RNG=15,DEPTH=2,NPOSE=8192,
                       ARMS=['R0D0E0F1'],SPPS=[4000000000],DIP=.9,ROOT=str(ROOT),
                       MESH='mfixbatteryi5_blperairframe'))
    output={}
    with tempfile.TemporaryDirectory(prefix='sionna-fix-probes-') as td:
        td=Path(td);ns['SHD']=str(td);ms['SHD']=str(td);ds['SHD']=str(td)
        ns['OUT']=str(td/'canyon.json');ds['OUT']=str(td/'drop.json')
        # Within-record metadata mismatch and complex128 nonfinite fields are now rejected.
        for label in ['metadata','nan128','nan64','missingmeta']:
            N=4096 if label=='missingmeta' else 8192
            for sh in range(2):
                idx=np.arange(sh,N,2);E=np.ones(idx.size,np.complex64 if label=='nan64' else complex)
                if sh==0 and label.startswith('nan'):E[0]=complex(float('nan'),0)
                kw=dict(idx=idx,E=E)
                if label!='missingmeta':kw['meta']=[-60,sh,2,16384 if label=='metadata' and sh==0 else N,
                                                    10000 if label=='metadata' and sh==1 else 19700]
                np.savez(td/f'{label}_el-60_{sh:02d}.npz',**kw)
            c,n=ns['load'](label,-60)
            output[label]=dict(idx_ok=c['idx_ok'],n_rows=c['n_rows'],n_expected=c['n_expected'],
                reported_nonfinite=c['n_nonfinite'],actual_nonfinite=int((~np.isfinite(c['E'])).sum()),
                dtype=str(c['E'].dtype),metadata_mismatch=c['meta_mismatch'])
        # Each record is internally consistent, but scene and free have different PRFs.
        for env in [False,True]:
            name=ns['stem'](4000000000,0,env)
            for sh in range(2):
                idx=np.arange(sh,8192,2)
                np.savez(td/f'{name}_el-60_{sh:02d}.npz',idx=idx,E=np.full(idx.size,2.+0j if env else 1.+0j),
                         meta=[-60,sh,2,8192,10000 if env else 19700],npaths=np.ones(idx.size),
                         n_dup=np.zeros(idx.size),nret=np.ones(idx.size),n_trunc=[0,2000000])
        with contextlib.redirect_stdout(io.StringIO()):ns['main']()
        j=json.loads(Path(ns['OUT']).read_text())
        output['cross_record_prf']=dict(free_prf_hz=19700,scene_prf_hz=10000,
            accepted_cells=list(j['by_el']['-60']['cells']),missing=j['by_el']['-60']['missing'])
        # Actual Hampel function, without importing plotting modules.
        fake=types.ModuleType('bake_outdoor')
        fake.hampel_mask=base.funcs(ROOT.parent/'team_meeting/teammeeting_0910/bake_outdoor.py',
                                   ['hampel_mask'],dict(np=np))['hampel_mask']
        prior=sys.modules.get('bake_outdoor');sys.modules['bake_outdoor']=fake
        bad=dict(E=np.ones(8192),idx_ok=False,n_unique=4096,n_rows=8192,n_expected=8192)
        try:
            t=real_table(lambda *args:(bad,2),lambda *args:'base',[-60],[('candidate',4000000000,1)])
        finally:
            if prior is None:sys.modules.pop('bake_outdoor',None)
            else:sys.modules['bake_outdoor']=prior
        output['baseline_rejected']='unavailable_ko' in t['-60']
        # Actual cell() and main() for each drop case, with an on-disk complete fixture.
        prefix='sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2_el+0'
        for case in ['fractional','partial','all_unmeasured','nan','metadata']:
            for sh in range(2):
                idx=np.arange(sh,8192,2);E=np.ones(idx.size,complex);D=np.full(idx.size,2)
                if case=='fractional':D[:]=sh+1
                if case=='partial' and sh==1:D[:]=-1
                if case=='all_unmeasured':D[:]=-1
                if case=='nan' and sh==0:E[0]=np.nan
                meta=[0,sh,2,16384 if case=='metadata' and sh==0 else 8192,
                      10000 if case=='metadata' and sh==1 else 19700]
                np.savez(td/f'{prefix}_{sh:02d}.npz',idx=idx,E=E,npaths=np.ones(idx.size),n_dup=D,meta=meta)
            buf=io.StringIO()
            with contextlib.redirect_stdout(buf),np.errstate(invalid='ignore'):ds['main']()
            doc=json.loads(Path(ds['OUT']).read_text())
            output['drop_'+case]=dict(n_rows=len(doc['rows']),skipped=doc['_meta']['skipped'],
                rows=doc['rows'],printed_fractional='?(1.5)' in buf.getvalue(),completed=True)
        # nret diagnostics must not depend on whether npaths was stored.
        z=types.SimpleNamespace()
        out=dict(E=np.ones(8192,complex),npaths=np.full(8192,-1),n_dup=np.zeros(8192),n_shards=2,
                 trunc=[dict(file='synthetic',stored=0,cap=2000000,recomputed=1)])
        r=ms['measure'](out,out)
        output['cap_without_npaths']=dict(stored_recomputed=1,
            summary_present='n_poses_near_cap_now' in r,summary=r.get('n_poses_near_cap_now'),
            preserved_raw_diagnostic=r['trunc_outdoor'])
        # Mutation probe: reintroduce the old short=D<2 bug in memory only.
        text=base.read('benchmark/read_dropladder_0910.py');tree=ast.parse(text);changed=0
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='short' for t in node.targets):
                node.value=ast.parse('D < 2',mode='eval').body;changed+=1
        assert changed==1
        tree=ast.fix_missing_locations(tree);mutated=ast.unparse(tree)
        real_cell=ds['cell']
        fixture=dict(E=np.ones(8192,complex),D=np.r_[np.full(4096,2),np.full(4096,-1)],P=np.ones(8192),
                     idx_ok=True,n_shards=2,files=[])
        ds['cell']=lambda *args:fixture
        with contextlib.redirect_stdout(io.StringIO()):ds['main']()
        before=json.loads(Path(ds['OUT']).read_text())['rows'][0]['n_short']
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main']
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'in-memory mutant','exec'),ds)
        with contextlib.redirect_stdout(io.StringIO()):ds['main']()
        after=json.loads(Path(ds['OUT']).read_text())['rows'][0]['n_short']
        m=old_module();original_read=m.read
        m.read=lambda p:mutated if Path(p).name=='read_dropladder_0910.py' else original_read(p)
        verdict=m.adversarial_check()
        output['test_mutation']=dict(scope='In-memory reverted short expression; no source files changed.',
            actual_main_short_before=before,actual_main_short_after=after,
            verification_claims_fixed=not verdict['defects_still_present']['unknown_dup_counted_as_short'],
            verification_status=verdict['status_ko'])
    return output


def statuses(c):
    t=c['tests'];p=c['published']
    return [dict(id=1,status='확인',evidence=f"실제 낙차 main 완료, 표시 {t['drop_fractional']['printed_fractional']}; 중앙값 {t['drop_fractional']['rows'][0]['n_dup_median']}"),
        dict(id=2,status='미완료 — 수정 대상 파일 불일치',evidence='read_0918B_0909는 수정됐으나 elevation_sweep_md.analyse의 저장값 합산은 유지'),
        dict(id=3,status='부분 수정',evidence='협곡 내부 메타데이터·complex128 유한값·기준선 거절은 확인; 대조 쌍 시간축과 낙차 판독기 검사는 남음'),
        dict(id=4,status='확인',evidence=f"부분 계측의 dip_equals_short={t['drop_partial']['rows'][0]['dip_equals_short']}"),
        dict(id=5,status='실행 확인 · 보고 내용과 검증 강도는 보완 필요',evidence=f"mode={c['builder']['mode']}, 이중 배율 없음={c['builder']['no_double_scale']}"),
        dict(id=6,status='핵심 문구 정정 확인',evidence='make_jobs_0924에 남은 수와 목록의 구분 반영; 반복의 정보 부재와 추가 눈금의 판별력 표현은 보완 필요')]


def findings(c):
    fs=[]
    def add(title,kind,evidence,fix,refs):
        fs.append(dict(title=title,kind=kind,evidence=evidence,fix=fix,
                       sources=[base.source(p,s) for p,s in refs]))
    m=c['cap']['merge_probe']
    add('주 원장 병합기를 다른 판독기로 잘못 대응해 미수정 상태를 완료로 보고했다','남은 기존 문제',
        f"현 elevation_sweep_md.analyse의 진단 블록에 실제 저장 샤드를 넣으면 {m['n_poses']}표본에서 "
        f"경고 {m['merge_n_trunc']}개를 합산하고, 저장 상한 {m['cap']}으로 재계산하면 {m['recomputed_n_trunc']}개다. "
        'read_0918B_0909.load/measure의 수정은 이 함수에 전달되지 않는다. 현재 주 원장에 해당 재고가 포함됐다는 주장은 하지 않는다. '
        '반환 수의 상한 근접 경고를 후보 잘림의 직접 증거와 구분한다.',
        'elevation_sweep_md.analyse의 해당 블록을 대상으로 수정하고, 그 실제 실행 경로에 저장값 영·현재 경고 양수인 샤드를 넣어 확인한다.',
        [('benchmark/elevation_sweep_md.py','n_tr += int(_nt[0])'),('benchmark/read_0918B_0909.py','_rec = int(np.count_nonzero')])
    t=c['tests'];a=t['cross_record_prf']
    add('장면·자유공간 사이의 시간축과 낙차 판독기 검증은 아직 빠져 있다','부분 수정의 잔여 범위',
        f"각 기록 안에서는 정상인 자유공간 {a['free_prf_hz']} Hz와 장면 {a['scene_prf_hz']} Hz를 실제 협곡 main이 "
        f"{len(a['accepted_cells'])}개 조건으로 발간했다. 서로 다른 시각의 값을 같은 인덱스로 빼는 셈이다. "
        f"낙차 main은 비유한 전계 입력에서도 {t['drop_nan']['n_rows']}개 행을 내고, "
        f"낙차 {t['drop_nan']['rows'][0]['n_dip']}개·일치 {t['drop_nan']['rows'][0]['dip_equals_short']}를 기록했다. "
        '메타데이터 불일치만 넣은 낙차 입력도 통과했다. 메타데이터 없는 연속 반쪽 입력을 온전하다고 처리하는 협곡 분기도 남아 있다. '
        '이 결과들은 합성 반례이며 현재 발간 자료의 손상으로 소급하지 않는다.',
        '한 기록 내부뿐 아니라 비교 쌍 사이의 N·PRF·인덱스와 실행 조건을 확인한다. 낙차와 동체 판독 경로에도 같은 입력 검증을 적용하고, 미기재 메타데이터는 근거 없이 정상으로 간주하지 않는다.',
        [('benchmark/read_canyonnull_0910.py','if sc["E"].size != fr["E"].size:'),
         ('benchmark/read_dropladder_0910.py','n_expected = int(_m[3])'),
         ('benchmark/read_canyonnull_0910.py','and (n_expected is None or idx.size == n_expected)')])
    a=t['nan64']
    add('새 비유한값 검사가 complex64 전계에서는 NaN을 놓친다','추가 발견 · 자료형 경계 반례',
        f"complex64 전계에 실제 비유한 표본 {a['actual_nonfinite']}개를 넣었지만 검사 결과는 "
        f"n_nonfinite={a['reported_nonfinite']}, idx_ok={a['idx_ok']}였다. Ecat.view(float)는 값을 변환하는 대신 "
        '메모리의 비트를 float64로 재해석한다. 현재 발간 샤드가 이 자료형으로 오염됐다는 발견은 아니다.',
        '복소 배열 자체에 np.isfinite를 적용해 표본 단위로 센다. 지원하지 않는 자료형이면 명시적으로 거절한다. 허용된 정밀도마다 같은 비유한값 검사를 검증한다.',
        [('benchmark/read_canyonnull_0910.py','Ecat.view(float)')])
    a=t['test_mutation']
    add('네 결함이 고쳐졌다는 반례 검증 중 하나는 생산 코드를 실행하지 않는다','추가 발견 · 검증의 거짓 통과 재현',
        'unknown_dup_counted_as_short 판정은 낙차 main을 부르지 않고 검토 빌더 안에서 have & (D<2)를 직접 다시 계산한다. '
        f"메모리에서 생산 main의 short를 옛 식으로 되돌리면 실제 오집계는 {a['actual_main_short_before']} → "
        f"{a['actual_main_short_after']}개가 되는데, 같은 변경 소스를 읽힌 검토 반례는 여전히 “{a['verification_status']}”라고 썼다. "
        '실제 생산 파일을 되돌린 것은 아니며 회귀 검사의 오류 탐지 능력을 별도로 시험한 결과다.',
        '실제 main 또는 main이 호출하는 순수 집계 함수를 반례로 실행한다. 입력만 교체하고, 기대 계산을 검증 대상 대신 실행하지 않는다. 검사마다 대상 함수와 통과 조건을 기록한다.',
        [('benchmark/review_latest_readers_0910.py','short_fixed=int'),
         ('benchmark/review_latest_readers_0910.py',"unknown_dup_counted_as_short=bool")])
    b=c['builder']
    add('regression으로 실행되지만 보고서는 여전히 미수정 결함이라고 서술한다','추가 발견 · 현재 발간 검토 문서의 불일치',
        f"빌더는 정상 완료했고 mode={b['mode']}, 대역은 {b['current_tip_hz']:.6f}와 {b['scaled_tip_hz']:.6f} Hz로 같다. "
        f"그러나 새로 생성한 제목은 “{b['current_atlas_finding']['title']}”였다. n_trunc를 버린다는 과거 설명도 현재 문제로 재출력한다. "
        '계산의 회귀 모드가 판정·제목·수정 순서에는 전달되지 않은 상태다. 철회한 보완 문구도 재생성된다.',
        '검토 항목에 발견 당시 상태와 현재 재검증 상태를 분리해 둔다. 본문·제목·권장 작업을 현재 상태에서 생성하고, 역사적 수치와 당시 소스는 별도 기록으로 보존한다.',
        [('benchmark/review_latest_readers_0910.py',"mode=('regression'"),
         ('benchmark/review_latest_readers_0910.py',"add('별도 분석기에서 고친"),
         ('benchmark/review_latest_readers_0910.py',"'새 load는 n_trunc를 읽지 않고")])
    a=t['drop_all_unmeasured'];b=t['cap_without_npaths']
    add('미계측을 표시하는 분기에도 기록이 사라지는 경로가 남아 있다','추가 발견 · 미수집 상태 보고 누락',
        f"전 자세의 n_dup가 미계측인 온전한 입력은 낙차 결과 {a['n_rows']}행·skipped {len(a['skipped'])}건으로 끝났다. "
        '오류 없이 종료된 것은 맞지만, 요청한 조건이 없어진 이유가 원장에 남지 않는다. '
        f"또 measure에 유효한 상한 재계산 {b['stored_recomputed']}건을 주어도 npaths가 미기록이면 "
        f"진단 요약 필드 존재 여부는 {b['summary_present']}다. 원시 trunc 기록은 보존되므로 완전 유실이라고 하지는 않는다.",
        '전부 미계측인 조건도 상태와 사유를 남긴다. 상한 진단 집계는 npaths의 유무와 독립적으로 수행하고, 요약 불능과 영 경고를 분리한다.',
        [('benchmark/read_dropladder_0910.py','if (D < 0).all():'),
         ('benchmark/read_0918B_0909.py','if (npa >= 0).any():')])
    return fs


def render(o):
    c=o['checks'];p=c['published'];j=str(OUT.relative_to(ROOT))
    lines=['# 수정 완료 주장 재검증 — 2026-09-11','',
        f"기준 커밋 `{o['_meta']['head']}` · 확인 {o['_meta']['checked_at_utc']}.",'',
        '전달받은 여섯 항목의 완료 여부를 실제 실행 경로에서 확인했다. 운영 코드와 기존 원장은 변경하지 않았다. '
        '반례는 임시 자료 또는 메모리 안의 변형으로 실행했으며 GPU 계산은 수행하지 않았다.', '',
        '[주피터 보고서](FIX_VERIFICATION_0911.ipynb) · [재계산 원장](../outputs/fix_verification_0911.json) · '
        '[생성기](../benchmark/review_fix_verification_0911.py)', '',
        '```bash','cd /workspace/sionna',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_fix_verification_0911.py",'```','',
        '## 전달된 완료표의 재검증','', '| 항목 | 현재 판정 | 근거 |','|---|---|---|']
    for r in o['statuses']:lines.append(f"| {r['id']} | {r['status']} | {r['evidence']} |")
    lines += ['',f"협곡 {p['n_canyon_cells']}개 조건과 낙차 {p['n_drop_cells']}개 조건의 발간 수를 원본 샤드 "
        f"{p['n_unique_shards']}개에서 재계산했다. 원본의 인덱스·전계 유한값·대조 시간축 검사는 통과했다. "
        '합성 반례의 실패를 이 발간 자료의 손상으로 소급하지 않는다.', '',
        '## 남은 문제와 추가 발견','']
    for i,f in enumerate(o['findings'],1):
        lines += [f"### {i}. {f['title']}",'','**분류:** '+f['kind'],'','**근거와 범위:** '+f['evidence'],'',
                  '**수정 제안:** '+f['fix'],'',f"원장: `{j}` → `findings[{i-1}]` 및 `checks`.",'']
        for s in f['sources']:
            target='../'+s['path'] if not Path(s['path']).is_absolute() else s['path']
            lines += [f"- [{Path(s['path']).name}:{s['line']}]({target}#L{s['line']})",'```python',s['quote'],'```','']
    lines += ['## 문면 보완','',
        '0924의 핵심 문장은 잔존 수와 사건 목록을 구분하도록 바뀌었다. 다만 되풀이에서 “정보가 안 나온다”는 설명은 '
        '“확률적 독립 표본을 추가하는 대조가 아니며 실행 재현성을 확인한다”로 한정하는 편이 정확하다. '
        '새 배율 눈금만 추가한다고 두 원인을 분리할 수 있는 것도 아니므로, 분리하려는 효과와 비교 조건을 별도로 정해야 한다.', '',
        '실행 성공, 지정 반례 통과, 실제 발간값 유지, 결함의 전체 해결은 각각 다른 확인이다. '
        '이번 검증은 추가 반례를 통해 적용 범위를 확인했으며, 물리적 정확성이나 실측 일치를 판정한 보고서가 아니다.', '']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'))
    from report_style import header,md,next_steps,build_notebook
    blocks=[header(num='수정 재검증',title='완료된 수정과 남은 실행 경로',
        did='전달된 완료표를 실제 판독기 실행과 원본 자료로 대조했다.',
        results=[f"완료 주장 {len(o['statuses'])}건의 상태를 구분했다 ⟨{j} : statuses⟩.",
                 f"원본 샤드 {p['n_unique_shards']}개로 발간 수를 검산했다 ⟨{j} : checks.published.n_unique_shards⟩.",
                 f"잔여 문제와 추가 발견 {len(o['findings'])}건을 기록했다 ⟨{j} : findings⟩."],
        method=[('실제 실행','임시 입력·출력으로 현재 main을 실행'),
                ('검증기 점검','메모리에서 옛 오류를 재도입해 반례 검사의 탐지력을 확인')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_fix_verification_0911.py"],
                   out=[j],runtime='CPU 한 코어, GPU 사용 없음'))]
    for i,f in enumerate(o['findings']):
        blocks.append(md(f"## {i+1}. {f['title']}",'',f['fix'],'',
            f"[실행 결과·원문·조건](FIX_VERIFICATION_0911.md) ⟨{j} : findings[{i}]⟩"))
    blocks.append(next_steps([
        ('실제 병합기와 모든 비교 쌍을 검증한다','완료 범위가 어긋난 부분의 수정','FIX_VERIFICATION_0911.md'),
        ('회귀 검사와 보고 문면을 현재 상태에 연결한다','실행 성공과 문제 해결의 구분','FIX_VERIFICATION_0911.md')]))
    build_notebook(str(NB),blocks,strict=True)


def main():
    base.digest(__file__);base.digest('benchmark/review_current_state_0911.py')
    c=dict(published=base.published(),cap=base.cap_census(),builder=verify_builder(),tests=tests())
    fs=findings(c);ss=statuses(c)
    out=dict(_meta=dict(generator='benchmark/review_fix_verification_0911.py',
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256=base.HASHES,scope='Actual current reader entry points and explicitly labelled synthetic/mutation probes.'),
        statuses=ss,checks=c,findings=fs)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    render(out)
    print(json.dumps(dict(statuses=ss,mutation=c['tests']['test_mutation'],merge=c['cap']['merge_probe']),ensure_ascii=False))


if __name__=='__main__':main()
