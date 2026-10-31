"""Offline immutable-source, model completeness and CPU-QA boundary checks."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SPEC=importlib.util.spec_from_file_location('complete_models',Path(__file__).with_name('prepare_complete_models.py'))
builder=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(builder)


def sha(value):return hashlib.sha256(value).hexdigest()
def git_sha(value):return hashlib.sha1(f'blob {len(value)}\0'.encode()+value).hexdigest()


def metadata():
    payloads={name:b'{}' for name in ('config.json','generation_config.json','tokenizer_config.json',
               'tokenizer.json','speech_tokenizer/config.json','speech_tokenizer/preprocessor_config.json')}
    payloads.update({'model.safetensors':b'fake model bytes','speech_tokenizer/model.safetensors':b'fake tokenizer bytes'})
    siblings=[]
    for name,value in payloads.items():
        row={'rfilename':name,'size':len(value),'blobId':git_sha(value)}
        if name.endswith('.safetensors'):row['lfs']={'size':len(value),'sha256':sha(value)}
        siblings.append(row)
    return {'sha':'a'*40,'siblings':siblings},payloads


class CompleteModelsTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)

    def opener(self,data):return lambda request,timeout:io.BytesIO(json.dumps(data).encode())

    def test_only_fixed_official_repositories_resolve_once_to_immutable_commits(self):
        data,_=metadata();calls=[]
        def opener(request,timeout):calls.append(request.full_url);return io.BytesIO(json.dumps(data).encode())
        plan=builder.resolve_qwen('qwen',opener=opener)
        self.assertEqual(len(calls),1)
        self.assertIn('/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice/revision/main?blobs=true',calls[0])
        self.assertEqual(plan['revision'],'a'*40)
        self.assertEqual(plan['model_dir'],'qwen-customvoice')
        self.assertTrue(next(r for r in plan['files'] if r['name']=='model.safetensors')['sha256'])
        with self.assertRaises(ValueError):builder.resolve_qwen('untrusted-repository',opener=opener)
        self.assertEqual(len(calls),1)

    def test_required_generation_and_speech_tokenizer_assets_cannot_be_omitted(self):
        data,_=metadata()
        for name in ('generation_config.json','tokenizer_config.json','speech_tokenizer/preprocessor_config.json',
                     'model.safetensors','speech_tokenizer/model.safetensors','tokenizer.json'):
            damaged={**data,'siblings':[row for row in data['siblings'] if row['rfilename']!=name]}
            with self.subTest(name=name),self.assertRaises(ValueError):
                builder.resolve_qwen('qwen',opener=self.opener(damaged))
        for revision in ('main','b'*39,'Z'*40,None):
            with self.subTest(revision=revision),self.assertRaises(ValueError):
                builder.resolve_qwen('qwen',opener=self.opener({**data,'sha':revision}))

    def test_metadata_rejects_ambiguous_names_missing_hashes_and_excessive_sizes(self):
        data,_=metadata()
        for case in ('collision','hash','size'):
            bad=copy.deepcopy(data)
            if case=='collision':bad['siblings'].append({**bad['siblings'][0],'rfilename':'CONFIG.JSON'})
            if case=='hash':bad['siblings'][0]['blobId']='not a SHA1'
            if case=='size':bad['siblings'][0]['size']=9*1024**3
            with self.subTest(case=case),self.assertRaises(ValueError):builder.resolve_qwen('qwen',opener=self.opener(bad))
        for name in ('../escape.json','/absolute.json','speech_tokenizer/../../escape.json','bad\\file.json','url:https.json'):
            self.assertFalse(builder._model_file(name))

    def test_download_checks_both_lfs_sha256_and_small_git_blob_identity(self):
        payload=b'pinned bytes'
        for index,record in enumerate(({'name':'model.safetensors','size':len(payload),'sha256':sha(payload)},
                                       {'name':'config.json','size':len(payload),'git_blob_sha1':git_sha(payload)})):
            target=self.root/f'file-{index}'
            result=builder._download_record('https://huggingface.co/fixed',target,record,opener=lambda request,timeout:io.BytesIO(payload))
            self.assertEqual(result['sha256'],sha(payload));self.assertEqual(target.read_bytes(),payload)
            with self.assertRaises(FileExistsError):builder._download_record('https://huggingface.co/fixed',target,record)
        target=self.root/'bad'
        with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
            builder._download_record('https://huggingface.co/fixed',target,{'size':len(payload),'sha256':'0'*64},
                                     opener=lambda request,timeout:io.BytesIO(payload))
        self.assertFalse(target.exists());self.assertFalse(list(self.root.glob('*.part')))

    def test_prepare_records_the_complete_plan_before_any_weight_download(self):
        data,payloads=metadata()
        plans={engine:builder.resolve_qwen(engine,opener=self.opener(data)) for engine in builder.REPOSITORIES}
        destination=self.root/'extras';observed=[]
        def assert_plan(*args,**kwargs):
            self.assertTrue((destination/'EXTRA-MODEL-PLAN.json').is_file());observed.append(True);return {}
        native=SimpleNamespace(MODEL_SIZE=1,MODEL_SHA256='0'*64,MODEL_URL='https://github.com/fixed',MODEL_REVISION='b'*40,
            ASR_REPOSITORY='Systran/faster-whisper-base',ASR_REVISION='c'*40,ASR_FILES=[],prepare=assert_plan,prepare_asr=assert_plan)
        def download(url,path,record):
            self.assertTrue((destination/'EXTRA-MODEL-PLAN.json').is_file())
            self.assertIn('/resolve/'+'a'*40+'/',url);self.assertNotIn('/resolve/main/',url)
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payloads[record['name']])
            return {**record,'sha256':sha(payloads[record['name']])}
        with patch.object(builder,'native_preparer',return_value=native),patch.object(builder,'resolve_qwen',side_effect=lambda e:plans[e]),patch.object(builder,'_download_record',side_effect=download):
            builder.prepare(destination)
        self.assertEqual(len(observed),2)
        for engine in builder.REPOSITORIES:
            marker=json.loads((destination/'app/.data/models'/(engine+'.ready')).read_text())
            self.assertFalse(marker['cpu_synthesis_tested']);self.assertTrue(marker['source_weights_verified'])
        with self.assertRaises(FileExistsError):builder.prepare(destination)

    def qa_fixture(self):
        root=self.root/'extras';root.mkdir();builder.write_json(root/'EXTRA-PACK-OWNER.json',builder.OWNER)
        for engine in builder.REPOSITORIES:builder.write_json(root/'app/.data/models'/(engine+'.ready'),{'model':engine})
        builder.write_json(root/'runtime-qwen/VOICE-STUDIO-QWEN.json',{'tested_device':'cpu'})
        native=builder.native_preparer()
        report={'format':'voice-studio-extra-model-cpu-qa-v1','platform':'win32',
            'qwen_model_markers_sha256':builder._marker_hashes(root),
            'runtime_manifest_sha256':builder.sha256(root/'runtime-qwen/VOICE-STUDIO-QWEN.json'),
            'actual_application_adapter_tested':True,'main_runtime_heavy_qwen_imports':False,
            'gpu_inference_test':'not_run','target_30x_guaranteed':False,'private_voice_library_decoded':False,
            'qwen_customvoice':{'requests':[{'speaker':name,'valid_pcm_audio':True,'device':'cpu','audio_seconds':2} for name in builder.SPEAKERS]},
            'qwen_base':{'valid_pcm_audio':True,'device':'cpu','audio_seconds':2,'public_reference_sha256':builder.REFERENCE_SHA256},
            'asr':{'valid_transcription':True,'device':'cpu','public_reference_sha256':builder.REFERENCE_SHA256},
            'omnivoice_model_sha256':native.MODEL_SHA256}
        return root,report

    def test_cpu_qa_requires_all_nine_presets_clone_asr_and_exact_artifact_identity(self):
        root,report=self.qa_fixture();builder.validate_qa(root,report)
        for case in ('missing','gpu','stale','clone','asr','falseclaim','looping','looping_clone'):
            bad=copy.deepcopy(report)
            if case=='missing':bad['qwen_customvoice']['requests'].pop()
            if case=='gpu':bad['qwen_customvoice']['requests'][0]['device']='cuda'
            if case=='stale':bad['qwen_model_markers_sha256']['qwen']='0'*64
            if case=='clone':bad['qwen_base']['valid_pcm_audio']=False
            if case=='asr':bad['asr']['valid_transcription']=False
            if case=='falseclaim':bad['target_30x_guaranteed']=True
            if case=='looping':bad['qwen_customvoice']['requests'][0]['audio_seconds']=163.76
            if case=='looping_clone':bad['qwen_base']['audio_seconds']=163.76
            with self.subTest(case=case),self.assertRaises(ValueError):builder.validate_qa(root,bad)
        (root/'app/.data/models/qwen.ready').write_bytes(b'changed')
        with self.assertRaises(ValueError):builder.validate_qa(root,report)

    def test_owner_marker_and_runtime_recipe_preserve_isolation(self):
        with self.assertRaises(ValueError):builder.owned(self.root)
        root,_=self.qa_fixture();self.assertEqual(builder.owned(root),root.resolve())
        self.assertIn('huggingface-hub==0.36.2',builder.QWEN_REQUIREMENTS)
        self.assertIn('tokenizers==0.22.2',builder.QWEN_REQUIREMENTS)
        self.assertNotIn('flash-attn',builder.QWEN_REQUIREMENTS)


if __name__=='__main__':unittest.main()
