# Local Hmong voice cloning: implementation status

The published ZIPs through 0.3.3 do not contain a local cloning inference engine or its weights. Installing requirements-local.txt installs MMS dependencies; MMS VITS cannot clone these voices. The two supplied MP3s are references, not executable models. Microphone permission does not enable cloning.

The user requires local processing with no paid service. The user's posted Hmong poem explicitly does NOT match the two reference recordings; never use that poem as their reference transcript.

## Candidate requiring actual inference validation

- Repository: https://huggingface.co/Xuajpaj2026/hmong-tts-weights
- Pinned revision: 5663e0df2589c2ca2403cd327a52702c3ff96e8f
- Architecture: Fun-CosyVoice3-0.5B-hmong, matching cosyvoice3.yaml and bundled CosyVoice source.
- Author's tts_core.py explicitly instructs White Hmong RPA. inference_instruct2 uses reference audio without a matching transcript; inference_zero_shot also needs an accurate reference transcript.
- Approximately 7.7 GB total repository storage, including optional/duplicate/training artifacts; determine a minimal inference-only file set before downloading.
- Do not execute author's wrapper blindly: ensure_clean_llm uses weights_only=False and rewrites checkpoints; use an audited weights-only path. Its reference preparation clips10 seconds and cannot be combined with a full-reference transcript without alignment.
- Review model/source terms and dependencies; do not claim Windows or voice quality validation from the model description.

Required main weights (verified against Hub metadata, not yet downloaded):

| File under Fun-CosyVoice3-0.5B-hmong | Bytes | SHA256 |
| --- | ---: | --- |
| llm.pt | 2024669583 | 83386b9edd883b35ced9690b53c8d6d5ad7a5ddcd94275119892f13202b1bbfc |
| flow.pt | 1329116148 | a6fab32a7825e5b0bc855ddd948f8db9370b0a786fbc249caa4595e95b608e4b |
| hift.pt | 83202622 | b279d7641eb97ae55b3b540cfba4f953c26492a2df758328a89a4d007ab87a65 |
| campplus.onnx | 28303423 | a6ac6a63997761ae2997373e2ee1c47040854b4b759ea41ec48e4e42df0f4d73 |
| speech_tokenizer_v3.onnx | 969451503 | 23236a74175dbdda47afc66dbadd5bcb41303c467a57c261cb8539ad9db9208d |

Configuration, tokenizer files and possibly the BlankEN initialization weights are also required; inspect the loader to establish the complete set.

## Alternative investigated

Pakorn2112/F5TTS-Hmong, revision c50fc0cc991bc0c4f22d86c7a6152730c667c0d5, contains model_159952.safetensors (1348435761 bytes, SHA256 0b5e23fd6c9c1519f38195cbe0fdca3402beb75026b22ace483886529add3288) and vocab.txt. Its author's earlier app.py at revision c9a119f45d6ce9418ce5b6a59815febd9bb92734 establishes the F5TTS_Base DiT configuration. White Hmong support is not explicitly established. It requires an accurate reference transcript. Do not automatically substitute English Whisper recognition.

The current research machine has a separate /workspace/venvs/hmong-f5 environment with torch2.6.0+cpu, torchaudio2.6.0+cpu, f5-tts1.1.10; inference imports pass, but no real inference has run. Source installed version's preprocessing automatically clips reference audio, so inspect actual API before relying on a clip_short override. Calling infer_process with explicitly prepared reference audio may be necessary.

## Current external blocker

Hub metadata and raw source can be read. Binary checkpoints redirect to us.aws.cdn.hf.co, where the cloud network proxy returns HTTP403. An environment configuration draft preserving huggingface.co and cas-bridge.xethub.hf.co and adding us.aws.cdn.hf.co has been saved; saving the draft does not apply runtime policy or publish it. After the user saves settings and publishes, retry a real checkpoint read, then download and verify weights before inference.

Do not publish a new ZIP as a functioning clone until actual inference with supplied samples produces a decodable nonempty audio file; report listening/native-pronunciation validation separately. Pending 0.3.4 source changes only improve microphone diagnostics and optionality, not cloning.
