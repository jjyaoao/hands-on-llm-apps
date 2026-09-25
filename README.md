# 动手学大模型应用开发 · 学生资料

这里按节提供目前开放的 **第 0 节课程导学、第 1 节大模型基础、第 2 节 Agent 最小循环**。每节先看 PDF 课件，再看 Notebook 中的讲解、代码和保存输出，最后自己运行和改动实验。

| 节次 | 学习说明 | 课件 | Notebook |
| --- | --- | --- | --- |
| 00 | [课程导学](00%20%E8%AF%BE%E7%A8%8B%E5%AF%BC%E5%AD%A6/%E5%AD%A6%E4%B9%A0%E8%AF%B4%E6%98%8E.md) | [PDF](00%20%E8%AF%BE%E7%A8%8B%E5%AF%BC%E5%AD%A6/%E8%AF%BE%E4%BB%B6/L00-%E8%AF%BE%E7%A8%8B%E5%AF%BC%E5%AD%A6.pdf) | — |
| 01 | [大模型基础与最小训练实验](01%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80%E4%B8%8E%E6%9C%80%E5%B0%8F%E8%AE%AD%E7%BB%83%E5%AE%9E%E9%AA%8C/%E5%AD%A6%E4%B9%A0%E8%AF%B4%E6%98%8E.md) | [PDF](01%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80%E4%B8%8E%E6%9C%80%E5%B0%8F%E8%AE%AD%E7%BB%83%E5%AE%9E%E9%AA%8C/%E8%AF%BE%E4%BB%B6/L01-%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80%E4%B8%8E%E6%9C%80%E5%B0%8F%E8%AE%AD%E7%BB%83%E5%AE%9E%E9%AA%8C.pdf) | [第 1 本](01%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80%E4%B8%8E%E6%9C%80%E5%B0%8F%E8%AE%AD%E7%BB%83%E5%AE%9E%E9%AA%8C/Notebook/01-token-probability-loss.ipynb)、[第 2 本](01%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80%E4%B8%8E%E6%9C%80%E5%B0%8F%E8%AE%AD%E7%BB%83%E5%AE%9E%E9%AA%8C/Notebook/02-causal-transformer.ipynb)、[第 3 本](01%20%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80%E4%B8%8E%E6%9C%80%E5%B0%8F%E8%AE%AD%E7%BB%83%E5%AE%9E%E9%AA%8C/Notebook/03-train-and-generate.ipynb) |
| 02 | [从大模型到 Agent 组成与最小循环](02%20%E4%BB%8E%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%88%B0%20Agent%20%E7%BB%84%E6%88%90%E4%B8%8E%E6%9C%80%E5%B0%8F%E5%BE%AA%E7%8E%AF/%E5%AD%A6%E4%B9%A0%E8%AF%B4%E6%98%8E.md) | [PDF](02%20%E4%BB%8E%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%88%B0%20Agent%20%E7%BB%84%E6%88%90%E4%B8%8E%E6%9C%80%E5%B0%8F%E5%BE%AA%E7%8E%AF/%E8%AF%BE%E4%BB%B6/L02-%E4%BB%8E%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%88%B0Agent%E7%BB%84%E6%88%90%E4%B8%8E%E6%9C%80%E5%B0%8F%E5%BE%AA%E7%8E%AF.pdf) | [第 1 本](02%20%E4%BB%8E%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%88%B0%20Agent%20%E7%BB%84%E6%88%90%E4%B8%8E%E6%9C%80%E5%B0%8F%E5%BE%AA%E7%8E%AF/Notebook/01-tools-and-agent-components.ipynb)、[第 2 本](02%20%E4%BB%8E%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%88%B0%20Agent%20%E7%BB%84%E6%88%90%E4%B8%8E%E6%9C%80%E5%B0%8F%E5%BE%AA%E7%8E%AF/Notebook/02-loop-and-observations.ipynb)、[第 3 本](02%20%E4%BB%8E%E5%A4%A7%E6%A8%A1%E5%9E%8B%E5%88%B0%20Agent%20%E7%BB%84%E6%88%90%E4%B8%8E%E6%9C%80%E5%B0%8F%E5%BE%AA%E7%8E%AF/Notebook/03-deepseek-and-failures.ipynb) |

## 下载

在仓库页面点击 **Code → Download ZIP**，解压后保留三个节目录及根目录文件。也可以使用 `git clone`。单独下载一本 Notebook 时，图片、源码和数据路径可能无法解析。

## 环境与运行

建议使用 Python 3.12。第 1 节需要 PyTorch 和 Matplotlib；第 2 节离线部分只用 Python 标准库。两节都可用 JupyterLab 打开。PyTorch 安装包因系统而异，请先按 [PyTorch 官方安装说明](https://pytorch.org/get-started/locally/) 选择适合本机的命令。

在资料根目录创建虚拟环境并安装 JupyterLab 和 Matplotlib：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pip install jupyterlab ipykernel matplotlib
.\.venv\Scripts\python.exe -m jupyter lab
```

macOS / Linux：

```bash
./.venv/bin/python -m pip install jupyterlab ipykernel matplotlib
./.venv/bin/python -m jupyter lab
```

安装 PyTorch 后，在 Jupyter 中选择这个虚拟环境的 Python 内核，从上到下运行 Notebook。第 1 节训练的是教学用微型模型，可在 CPU 上完成。运行产生的临时文件放在根目录 `.local/`，随课文件不要改名或挪走。

## 真实模型请求

第 2 节的 02C Notebook 默认 `RUN_LIVE = False`，离线阅读和运行不会发起 DeepSeek 请求。要尝试真实请求，请自行设置 `DEEPSEEK_API_KEY`；若当前账号不支持 Notebook 中的默认模型，再设置 `DEEPSEEK_MODEL` 为账号可用的模型。开启前先了解服务费用和资料发送范围。密钥只放在本机环境变量中，不写入 Notebook 或提交到仓库。

Notebook 里已经保存的输出是制作课程时的实验记录；它们不表示你当前环境重新运行过，也不表示当前模型服务一定给出相同回答。

## 目录

每节直接包含 `课件/`、`Notebook/`，实践节另有 `代码/` 和 `数据/`。`代码/` 是 Notebook 调用的 Python 源文件；`Notebook/` 是可运行讲义。根目录 [资料来源](%E8%B5%84%E6%96%99%E6%9D%A5%E6%BA%90.md)列出本阶段使用的主要文档与实现来源。

课程后续节次会逐步加入。

## 许可

本课程原创文字、代码与机制图采用 [Apache License 2.0](LICENSE)。PDF 课件中嵌入的 Datawhale 标识和鲸鱼素材保留原有权利，不在该许可范围内；详见[第三方素材说明](THIRD_PARTY_NOTICES.md)。
