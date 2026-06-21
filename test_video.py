import os, tempfile

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

_load_env()

from tools_video import fetch_broll, generate_scene_image

with tempfile.TemporaryDirectory() as d:
    print(fetch_broll("Italian red wine vineyard", 1, d))
    print(generate_scene_image("Barolo wine bottle on rustic wooden table, Piedmont Italy", 1, d))
