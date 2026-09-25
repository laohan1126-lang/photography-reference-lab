import urllib.request
import ssl
import json
from pathlib import Path

out_dir = Path("staging/downloads/eyra_poses")
out_dir.mkdir(parents=True, exist_ok=True)

ctx = ssl._create_unverified_context()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.xiaohongshu.com/"
}

# The image list from the open note
imgs = [
    "https://sns-webpic-qc.xhscdn.com/202609250016/b14731b7a417a3afe0904afa2d49bc53/notes_pre_post/1040g3k831vhtdnlek8ag5o10lpfg88hadhrb8po!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/632e157f79e5643eef6321992223376c/notes_pre_post/1040g3k031vht73a7jm4g5o10lpfg88haes6m07g!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/e6f431e334406e7e98fc4978021e8433/notes_pre_post/1040g3k031vht73a7jm505o10lpfg88haklpe0v8!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/475ccb89af170a1fd2aa64d9bd0df28c/notes_pre_post/1040g3k031vht73a7jm6g5o10lpfg88ha8hbds0g!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/94b01d2f2f6ef6bfd167078cc266fb69/notes_pre_post/1040g3k831vhtdnlek8705o10lpfg88hasop4thg!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/9b987ceee585eacae06262d14756b6a4/notes_pre_post/1040g3k031vht73a7jm605o10lpfg88haqo02lo0!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/6998f7e5a41a395f58f60367e9409e3e/notes_pre_post/1040g3k831vhtdnlek87g5o10lpfg88havmjs3ko!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/abab367699927f15ab2e1a50c3cfbb51/notes_pre_post/1040g3k831vhtdnlek8805o10lpfg88hadu7sv20!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/82b21395ba7cc9ca9ecbfe24f24dd2ff/notes_pre_post/1040g3k831vhtdnlek88g5o10lpfg88hafds4sc8!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/e28862d149ce57f307f1a3d1088153f7/notes_pre_post/1040g3k831vhtdnlek8905o10lpfg88haes8c18g!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/7cc144749ddafb5a1236d3a1c6ee3def/notes_pre_post/1040g3k031vht73a7jm5g5o10lpfg88hapn9kc70!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/b15b96875737ae9c8df1f8d0386374aa/notes_pre_post/1040g3k831vhtdnlek89g5o10lpfg88haicfdir0!nd_dft_wlteh_webp_3",
    "https://sns-webpic-qc.xhscdn.com/202609250016/b4568126ac0c1975f07e12cb50623fed/notes_pre_post/1040g3k831vhtdnlek8a05o10lpfg88hamkop6l8!nd_dft_wlteh_webp_3"
]

for idx, url in enumerate(imgs):
    fn = f"eyra_pose_{idx+1:02d}.webp"
    fp = out_dir / fn
    if fp.exists():
        continue
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = resp.read()
            fp.write_bytes(data)
            print(f"Downloaded {fn} ({len(data)} bytes)")
    except Exception as e:
        print(f"Failed {fn}: {e}")
