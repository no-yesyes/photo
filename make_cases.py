"""Generate the real 6:1 and 8:1 sample images published in the repository.

Usage:
    python make_cases.py           # requires IMAGE_API_KEY in .env
    python make_cases.py --demo    # offline previews, written to cases/preview/
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import server

CASES = [
    {
        "name": "case-6-1",
        "width": 3072,
        "height": 512,
        "title": "6:1 城市黄昏全景",
        "prompt": "黄昏时分的现代城市天际线全景，横向超宽构图；左侧老城区红砖屋顶逐渐过渡到中央摩天玻璃幕墙，再到右侧滨水公园与跨江大桥；天空从暖橙渐变到深蓝，余晖从左侧低角度照来，玻璃幕墙反射晚霞；写实摄影风格，35mm 镜头，自然景深，画面连贯无接缝",
    },
    {
        "name": "case-8-1",
        "width": 4096,
        "height": 512,
        "title": "8:1 雪山峡谷长卷",
        "prompt": "清晨的雪山峡谷超宽幅长卷，横向构图；从左侧的高原草甸与散落的牦牛群，经过中央的冰河与碎石滩，到右侧终年积雪的山峰和冰川；冷暖交界的晨光从左后方照射，云雾在谷底缓慢流动，岩石和雪面细节清晰；写实航拍摄影，层次分明，色彩自然，画面整体连贯",
    },
]

README = Path(__file__).parent / "README.md"
START_MARK = "<!-- cases:start -->"
END_MARK = "<!-- cases:end -->"


def update_readme(metadata: list[dict]) -> None:
    """Rewrite the results table in README so the published page shows the real images."""
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    if START_MARK not in text or END_MARK not in text:
        return
    lines = ["| 案例 | 尺寸 | 比例 | 预览 |", "| --- | --- | --- | --- |"]
    for item in metadata:
        lines.append(
            f"| {item['title']} | {item['width']} × {item['height']} | {item['ratio']} : 1 | "
            f"![{item['title']}](cases/{item['name']}.png) |"
        )
    block = f"{START_MARK}\n" + "\n".join(lines) + f"\n{END_MARK}"
    head, rest = text.split(START_MARK, 1)
    _, tail = rest.split(END_MARK, 1)
    README.write_text(head + block + tail, encoding="utf-8")
    print("已更新 README 结果表格")


def main() -> int:
    demo = "--demo" in sys.argv
    server.load_env()
    if not demo and not os.environ.get("IMAGE_API_KEY"):
        print("缺少 IMAGE_API_KEY：请在 .env 中配置图像服务密钥，或使用 --demo 生成离线预览。")
        return 1
    out_dir = Path(__file__).parent / ("cases" if not demo else Path("cases") / "preview")
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata = []
    for case in CASES:
        print(f"[{case['name']}] {case['title']} {case['width']}x{case['height']}", flush=True)
        image = server.render_wide(
            case["prompt"],
            case["width"],
            case["height"],
            demo=demo,
            on_progress=lambda done, total, name=case["name"]: print(f"  {name}: segment {done + 1}/{total}", flush=True),
        )
        path = out_dir / f"{case['name']}.png"
        image.save(path, format="PNG", optimize=True)
        print(f"  saved {path.relative_to(Path(__file__).parent)}", flush=True)
        metadata.append(
            {
                "name": case["name"],
                "title": case["title"],
                "width": case["width"],
                "height": case["height"],
                "ratio": round(case["width"] / case["height"], 2),
                "prompt": case["prompt"],
                "model": os.environ.get("IMAGE_MODEL", "gpt-image-1"),
                "demo": demo,
            }
        )
    (out_dir / "cases.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if not demo:
        update_readme(metadata)
    print(f"done: {len(metadata)} cases in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
