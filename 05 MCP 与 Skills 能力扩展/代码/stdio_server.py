"""真正的 MCP stdio 服务端；stdout 专用于协议，不打印讲解文字。"""
from pathlib import Path
import sys
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02 从大模型到 Agent 组成与最小循环/代码'))
from agent_lab import RepoTools

# 复用第二章的真实只读文件工具；不扩大可读取范围。
repo = RepoTools(ROOT / '02 从大模型到 Agent 组成与最小循环/数据/demo-repo')
server = MCPServer('course-repository', version='1.0', log_level='ERROR')

@server.tool()
def list_files() -> dict:
    """列出当前教学仓库可读取的相对文件路径。"""
    return repo.list_files()

@server.tool()
def read_file(path: str) -> dict:
    """读取 list_files 返回的一个文本文件，返回原文和行号。"""
    if not path.strip() or len(path) > 200:
        raise ToolError('path 必须是 1–200 字符的非空相对路径')
    try:
        return repo.read_file(path)
    except PermissionError:
        raise ToolError('out_of_scope：只能读取 list_files 列出的课程文件') from None
    except (FileNotFoundError, ValueError, OSError):
        raise ToolError('read_failed：文件不存在、过大或无法读取') from None

if __name__ == '__main__':
    server.run(transport='stdio')
