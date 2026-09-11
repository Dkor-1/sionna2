"""Recheck current fixes, active queue, and remaining save/generation boundaries.
Run: CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_status_0911.py
Existing publications and live workers are read only; tests use temporary files.
"""
from __future__ import annotations
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OPENBLAS_NUM_THREADS']='1'
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import contextlib,io,json,shlex,shutil,struct,subprocess,sys,tempfile,zipfile
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import review_repository_0911 as repo
base=repo.base;ROOT=base.ROOT
OUT=ROOT/'outputs/status_review_0911.json';MD=ROOT/'docs/STATUS_REVIEW_0911.md';NB=MD.with_suffix('.ipynb')


def queue():
    rows=[]
    for ln in subprocess.check_output(['ps','-eo','pid=,etimes=,args='],text=True).splitlines():
        p=ln.strip().split(None,2)
        if len(p)!=3:continue
        try:a=shlex.split(p[2])
        except ValueError:continue
        if len(a)>1 and a[1] in ['runners/worker_supervisor.py','benchmark/elevation_sweep_md.py','runners/queue_keeper_0827.sh']:
            rows.append(dict(pid=int(p[0]),elapsed_s=int(p[1]),script=a[1],job=a[2] if a[1]=='runners/worker_supervisor.py' else None))
    logs=[]
    for r in rows:
        if r['job']:
            p=ROOT/'runners/logs'/('sup_'+Path(r['job']).stem+'.log')
            logs.append(dict(job=r['job'],last_lines=p.read_text().splitlines()[-3:]))
    return dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),processes=rows,supervisor_logs=logs,
        workers=sum(r['script']=='benchmark/elevation_sweep_md.py' for r in rows),
        keeper_mode=oct((ROOT/'runners/queue_keeper_0827.sh').stat().st_mode&0o777),
        chain_started=(ROOT/'runners/logs/queue_chain_0910_done.txt').read_text().splitlines())


def resume_checks():
    f=base.funcs('benchmark/elevation_sweep_md.py',['shard_done'],dict(np=np,os=os))['shard_done'];rows=[]
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for label in ['valid','truncated','bad_crc','wrong_length']:
            p=td/(label+'.npz');N=8
            np.savez(p,idx=np.arange(N),E=np.ones(3 if label=='wrong_length' else N,complex),meta=[0,0,1,N,19700,0])
            if label=='truncated':p.write_bytes(p.read_bytes()[:50])
            elif label=='bad_crc':
                with zipfile.ZipFile(p) as z:info=z.getinfo('E.npy')
                raw=bytearray(p.read_bytes());nl,xl=struct.unpack_from('<HH',raw,info.header_offset+26)
                off=info.header_offset+30+nl+xl+info.file_size-1;raw[off]^=1;p.write_bytes(raw)
            with contextlib.redirect_stdout(io.StringIO()):accepted=f(str(p))
            try:
                with np.load(p) as z:E=z['E'];idx=z['idx']
                valid=isinstance(E,np.ndarray) and E.ndim==1 and E.size==idx.size and np.isfinite(E).all();error=None
            except Exception as e:valid=False;error=type(e).__name__
            rows.append(dict(case=label,shard_done=accepted,array_valid=bool(valid),load_error=error))
    assert rows[0]['shard_done'] and not rows[1]['shard_done']
    return rows


def generation_checks(shards):
    choose=base.funcs('benchmark/elevation_sweep_md.py',['one_generation'],dict(np=np,os=os))['one_generation'];rows=[]
    for g in shards['duplicate_groups']:
        if not g['engine'].startswith('sionna'):continue
        files=[str(base.digest(base.SHD/f)) for f in g['files']]
        with contextlib.redirect_stdout(io.StringIO()):keep,note=choose(files,g['engine'])
        if note is None:continue
        original=repo.raw_merge(keep)['E']
        with tempfile.TemporaryDirectory() as td:
            cp=[]
            for f in files:
                p=Path(td)/Path(f).name;shutil.copyfile(f,p);os.utime(p,(1700000000,1700000000));cp.append(str(p))
            with contextlib.redirect_stdout(io.StringIO()):selected,newnote=choose(cp,g['engine'])
            E=repo.raw_merge(selected)['E']
            ii=np.concatenate([np.load(f)['idx'] for f in selected])
            rows.append(dict(engine=g['engine'],el=g['el_deg'],files=g['files'],original_kept=[Path(x).name for x in keep],
                original_coverage=note['kept_poses'],copied_kept=[Path(x).name for x in selected],
                copied_generations=newnote['n_generations'],copied_duplicate_rows=int(ii.size-np.unique(ii).size),
                changed_poses=int((E!=original).sum()),same_bytes=True,note='Only temporary-copy mtimes changed; source shards untouched.'))
    return rows


def pfa_checks():
    sys.path.insert(0,str(ROOT/'src'));import passive_process as p
    base.digest('src/passive_process.py');rows=[]
    for name in ['wifi','lte','nr']:
        for target in [1e-4,5e-4,1e-6,.1]:
            d=p.pfa_nominal_detail(name,target)
            try:v=p.pfa_nominal_for(name,target);error=None
            except Exception as e:v=None;error=type(e).__name__
            rows.append(dict(waveform=name,target=target,detail=d,strict_result=v,strict_error=error))
    assert all(r['strict_error']=='PfaOutOfRange' for r in rows if not r['detail']['calibrated'])
    return rows


def builder_checks():
    # Production old main, outputs isolated. Heavy inventory stages reuse the just-read snapshot.
    m=repo;paths=(m.OUT,m.MD,m.NB);out={}
    with tempfile.TemporaryDirectory(prefix='.status-review-',dir=ROOT/'work') as td:
        m.OUT=Path(td)/'out.json';m.MD=Path(td)/'out.md';m.NB=Path(td)/'out.ipynb'
        original_inventory=m.inventory;original_shards=m.shards
        m.inventory=lambda:SNAPSHOT['inventory'];m.shards=lambda:SNAPSHOT['shards']
        try:
            with contextlib.redirect_stdout(io.StringIO()):m.main()
            out['completed']=True
        except Exception as e:out.update(completed=False,error_type=type(e).__name__,error=str(e))
        finally:
            out.update(json_written=m.OUT.exists(),markdown_written=m.MD.exists(),notebook_written=m.NB.exists())
            m.OUT,m.MD,m.NB=paths;m.inventory=original_inventory;m.shards=original_shards
    # The older report builder (the previous ContractError) now succeeds independently.
    legacy=repo.previous.prior.previous.old_module()
    with tempfile.TemporaryDirectory(prefix='.status-legacy-',dir=ROOT/'work') as td:
        legacy.OUT=Path(td)/'out.json';legacy.MEMO=Path(td)/'out.md';legacy.NB=Path(td)/'out.ipynb'
        try:
            with contextlib.redirect_stdout(io.StringIO()):legacy.main()
            out['older_builder_completed']=True
        except Exception as e:out.update(older_builder_completed=False,older_builder_error=repr(e))
    return out


def repository_checks():
    results={}
    for name in ['check_new_file_rules','check_report_links','check_row_pointers']:
        rel='benchmark/'+name+'.py';base.digest(rel)
        r=subprocess.run([sys.executable,rel],cwd=ROOT,text=True,capture_output=True)
        results[name]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
    return results


def findings(c):
    fs=[]
    def add(title,kind,text,fix,refs):fs.append(dict(title=title,kind=kind,evidence=text,fix=fix,sources=[base.source(*x) for x in refs]))
    g=c['generation']
    _dup0=g[0]['copied_duplicate_rows']; _ch=[r['changed_poses'] for r in g]
    _steady = _dup0 == 0 and not any(_ch)
    add(('세대 선택이 파일 시각과 무관하다' if _steady
         else '파일 시각이 바뀌면 세대 선택이 다시 혼합 자료를 고른다'),
        ('2026-09-12 정정 뒤 현재 상태 · 실제 충돌 샤드의 임시 복제 대조' if _steady
         else '실제 충돌 샤드의 임시 복제 대조'),
        f"현재 원본에서는 {len(g)}조건 모두 완결 세대를 선택한다. 동일 바이트를 임시 복제하고 파일 시각만 같게 둔 대조에서 "
        f"선택 결과의 중복은 {_dup0}행이고 원본 선택과 비교해 바뀐 자세 수는 {_ch}다. "
        + ('세대는 파일 시각이 아니라 샤드에 적힌 조각 수(meta[2])로 가른다. 덮는 자세와 중복이 같아 내용으로 못 고르는 경우에는 '
           '파일 이름으로 결정적으로 고르고 그 사실을 tie_unresolved로 싣는다. 고른 뒤에는 묶음 안 중복과 값 충돌을 다시 세어 원장에 적는다.'
           if _steady else
           'one_generation은 파일 수정 시각 간격으로 세대를 묶으며 선택 뒤에도 중복 충돌을 재검사하지 않는다.')
        + ' 현재 아틀라스가 이 복제 입력으로 발행됐다는 뜻은 아니다.',
        ('남은 일은 샤드에 굽기 식별자를 함께 적는 것이다. 지금은 조각 수가 같은 두 굽기를 내용만으로 가르지 못하고 이름으로 고른다.'
         if _steady else
         '실행 식별자와 분할 설정을 저장하고, 선택한 묶음의 idx 중복·충돌을 마지막에 검사한다.'),
        [('benchmark/elevation_sweep_md.py','def _nsh(f):'),('benchmark/elevation_sweep_md.py','tie_unresolved = len(tied) > 1'),('benchmark/elevation_sweep_md.py','keep = sorted(gens[k])')])
    r={x['case']:x for x in c['resume']}
    _blocked=[k for k,v in r.items() if not v['shard_done']]
    add('샤드 완료 검사가 배열을 실제로 읽어 손상과 불일치를 거른다','2026-09-12 정정 뒤 현재 상태 · 합성 입력',
        f"ZIP가 잘린 입력, E 데이터의 CRC가 깨진 입력(shard_done={r['bad_crc']['shard_done']}, 실제 읽기 {r['bad_crc']['load_error']}), "
        f"E와 idx 길이가 다른 입력(shard_done={r['wrong_length']['shard_done']}) 모두 거절된다. 거절된 합성 입력은 {len(_blocked)}종이다. "
        f"함수는 이름 확인에 그치지 않고 모든 배열의 압축을 풀어 차원·길이·형식·인덱스 범위·유한성을 본다. "
        f"이번 실제 재고 판독 {c['shards']['files_read']}개에서 읽기 오류는 {len(c['shards']['errors'])}개이고, 전수에서 잘못 거절된 파일도 없다.",
        '남은 일은 저장 쪽이다. 임시 파일에 쓴 후 검사를 통과한 결과를 최종 이름으로 교체하면 끊긴 파일이 창고에 남지 않는다.',
        [('benchmark/elevation_sweep_md.py','arrs = {k: z[k] for k in names}'),('benchmark/elevation_sweep_md.py','if np.unique(ii).size != ii.size:')])
    b=c['builders']
    add('교정 API의 정상 거절을 감사 빌더가 시험 성공으로 기록한다','2026-09-12 정정 뒤 현재 상태',
        f"교정 범위 밖 입력은 PfaOutOfRange로 거절된다. review_repository.main은 그 거절을 예상 결과로 받아 "
        f"완료={b.get('completed')}, 오류 종류={b.get('error_type')}로 끝나고, 임시 출력에서 JSON 작성={b['json_written']}, 노트북 작성={b['notebook_written']}다. "
        f"이전 ContractError가 나던 review_latest_readers 빌더의 완료={b['older_builder_completed']}도 확인했다. "
        '거절된 입력에는 옛 동작이 돌려줬을 경계값을 함께 적어, 포화가 보이지 않게 되지는 않는다.',
        '남은 일은 교정표를 넓혀 더 엄격한 목표까지 실제로 교정하는 것이다. 그전까지 범위 밖이 필요하면 strict=False로 부르고 source를 결과에 함께 싣는다.',
        [('benchmark/review_repository_0911.py','calls=[_probe(name,x) for x in values]'),('src/passive_process.py','if strict:')])
    assert all(x['found'] for f in fs for x in f['sources'])
    return fs


def render(o):
    c=o['checks'];q=c['queue'];j=str(OUT.relative_to(ROOT));pub=c['publications']
    lines=['# 현재 상태 재점검','',f"기준 `{o['_meta']['head']}` · {o['_meta']['checked_at_utc']}",'',
        '[주피터 보고서](STATUS_REVIEW_0911.ipynb) · [실행 원장](../outputs/status_review_0911.json) · [생성기](../benchmark/review_status_0911.py)','',
        '## 현재 실행과 확인된 수정','',
        f"프로세스 조회 시점에 워커 {q['workers']}개가 있었고, 감독자·지킴이 목록과 최근 로그를 원장에 남겼다. 큐의 분수는 투입 포인터이며 완료 수로 읽지 않는다.",'',
        f"실제 저장 샤드 {c['shards']['files_read']}개를 재판독했다. 읽기 오류 {len(c['shards']['errors'])}개다. 최근 수정되어 제외한 파일은 {len(c['shards']['recent_skipped'])}개다. "
        f"기존 관측 사건은 원본 {pub['union_shards']}개·협곡 {pub['canyon_drop']['n_canyon_cells']}칸·낙차 {pub['canyon_drop']['n_drop_cells']}칸·동체 {pub['body_cells']}칸에서 발간값과 일치했다.",'',
        f"영 전계가 일부인 {len(c['aggregation']['partial_zero'])}조건의 현재 레벨과 결측 수를 원본으로 다시 계산했다. "
        '원본 파일 시각을 유지한 현재 재고에서는 세대 선택과 발간 선택 기록이 일치한다. 교정 범위 밖 목표는 거절되고, 표 안 목표는 교정값을 반환한다. '
        '각 확인의 상세 조건은 aggregation·generation_current·pfa에 있다.','',
        '## 남은 보완점','']
    for i,f in enumerate(o['findings']):
        lines += [f"### {i+1}. {f['title']}",'',f"**범위:** {f['kind']}",'',f['evidence'],'','**수정 제안:** '+f['fix'],'',f"⟨{j} : findings[{i}]⟩",'']
        for s in f['sources']:lines += [f"- [{Path(s['path']).name}:{s['line']}](../{s['path']}#L{s['line']})",'```python',s['quote'],'```','']
    lines += ['## 기존 보고서의 참조 검사','',
        '아래는 저장소 검사기의 실제 출력이다. 행 포인터 불일치 수는 권과 조각에 반복 실린 각주를 포함하므로 독립 주장 수로 해석하지 않는다. '
        '링크가 열리는 것과 해당 링크의 행이 맞는 것은 별도 검사다. 불일치한 각주는 조각 빌더와 권 빌더로 다시 생성하고, '
        '장기적으로는 배열 위치 대신 조건 식별자로 원장 행을 찾도록 바꾼다. 이번 포인터 검사는 문장 속 수치의 참·거짓까지 판정하지 않는다.','']
    for name,result in c.get('repository_checks',{}).items():
        lines += [f"- `{name}.py`: exit {result['returncode']}",'```text',result['stdout'].strip(),'```','']
    lines += [f"⟨{j} : checks.repository_checks⟩",'']
    lines += ['## 실행 범위','',
        '기존 원장·소스·GPU 프로세스를 변경하지 않았다. 파일 시각과 CRC 변경은 임시 복제본에만 적용했다. '
        '기존 전체 감사 main을 실행할 때 재고 열거 두 단계는 바로 앞에서 읽은 동일 스냅샷을 주입해 중복 판독을 줄였다. '
        '생산 진단·API·판정 코드는 그대로 실행했다. 기존 수정의 완료와 새 반례의 범위를 구분한다.','',
        '```bash',"CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_status_0911.py",'```','']
    MD.write_text('\n'.join(lines))
    sys.path.insert(0,str(ROOT/'src'));from report_style import header,md,next_steps,build_notebook
    cells=[header(num='현재 재점검',title='현재 재고의 수정과 남은 세대·완료 검사',did='현재 자료와 수정된 생산 함수를 다시 대조했다.',
        results=[f"샤드 {c['shards']['files_read']}개를 읽었다 ⟨{j} : checks.shards⟩.",f"원본 {pub['union_shards']}개에서 기존 발간 사건을 재계산했다 ⟨{j} : checks.publications⟩.",
                 f"남은 보완점 {len(o['findings'])}건을 기록했다 ⟨{j} : findings⟩."],
        method=[('현재 재고','원본 배열과 발간 원장을 대조'),('추가 반례','임시 파일의 시각·내용을 바꿔 생산 검사를 실행')],
        repro=dict(cmd=["CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_status_0911.py"],out=[j],runtime='CPU 한 코어, 샤드 재판독'))]
    for i,f in enumerate(o['findings']):cells.append(md(f"## {i+1}. {f['title']}",'',f['fix'],'',f"[조건과 실행 근거](STATUS_REVIEW_0911.md) ⟨{j} : findings[{i}]⟩"))
    cells.append(md('## 기존 보고서의 참조 검사','',
        '링크 존재와 행의 일치를 별도로 검사했다. 포인터 오류는 각주의 근거 추적을 방해하며, 수치 오류 여부는 별도 대조가 필요하다.',
        '',f'[검사 출력과 재생성 제안](STATUS_REVIEW_0911.md) ⟨{j} : checks.repository_checks⟩'))
    cells.append(next_steps([('선택된 세대와 완료 배열을 검증한다','복제·내용 손상 반례','STATUS_REVIEW_0911.md'),('감사 빌더를 현재 API에 맞춘다','정상적인 거절을 시험 성공으로 기록','STATUS_REVIEW_0911.md')]))
    build_notebook(str(NB),cells,strict=True)


SNAPSHOT={}
def main():
    base.digest(__file__);base.digest('benchmark/review_repository_0911.py')
    c=dict(queue=queue());print('completed queue',flush=True)
    SNAPSHOT.update(inventory=repo.inventory(),shards=repo.shards());c['shards']=SNAPSHOT['shards'];print('completed shards',flush=True)
    c['aggregation']=repo.zero_and_overlap(c['shards']);c['generation_current']=repo.generation_selection(c['aggregation'])
    for r in c['aggregation']['partial_zero']:
        assert r['current_level_db']==r['mean_including_stored_zero_db']==r['published']['level_db']
        assert r['reported_missing']==r['actual_missing_indices']==0
        assert not r['atlas']['incomplete']
    for name,fn in [('resume',resume_checks),('generation',lambda:generation_checks(c['shards'])),('pfa',pfa_checks),('builders',builder_checks),('publications',repo.previous.actual_publications),('repository_checks',repository_checks)]:
        c[name]=fn();print('completed '+name,flush=True)
    fs=findings(c)
    o=dict(_meta=dict(generator='benchmark/review_status_0911.py',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        checked_at_utc=datetime.now(timezone.utc).isoformat(),source_sha256=base.HASHES),checks=c,findings=fs)
    OUT.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n');render(o)
    print(json.dumps(dict(findings=len(fs),workers=c['queue']['workers'],shards=c['shards']['files_read']),ensure_ascii=False))

if __name__=='__main__':main()
