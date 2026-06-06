import os
import pytest

AGENTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'agents')
AGENT_NAMES = ['ceo', 'sommelier', 'creator', 'marketer', 'barista', 'book_reader', 'writer']


def test_all_agent_files_exist():
    for name in AGENT_NAMES:
        path = os.path.join(AGENTS_DIR, f'{name}.txt')
        assert os.path.exists(path), f"agents/{name}.txt が見つかりません"


def test_agent_files_not_empty():
    for name in AGENT_NAMES:
        path = os.path.join(AGENTS_DIR, f'{name}.txt')
        with open(path, encoding='utf-8') as f:
            content = f.read().strip()
        assert len(content) > 100, f"agents/{name}.txt の内容が短すぎます（100字以上必要）"


def test_agent_files_contain_role_description():
    for name in AGENT_NAMES:
        path = os.path.join(AGENTS_DIR, f'{name}.txt')
        with open(path, encoding='utf-8') as f:
            content = f.read()
        assert 'CUBOCCI STUDIO' in content, f"agents/{name}.txt に 'CUBOCCI STUDIO' が含まれていません"
