"""可选下载固定版本的公开学习资料；只下载清单中文本，不执行、安装或发布。"""
import hashlib,json,urllib.request,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
MANIFEST=ROOT/'08 综合实践一 资料与仓库导读/数据/hello-agents-input.json'

def fetch():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    base=ROOT/'.local/external-materials/hello-agents'/manifest['revision']
    reading=base/'reading';reading.mkdir(parents=True,exist_ok=True)
    for item in manifest['files']:
        target=(base if item['role']=='license' else reading)/item['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        data=target.read_bytes() if target.exists() else urllib.request.urlopen(item['url'],timeout=40).read(1_000_001)
        if len(data)>1_000_000:raise ValueError('下载超出文本上限')
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if blob!=item['git_blob_sha1']:raise ValueError('文件与固定提交清单不一致')
        if 'sha256' in item and hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('内容哈希不一致')
        target.write_bytes(data)
    print(reading)
    return reading
if __name__=='__main__':fetch()
