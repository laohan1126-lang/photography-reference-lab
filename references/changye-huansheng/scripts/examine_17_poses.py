import sys, yaml
sys.stdout.reconfigure(encoding='utf-8')

with open('references/changye-huansheng/data/references.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

poses = [r for r in data if r.get('id', '').startswith('POSE_') and r.get('priority') == 'CORE']
print(f"Total CORE poses: {len(poses)}")
print("-" * 100)
for p in poses:
    pid = p.get('id')
    f = p.get('file')
    iq = p.get('image_quality', {})
    va = p.get('visual_audit', {})
    src = p.get('source', {})
    w = iq.get("width")
    h = iq.get("height")
    author = src.get("author", "N/A")[:15]
    pose = va.get("actual_pose", "N/A")[:45]
    print(f"{pid:10} | {w}x{h:4} | {author:15} | {pose}")
