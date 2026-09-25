import sys, time
sys.path.append("scripts")
import xhs_explore

note_info = xhs_explore.get_note_detail()
print("Title:", note_info.get("title"))
print("Author:", note_info.get("author"))
images = xhs_explore.get_note_images()
print(f"Total images found: {len(images)}")
for i, img in enumerate(images):
    src = img.get("currentSrc", "")
    nw = img.get("naturalWidth", 0)
    nh = img.get("naturalHeight", 0)
    print(f"[{i}] {nw}x{nh} | {src[:80]}")
