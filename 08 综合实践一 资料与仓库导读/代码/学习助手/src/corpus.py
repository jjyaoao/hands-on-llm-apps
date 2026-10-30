"""导入明确给定的教学目录：只读文本与 PDF，不执行其中代码。"""
import hashlib,json,os,sys
from dataclasses import asdict
from pathlib import Path
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'03 资料检索与有依据的回答/代码'))
from retrieval_lab import Chunk,chunk_text,TfidfIndex

class Corpus:
    def __init__(self,directory):
        original=Path(directory)
        if original.is_symlink():raise ValueError('不导入符号链接根目录')
        self.root=original.resolve()
        if not self.root.is_dir():raise ValueError('资料根目录不存在')
        self.documents=[];self.chunks=[];self.locations={};self.hashes={};self.full_documents={}
        paths=[]
        for parent,dirs,files in os.walk(self.root,followlinks=False):
            dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in {'node_modules','__pycache__','venv','mock','mocks'}
                           and not (Path(parent)/d).is_symlink())
            for name in sorted(files):
                path=Path(parent)/name
                if name.startswith('.') or '.mock.' in name or path.is_symlink():continue
                if path.suffix.lower() not in {'.md','.txt','.py','.json','.pdf'}:continue
                if len(paths)>=200:raise ValueError('教学资料最多 200 个文件，请先缩小选择')
                paths.append(path)
        if sum(p.stat().st_size for p in paths)>20_000_000:raise ValueError('总资料上限 20 MB')
        for path in paths:self._read(path)
        if not self.chunks:raise ValueError('没有可检索文本')
        self.index=TfidfIndex(self.chunks);self.by_id={c.id:c for c in self.chunks}
        self.by_id.update({c.id:c for c in self.full_documents.values()})
        self.fingerprint=hashlib.sha256(json.dumps(self.hashes,sort_keys=True).encode()).hexdigest()

    def _read(self,path):
        relative=path.relative_to(self.root).as_posix();size=path.stat().st_size
        if size>10_000_000:raise ValueError('单文件上限 10 MB')
        digest=hashlib.sha256(path.read_bytes()).hexdigest();self.hashes[relative]=digest
        if path.suffix.lower()=='.pdf':
            reader=PdfReader(path)
            if reader.is_encrypted:raise ValueError('课程导入不处理加密 PDF')
            if not 1<=len(reader.pages)<=80:raise ValueError('教学 PDF 最多 80 页，请先明确选页')
            pages=[(i+1,page.extract_text() or '') for i,page in enumerate(reader.pages)]
        else:
            if size>1_000_000:raise ValueError('文本单文件上限 1 MB')
            pages=[(None,path.read_text(encoding='utf-8'))]
        document={'path':relative,'sha256':digest,'kind':'pdf' if pages[0][0] else 'text',
                  'pages':len(pages),'headings':[],'empty_pages':[]}
        for page,text in pages:
            if len(text)>300_000:raise ValueError('单页/文本提取量过大')
            if not text.strip():document['empty_pages'].append(page);continue
            if page is None:
                document['headings'] += [line.strip('# ')[:100] for line in text.splitlines() if line.startswith('#')][:8]
            source=relative if page is None else f'{relative}#page={page}'
            whole=Chunk(source,1,len(text.splitlines()),text.rstrip('\n'),hashlib.sha256(text.encode()).hexdigest())
            self.full_documents[(relative,page or 0)]=whole
            self.locations[whole.id]={'path':relative,'page':page,'start':1,'end':whole.end_line,
                'line_unit':'source_line' if page is None else 'extracted_text_line','document_sha256':digest}
            for chunk in chunk_text(text,source,lines_per_chunk=12,overlap=2):
                self.chunks.append(chunk)
                self.locations[chunk.id]={'path':relative,'page':page,'start':chunk.start_line,'end':chunk.end_line,
                    'line_unit':'source_line' if page is None else 'extracted_text_line','document_sha256':digest}
        self.documents.append(document)

    def map(self):
        return {'fingerprint':self.fingerprint,'documents':self.documents,'chunks':len(self.chunks),
                'note':'PDF 空文本页可能需要 OCR；当前没有 OCR，不能当作内容不存在。'}

    def search(self,query,k=3):
        if not isinstance(query,str) or not 1<=len(query.strip())<=300:raise ValueError('查询需为 1–300 字符')
        if type(k) is not int or not 1<=k<=5:raise ValueError('k 为 1–5')
        return {'hits':[{'id':h['chunk'].id,'score':round(h['score'],6),'location':self.locations[h['chunk'].id],
                        'preview':h['chunk'].text[:400]} for h in self.index.search(query,k)],
                'score_meaning':'TF-IDF 余弦相似度，不是正确概率'}

    def read(self,chunk_id):
        if not isinstance(chunk_id,str) or chunk_id not in self.by_id:raise ValueError('资料块 ID 不存在')
        c=self.by_id[chunk_id]
        if len(c.text)>6000:raise ValueError('此块超过读取上限，需要更细的资料预处理')
        return {'id':c.id,'location':self.locations[c.id],'text':c.text,'text_sha256':c.source_sha256}

    def read_document(self,path,page=0):
        """短文本全文或 PDF 单页；长文本仍需先检索分块。page=0 表示普通文本。"""
        if not isinstance(path,str) or type(page) is not int or (path,page) not in self.full_documents:
            raise ValueError('文件或物理页不存在；普通文本 page=0')
        return self.read(self.full_documents[(path,page)].id)
