"""Download a pinned public model. Reads/uploads no student records."""
import argparse
from pathlib import Path
from vision_ocr import MODEL_ID, MODEL_REVISION

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True)
    args=parser.parse_args()
    from huggingface_hub import snapshot_download
    target=Path(args.directory).expanduser().resolve()
    snapshot_download(MODEL_ID,revision=MODEL_REVISION,local_dir=str(target),
                      allow_patterns=['*.json','*.jinja','*.txt','*.safetensors'],max_workers=2)
    (target/'paperdesk-model-revision.txt').write_text(MODEL_REVISION+'\n')
    print('Pinned local handwriting model installed.')
