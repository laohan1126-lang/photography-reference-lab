"""Reuse a sealed local primary-source investigation, never a name-only lookup."""
import hashlib
import json
from pathlib import Path
import time

from PIL import Image

from .policy import digest
from .storage import atomic_write


MAX_AGE_SECONDS=86400


def file_sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceCache:
    def __init__(self,root:Path):self.root=root

    def key(self,project,model):
        from .verified_collection import scope_sha
        code=Path(__file__).parent
        return digest({'scope':scope_sha(project),'model':model,
                       'contract':{name:file_sha(code/name) for name in
                                   ('verified_collection.py','automatic_references.py','reference_cache.py')}})

    def seal(self,source,project,model):
        """May also explicitly seed from a preserved run; verify the original receipts."""
        from .automatic_references import SourceAssessment,parse_reference_page,trusted_images,assessment_prompt
        from .verified_collection import AntigravityCollectionAgent,NamePlan
        source=source.resolve();files={}
        def read(path):
            if path.is_symlink():raise ValueError('Cache evidence cannot be a symlink')
            path=path.resolve()
            if not path.is_relative_to(source):raise ValueError('Cache source escapes run')
            if path.stat().st_size>20*1024*1024:raise ValueError('Cache evidence too large')
            raw=path.read_bytes()
            files[str(path)]=hashlib.sha256(raw).hexdigest()
            return raw
        def load(path):return json.loads(read(path))
        info=load(source/'run-info.json')
        if info['model']!=model:raise ValueError('Cache model changed')
        created=float(info['started_at'])
        if not 0<=time.time()-created<=MAX_AGE_SECONDS:raise ValueError('Cache source expired')
        plan=NamePlan.model_validate(load(source/'name-plan.json')['plan'])
        report=load(source/'reference-research/report.json')
        refs=report['references']
        if not refs or len(refs)>8 or len({r['asset_sha'] for r in refs})!=len(refs):raise ValueError('Invalid cache references')
        receipts=[(p,json.loads(p.read_text('utf8'))) for p in source.glob('agent-*.json')]

        def receipt(result_type,value,*,prompt_sha=None,evidence=None):
            for path,entry in receipts:
                binding=entry.get('binding') or {}
                if (entry.get('result')!=value or binding.get('model')!=model
                        or binding.get('schema_sha256')!=digest(result_type.model_json_schema())
                        or (prompt_sha and binding.get('prompt_sha256')!=prompt_sha)):
                    continue
                inputs=binding.get('inputs',{})
                if result_type is NamePlan and inputs:continue
                if evidence is not None:
                    if evidence.get('project')!=project or evidence.get('known_name_hypotheses')!=plan.model_dump():continue
                    supplied=evidence.get('downloaded_images',[])
                elif result_type is SourceAssessment:
                    by_path={str(Path(r['path']).resolve()):r for r in refs}
                    if any(name not in by_path for name in inputs):continue
                    # run() binds reference_paths first and its primary image last.
                    names=list(inputs);names=names[-1:]+names[:-1]
                    supplied=[{k:by_path[name][k] for k in ('asset_sha','path','image_url','observed_image_url','page_image_context')} for name in names]
                else:supplied=[]
                if result_type is SourceAssessment:
                    bound={'project':project,'known_name_hypotheses':plan.model_dump(),'source_page':page,'downloaded_images':supplied}
                    if evidence is not None and evidence!=bound:continue
                    if binding.get('prompt_sha256')!=hashlib.sha256(assessment_prompt(bound).encode()).hexdigest():continue
                    if {str(Path(r['path']).resolve()):r['asset_sha'] for r in supplied}!=inputs:continue
                    if any(r['page_image_context'] not in page['images'] or r['observed_image_url']!=r['page_image_context']['url'] for r in supplied):continue
                opened={str(Path(r['path']).resolve()) for r in entry['reads'] if r['tool']=='view_file' and r['state']=='DONE'}
                if opened!=set(inputs) or any(r['tool'] not in ('view_file','finish') for r in entry['reads']):continue
                key=binding['prompt_sha256'][:16]
                successes=[]
                for attempt in source.glob('attempt-'+key+'*.json'):
                    record=load(attempt);terminal=record.get('result') or {}
                    if (record.get('state')=='finished' and record.get('termination')=='returned' and record.get('exit_code')==0
                            and terminal.get('status')=='SUCCESS' and not terminal.get('denied_actions')
                            and not record.get('validation_failure') and record.get('tools')==entry['reads']):
                        value_in_terminal=terminal.get('structured_output')
                        if value_in_terminal is None:
                            raw=terminal.get('response','').strip()
                            if raw.startswith('```'):raw=raw.split('\n',1)[1].rsplit('```',1)[0].strip()
                            try:value_in_terminal=json.loads(raw)
                            except ValueError:continue
                        try:
                            if result_type.model_validate(value_in_terminal).model_dump()==value:successes.append(attempt)
                        except ValueError:continue
                if not successes:continue
                read(path)
                for name,sha in inputs.items():
                    image=Path(name).resolve()
                    if not image.is_relative_to(source/'reference-research/images') or hashlib.sha256(read(image)).hexdigest()!=sha:
                        raise ValueError('Reference evidence bytes/path changed')
                    with Image.open(image) as im:
                        if min(im.size)<240 or im.width*im.height>40_000_000:raise ValueError('Reference dimensions changed')
                        im.verify()
                return inputs
            raise ValueError('No successful bound source receipt')

        # Rebuild the unchanged name-planning prompt without running a model.
        probe=object.__new__(AntigravityCollectionAgent);prompts=[]
        probe.run=lambda prompt,*args,**kwargs:prompts.append(prompt) or plan
        probe._plan_fresh(project)
        receipt(NamePlan,plan.model_dump(),prompt_sha=hashlib.sha256(prompts[0].encode()).hexdigest())
        verified={}
        for page_record in report['pages']:
            if page_record.get('status')!='trusted':continue
            page_files=list((source/'reference-research').glob('source-*.json'))
            matches=[p for p in page_files if json.loads(p.read_text('utf8')).get('url')==page_record['url']]
            if len(matches)!=1:raise ValueError('Ambiguous source page evidence')
            page=load(matches[0]);raw=read(matches[0].with_suffix('.html'))
            if parse_reference_page(page['url'],raw.decode('utf8',errors='replace'))!=page:raise ValueError('Source page evidence changed')
            assessment=SourceAssessment.model_validate(page_record['assessment'])
            inputs=receipt(SourceAssessment,assessment.model_dump(),evidence=page_record.get('evidence'))
            supplied=[]
            for ref in refs:
                if ref['page_url']!=page['url']:continue
                path=str(Path(ref['path']).resolve())
                if inputs.get(path)!=ref['asset_sha'] or ref.get('page_image_context') not in page['images']:
                    raise ValueError('Reference lacks original image/source binding')
                supplied.append(ref)
            for ref in trusted_images(assessment,page,plan,supplied):verified[ref['asset_sha']]=ref
        for ref in refs:
            trusted=verified.get(ref['asset_sha'])
            if not trusted or any(trusted.get(k)!=ref.get(k) for k in ('label','authority','page_url','license_quote','work_quote')):
                raise ValueError('Reference no longer meets current source rules')
        entry={'version':1,'key':self.key(project,model),'created_at':created,'project':project,'model':model,
               'source':str(source),'plan':plan.model_dump(),'references':refs,'files':files}
        entry['seal_sha256']=digest(entry)
        self.root.mkdir(parents=True,exist_ok=True)
        atomic_write(self.root/(entry['key']+'.json'),json.dumps(entry,ensure_ascii=False,indent=2).encode('utf8'))
        return entry

    def load(self,project,model):
        key=self.key(project,model);path=self.root/(key+'.json')
        if not path.exists():return None
        try:
            entry=json.loads(path.read_text('utf8'));seal=entry.pop('seal_sha256')
            if (entry['version']!=1 or entry['key']!=key or digest(entry)!=seal or entry['project']!=project
                    or entry['model']!=model or not 0<=time.time()-entry['created_at']<=MAX_AGE_SECONDS):return None
            source=Path(entry['source']).resolve()
            required={str(source/n) for n in ('run-info.json','name-plan.json','reference-research/report.json')}
            required.update(str(Path(r['path']).resolve()) for r in entry['references'])
            if not entry['references'] or not required.issubset(entry['files']):return None
            for name,sha in entry['files'].items():
                item=Path(name)
                if item.is_symlink():return None
                item=item.resolve()
                if not item.is_relative_to(source) or file_sha(item)!=sha:return None
            report=json.loads((source/'reference-research/report.json').read_text('utf8'))
            plan=json.loads((source/'name-plan.json').read_text('utf8'))['plan']
            if report['references']!=entry['references'] or plan!=entry['plan']:return None
            entry['seal_sha256']=seal
            return entry
        except (OSError,ValueError,KeyError,TypeError):return None

    def restore(self,entry,research):
        current=self.load(entry['project'],entry['model'])
        if current is None or current['seal_sha256']!=entry['seal_sha256']:
            raise ValueError('Reference evidence changed between planning and preparation')
        references=[]
        for ref in entry['references']:
            source=Path(ref['path']);raw=source.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=ref['asset_sha']:raise ValueError('Cached reference changed during restore')
            target=research.folder/'images'/(ref['asset_sha']+source.suffix.lower())
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and target.read_bytes()!=raw:raise ValueError('Immutable reference copy conflict')
            if not target.exists():atomic_write(target,raw)
            references.append({**ref,'path':str(target.resolve())})
        research.references=references
        research.seen.update(ref['page_url'] for ref in references)
        research.cached_from={'source':entry['source'],'seal_sha256':entry['seal_sha256'],'created_at':entry['created_at']}
        research.save()
