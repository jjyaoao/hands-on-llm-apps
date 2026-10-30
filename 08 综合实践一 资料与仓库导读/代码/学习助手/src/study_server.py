"""只读资料 MCP 服务；目录由宿主显式传入，不执行导入内容。"""
import sys
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from corpus import Corpus
corpus=Corpus(sys.argv[1])
server=MCPServer('course-study-materials',version='1.0',log_level='ERROR')

@server.tool()
def source_map()->dict:
    """列出资料文档、PDF 物理页数、版本指纹与空文本页。"""
    return corpus.map()

@server.tool()
def search_corpus(query:str,k:int=3)->dict:
    """按关键词检索最多 5 个资料片段，返回 ID、位置和短预览。"""
    try:return corpus.search(query,k)
    except ValueError as error:raise ToolError(str(error)) from None

@server.tool()
def read_chunk(chunk_id:str)->dict:
    """根据检索所得 ID 读取完整原文块及来源位置，用于引用核验。"""
    try:return corpus.read(chunk_id)
    except ValueError as error:raise ToolError(str(error)) from None

@server.tool()
def read_document(path:str,page:int=0)->dict:
    """读取短文本全文或 PDF 的一个物理页。普通文本 page=0，PDF 页从 1 开始。"""
    try:return corpus.read_document(path,page)
    except ValueError as error:raise ToolError(str(error)) from None

if __name__=='__main__':server.run(transport='stdio')
