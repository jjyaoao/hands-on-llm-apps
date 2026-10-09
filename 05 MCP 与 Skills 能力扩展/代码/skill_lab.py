"""课程自编最小 Skill 加载器；覆盖本课两字段包，不是完整规范实现。"""
import re
from pathlib import Path
import yaml

class SkillLibrary:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.entries, self.active, self.events = {}, set(), []
        for path in sorted(self.root.glob('*/SKILL.md')):
            if path.is_symlink() or path.parent.is_symlink():
                raise ValueError('课堂包不接受符号链接')
            if path.stat().st_size > 16000:
                raise ValueError('课堂 SKILL.md 上限为 16000 字节')
            # 仅读取文件头；发现阶段不把正文交给模型。
            with path.open(encoding='utf-8') as f:
                if f.readline().strip() != '---': raise ValueError('缺少 YAML 文件头')
                header = []
                for line in f:
                    if line.strip() == '---': break
                    header.append(line)
                else: raise ValueError('文件头未关闭')
            info = yaml.safe_load(''.join(header))
            if not isinstance(info, dict) or set(info) != {'name', 'description'}:
                raise ValueError('本课加载器仅支持 name 和 description 两字段')
            name, desc = info['name'], info['description']
            if (not isinstance(name, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name)
                    or len(name) > 64 or name != path.parent.name):
                raise ValueError('Skill 名称与目录不匹配或不合法')
            if not isinstance(desc, str) or not 1 <= len(desc.strip()) <= 1024:
                raise ValueError('description 必须为 1–1024 字符')
            self.entries[name] = info
        self.events.append({'stage': 'discover', 'names': list(self.entries)})

    def catalog(self):
        return [dict(x) for x in self.entries.values()]

    def activate(self, name):
        if name not in self.entries: raise ValueError('Skill 未注册')
        text = (self.root / name / 'SKILL.md').read_text(encoding='utf-8')
        self.active.add(name)
        self.events.append({'stage': 'activate', 'name': name})
        return text

    def read_resource(self, name, path):
        if name not in self.active: raise PermissionError('需要先激活 Skill')
        # 这是本课显式可读清单，不是所有 Skill 的通用路径规则。
        if path != 'references/conditions.md': raise PermissionError('资源未在本课清单中')
        target = self.root / name / path
        if target.is_symlink() or target.parent.is_symlink(): raise PermissionError('不读取符号链接')
        if target.stat().st_size > 16000: raise ValueError('资源过大')
        self.events.append({'stage': 'resource', 'name': name, 'path': path})
        return target.read_text(encoding='utf-8')
