import sys, glob, re
sys.stdout.reconfigure(encoding='utf-8')

manifest_info = {}
try:
    with open('staging/manifest.md', 'r', encoding='utf-8') as f:
        content = f.read()
    entries = re.split(r'\n##\s+', content)
    for e in entries[1:]:
        lines = e.strip().split('\n')
        title = lines[0]
        fm = re.search(r'文件：`([^`]+)`', e)
        pt = re.search(r'Pose Type：([^;\n\r]+)', e)
        desc = re.search(r'怎么摆：([^;\n\r]+)', e)
        src = re.search(r'来源：([^;\n\r]+)', e)
        author = re.search(r'作者：([^;\n\r]+)', e)
        url = re.search(r'<(https://[^>]+)>', e)
        if fm:
            manifest_info[fm.group(1).strip()] = {
                'title': title,
                'pose_type': pt.group(1).strip() if pt else '',
                'desc': desc.group(1).strip() if desc else '',
                'src': src.group(1).strip() if src else '',
                'author': author.group(1).strip() if author else '',
                'url': url.group(1).strip() if url else ''
            }
except Exception as ex:
    print('Manifest read error:', ex)

for f in sorted(glob.glob('images/*.*')):
    norm_f = f.replace('\\', '/')
    info = manifest_info.get(norm_f, {})
    title = info.get('title', 'NO_TITLE')[:25]
    pt = info.get('pose_type', 'NO_PT')[:35]
    src = info.get('src', 'NO_SRC')[:25]
    print(f"{norm_f:25} | {title:25} | {pt:35} | {src}")
