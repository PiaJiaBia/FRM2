"""按章节加载计算器，保留教材目录及跨章节导入关系。"""
from functools import lru_cache
from hashlib import sha256
from importlib import import_module
from pathlib import Path
import json
import sys

ROOT = Path(__file__).parent / 'Market Risk Measurement and Mangement'
MANIFEST = json.loads((ROOT / 'chapter_manifest.json').read_text(encoding='utf-8'))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@lru_cache
def load_chapter(number):
    """返回章节模块；函数和类保持原有接口。"""
    entry = MANIFEST[str(number)]
    return import_module(f'Chapter{number}.{entry["module"]}')


def source_fingerprint():
    """包含全部章节源码，覆盖跨章节计算依赖。"""
    digest = sha256()
    for number, entry in MANIFEST.items():
        path = ROOT / f'Chapter{number}' / (entry['module'] + '.py')
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
