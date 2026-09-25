"""课程自编的字符级因果 Transformer。CPU 小实验，不是通用聊天模型。"""
import copy
import hashlib
import json
import math
import platform
import time
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

# %% 数据：先分文档，词表只从训练文档建立

def load_data(path):
    docs = json.loads(Path(path).read_text(encoding="utf-8"))
    train = [d["text"] for d in docs if d["split"] == "train"]
    valid = [d["text"] for d in docs if d["split"] == "valid"]
    assert not set(train) & set(valid), "训练与验证不能包含相同文档"
    vocab = ["<UNK>"] + sorted(set("\n".join(train)))
    stoi = {ch: i for i, ch in enumerate(vocab)}
    def encode(text):
        return torch.tensor([stoi.get(ch, 0) for ch in text], dtype=torch.long)
    return vocab, [encode(x) for x in train], [encode(x) for x in valid]


def windows(documents, context=32):
    # 窗口不能跨越文档边界；输入与标签错开一个位置。
    pairs = [(d[i:i+context], d[i+1:i+context+1])
             for d in documents for i in range(len(d)-context)]
    if not pairs:
        raise ValueError("文档必须长于上下文窗口")
    return torch.stack([p[0] for p in pairs]), torch.stack([p[1] for p in pairs])

# %% 模型：预归一化、因果注意力、残差和前馈层
class CausalAttention(nn.Module):
    def __init__(self, width, heads, context):
        super().__init__()
        assert width % heads == 0
        self.heads, self.head_dim = heads, width // heads
        self.qkv = nn.Linear(width, 3 * width)
        self.out = nn.Linear(width, width)
        self.register_buffer("mask", torch.tril(torch.ones(context, context, dtype=torch.bool)))

    def forward(self, x):
        batch, length, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        # [B,T,C] -> [B,H,T,D]，每个头学习不同的关系。
        q, k, v = [t.reshape(batch, length, self.heads, self.head_dim).transpose(1, 2)
                   for t in (q, k, v)]
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.head_dim)
        scores = scores.masked_fill(~self.mask[:length, :length], float("-inf"))
        weights = scores.softmax(dim=-1)
        mixed = (weights @ v).transpose(1, 2).contiguous().reshape(batch, length, width)
        return self.out(mixed)


class Block(nn.Module):
    def __init__(self, width, heads, context):
        super().__init__()
        self.norm1, self.norm2 = nn.LayerNorm(width), nn.LayerNorm(width)
        self.attention = CausalAttention(width, heads, context)
        self.ffn = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(), nn.Linear(4 * width, width))

    def forward(self, x):
        x = x + self.attention(self.norm1(x))
        return x + self.ffn(self.norm2(x))


class TinyLM(nn.Module):
    def __init__(self, vocab_size, width=48, heads=4, context=32):
        super().__init__()
        self.context = context
        self.token_embedding = nn.Embedding(vocab_size, width)
        self.position_embedding = nn.Embedding(context, width)
        self.block = Block(width, heads, context)
        self.norm = nn.LayerNorm(width)
        self.output = nn.Linear(width, vocab_size)

    def forward(self, ids):
        length = ids.shape[1]
        if not 0 < length <= self.context:
            raise ValueError("输入长度必须在上下文窗口内")
        pos = torch.arange(length, device=ids.device)
        x = self.token_embedding(ids) + self.position_embedding(pos)
        return self.output(self.norm(self.block(x)))  # [B,T,V]，返回 logits

# %% 训练：固定评估集合、记录真实采样点
@torch.no_grad()
def evaluate(model, pairs):
    model.eval()
    total, count = 0., 0
    for x, y in zip(pairs[0].split(128), pairs[1].split(128)):
        loss = F.cross_entropy(model(x).reshape(-1, model.output.out_features), y.reshape(-1), reduction="sum")
        total += loss.item()
        count += y.numel()
    return total / count


@torch.no_grad()
def generate(model, vocab, prefix="学习", steps=60, temperature=0.8, seed=11):
    if temperature <= 0:
        raise ValueError("temperature 必须大于 0；本函数不把 0 当作贪心解码")
    model.eval()
    stoi = {ch: i for i, ch in enumerate(vocab)}
    ids = torch.tensor([[stoi.get(ch, 0) for ch in prefix]], dtype=torch.long)
    if ids.shape[1] == 0:
        raise ValueError("前缀不能为空")
    rng = torch.Generator().manual_seed(seed)
    for _ in range(steps):
        logits = model(ids[:, -model.context:])[:, -1, :]
        next_id = torch.multinomial((logits / temperature).softmax(-1), 1, generator=rng)
        ids = torch.cat([ids, next_id], dim=1)
    return "".join(vocab[i] for i in ids[0].tolist())


def train_experiment(data_path, steps=240, lr=0.003, seed=7, context=32, width=48, batch_size=16):
    torch.set_num_threads(2)
    torch.manual_seed(seed)
    vocab, train_docs, valid_docs = load_data(data_path)
    train_pairs, valid_pairs = windows(train_docs, context), windows(valid_docs, context)
    model = TinyLM(len(vocab), width=width, context=context)
    initial_state = copy.deepcopy(model.state_dict())
    before = generate(model, vocab)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    rng = torch.Generator().manual_seed(seed + 1)
    history, started = [], time.perf_counter()
    for step in range(steps + 1):
        if step % 40 == 0 or step == steps:
            history.append({"step": step, "train_loss": evaluate(model, train_pairs),
                            "valid_loss": evaluate(model, valid_pairs)})
        if step == steps:
            break
        model.train()
        index = torch.randint(len(train_pairs[0]), (batch_size,), generator=rng)
        x, y = train_pairs[0][index], train_pairs[1][index]
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, len(vocab)), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)  # 清除上一批累积的梯度
        loss.backward()                      # 自动求导，得到每个参数的梯度
        optimizer.step()                     # AdamW 按优化器规则更新参数
    report = {"seed": seed, "steps": steps, "lr": lr, "context": context, "width": width,
              "batch_size": batch_size, "parameters": sum(p.numel() for p in model.parameters()),
              "vocab_size": len(vocab), "train_documents": len(train_docs), "valid_documents": len(valid_docs),
              "train_windows": len(train_pairs[0]), "valid_windows": len(valid_pairs[0]),
              "valid_unknown_ratio": sum((d == 0).sum().item() for d in valid_docs) / sum(len(d) for d in valid_docs),
              "elapsed_seconds": round(time.perf_counter() - started, 3), "device": "cpu",
              "python": platform.python_version(), "torch": torch.__version__, "platform": platform.platform(),
              "data_sha256": hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
              "history": history, "before": before, "after": generate(model, vocab),
              "temperatures": {str(t): generate(model, vocab, temperature=t) for t in (0.3, 0.8, 1.5)}}
    return model, vocab, report, initial_state
