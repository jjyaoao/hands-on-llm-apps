"""课堂连接器：官方 stdio 传输与被动协议记录，不自己实现 MCP。"""
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
import anyio
from mcp import Client, StdioServerParameters, stdio_client

class RecordingStream:
    """只复制 JSON-RPC 消息用于观察；不改变内容或包办协议解析。"""
    def __init__(self, stream, events, direction):
        self.stream, self.events, self.direction = stream, events, direction

    def record(self, item):
        if isinstance(item, Exception):
            self.events.append({'direction': self.direction, 'error_type': type(item).__name__})
        else:
            self.events.append({'direction': self.direction,
                'message': item.message.model_dump(mode='json', by_alias=True, exclude_none=True)})

    async def send(self, item):
        await self.stream.send(item)
        self.record(item)

    async def receive(self):
        item = await self.stream.receive()
        self.record(item)
        return item

    def __aiter__(self): return self

    async def __anext__(self):
        try: return await self.receive()
        except anyio.EndOfStream: raise StopAsyncIteration

    async def aclose(self): await self.stream.aclose()
    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.aclose()

@asynccontextmanager
async def recording_stdio(parameters, events):
    # Jupyter 的 stderr 是展示流，Windows 子进程需要真实文件句柄。
    # 将服务端诊断写到临时文件，连接结束后回显；stdout 仍专用于 MCP。
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8', errors='replace') as errlog:
        try:
            async with stdio_client(parameters, errlog=errlog) as (read_stream, write_stream):
                yield (RecordingStream(read_stream, events, 'server_to_client'),
                       RecordingStream(write_stream, events, 'client_to_server'))
        finally:
            errlog.seek(0)
            diagnostics = errlog.read()
            if diagnostics:
                sys.stderr.write(diagnostics)

@asynccontextmanager
async def connect(events=None, mode='2026-07-28'):
    """固定当前协议，无初始化握手；auto 可用于兼容旧服务的发现探测。"""
    events = [] if events is None else events
    parameters = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).with_name('stdio_server.py'))], env={})
    # SDK 只继承其默认必要环境；不把 DeepSeek 凭据交给资料进程。
    async with Client(recording_stdio(parameters, events), mode=mode,
                      read_timeout_seconds=10, cache=None) as client:
        yield client

async def probe():
    events = []
    async with connect(events) as client:
        tools = await client.list_tools()
        files = await client.call_tool('list_files', {})
        config = await client.call_tool('read_file', {'path': 'config.py'})
        denied = await client.call_tool('read_file', {'path': '../outside.txt'})
    return {'kind': 'real_local_mcp_stdio', 'protocol': '2026-07-28',
        'sdk': 'mcp==2.1.1', 'tools': tools.model_dump(mode='json', by_alias=True),
        'files': files.model_dump(mode='json', by_alias=True),
        'config': config.model_dump(mode='json', by_alias=True),
        'denied': denied.model_dump(mode='json', by_alias=True), 'events': events}
