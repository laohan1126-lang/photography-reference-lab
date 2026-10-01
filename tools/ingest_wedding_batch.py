"""Ingest downloaded high-res wedding reference images into project '婚纱'.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ref_lab.config import Settings
from ref_lab.models import CandidateInput, Source
from ref_lab.service import Library

NOTES_DATA = [
    {
        "author": "kimayi",
        "note_id": "6a3fae09000000002003ba65",
        "title": "爱如此刻永恒 - 昔涟花嫁婚纱",
        "character": "昔涟",
        "images": [
            "http://sns-webpic-qc.xhscdn.com/202610011935/6eb79ae9108e29cac5c68ca021b6ba49/notes_pre_post/1040g3k0321ts6kj3nu605p8rt7vp2r6bdp5n1v0!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011935/2eb1f8dafa0a579e79db5b4202801c00/notes_pre_post/1040g3k0321ts6kj3nu5g5p8rt7vp2r6b5t538s0!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011935/14ba0c387b59eefacf9006f6a318ed2c/notes_pre_post/1040g3k0321ts6kj3nu505p8rt7vp2r6bfgete30!nd_dft_wgth_webp_3",
        ]
    },
    {
        "author": "南音不难",
        "note_id": "6a0e9df7000000003601887b",
        "title": "即使世界都否认了你 我也会站在你这边 - 蕾姆花嫁",
        "character": "蕾姆",
        "images": [
            "http://sns-webpic-qc.xhscdn.com/202610011939/be0c87d7196f010bcaefbd3b3813d8b3/1040g008320duv72mls6g5nhhbbhg96pbpdoq770!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/b70de4fabaa77e5f94159e40fcbc247c/1040g008320duv72mls5g5nhhbbhg96pb9v683t8!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/0c622cee68af81207da27f50ee72e33e/1040g008320duv72mls005nhhbbhg96pbllh7il8!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/a0d1d4eb58612622781d3b9287402d4e/1040g008320duv72mls505nhhbbhg96pbb5raob0!nd_dft_wlteh_webp_3",
        ]
    },
    {
        "author": "林灬小逸丶",
        "note_id": "69fad6500000000035024ffe",
        "title": "天选coser：我的婚礼入场进行曲！ - 婚纱蕾姆",
        "character": "蕾姆",
        "images": [
            "http://sns-webpic-qc.xhscdn.com/202610011939/3d088a4fc8e8d30231b95c5183841cd7/notes_pre_post/1040g3k031vqkqub256005n45t8pkc2av5elb1ug!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/7eab77d417520a73a74575efd731c578/notes_pre_post/1040g3k031vqkqub2560g5n45t8pkc2av8u5f9k8!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/4dde8d413ea83f2f26c0bbda9b1c9da1/notes_pre_post/1040g3k031vqkqub256105n45t8pkc2avp5ri710!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/e199225957964f8455b33efdcf7eef1e/notes_pre_post/1040g3k031vqkqub2561g5n45t8pkc2avbrn9l38!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/fceb04bb396a34e7c4810d52433598ff/notes_pre_post/1040g3k031vqkqub256205n45t8pkc2avl2vp5b8!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/0d8dbd65f74fb89109ca54ea03791a72/notes_pre_post/1040g3k031vqkqub2562g5n45t8pkc2avabao5pg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/e55e44d92ed19c0bdda16f0f8c3c96b7/notes_pre_post/1040g3k031vqkqub256305n45t8pkc2avh6haid0!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011939/3107870c06a76f3e9fb802d39852ab94/notes_pre_post/1040g3k031vqkqub2563g5n45t8pkc2av2rfsc2g!nd_dft_wlteh_webp_3",
        ]
    },
    {
        "author": "didiBabawU～",
        "note_id": "68b9e4af000000001b0236f9",
        "title": "遵从召唤而来，你就是我的master嘛 - 花嫁Saber",
        "character": "阿尔托莉雅/Saber",
        "images": [
            "http://sns-webpic-qc.xhscdn.com/202610011941/331cdfcbc37d576d64c7adff7a2978c2/1040g00831m1748t6l8805n87i1u4ng3gpsgifq0!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/70a431508752199259153868baf53cfd/1040g00831m1748t6l87g5n87i1u4ng3gnfimni8!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/cf19c29763675599ca0b656dc4787b3e/1040g00831m1748t6l8705n87i1u4ng3gf4se3ag!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/fe92ab74bd7ebdf0d18ae3d1bb2c7fec/1040g00831m1748t6l89g5n87i1u4ng3gsd8qfo8!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/c5694c17e3082faff20c840d948b926b/1040g00831m1748t6l88g5n87i1u4ng3guh48fc8!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/a9bb7340d62e40fb5d7961853cb7e0c9/1040g00831m1748t6l8905n87i1u4ng3gr3nhv1g!nd_dft_wgth_webp_3",
        ]
    },
    {
        "author": "海海📸",
        "note_id": "6aad35fc000000002901053b",
        "title": "时崎狂三花嫁九宫格",
        "character": "时崎狂三",
        "images": [
            "http://sns-webpic-qc.xhscdn.com/202610011941/c4ab89ee01534ef39b9793786bb5a2db/1040g2sg3258r12jsk6jg5obgocmgkgi1a88eflg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/7444b0314e83375b2761c2c7237a3d2e/1040g2sg3258r12jsk6kg5obgocmgkgi1esd2v20!nd_dft_wgth_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/0d41ad91627db14e902096ce96e2cf0c/1040g2sg3258r12jsk6fg5obgocmgkgi1r1e7qr8!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/6549b4a0a70ed93577f63d6fd457b0e5/1040g2sg3258r12jsk6gg5obgocmgkgi1emjmmq8!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/43f45d1a9ba0c491ba3b5c35ee4c7a83/1040g2sg3258r12jsk6hg5obgocmgkgi1odmklcg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/02693142bf8d6d183103b8c13067c7db/1040g2sg3258r12jsk6k05obgocmgkgi1lgsatb0!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/c313df971254d39f8c22d8b2806441be/1040g2sg3258r12jsk6ig5obgocmgkgi1o2vnlhg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/fa37df49ae0fa11686210233bffc38e9/1040g2sg3258r12jsk6i05obgocmgkgi1fd14evo!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/b1e7ac1c19497b925a2a53a2e2a15202/1040g2sg3258r12jsk6h05obgocmgkgi1fjogft8!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/c3f352a229ddfdbc17c3ff3f606667ed/1040g2sg3258r12jsk6eg5obgocmgkgi1ianboqo!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011941/8cfd6c8d62b3a95468892dab757a1e05/1040g2sg3258r12jsk6j05obgocmgkgi1d2luaqg!nd_dft_wlteh_webp_3",
        ]
    },
    {
        "author": "飞鸟Fay",
        "note_id": "69733a18000000000e03e1cb",
        "title": "爱是神洒在她肩上的光 - 极简复古白纱",
        "character": "复古白纱",
        "images": [
            "http://sns-webpic-qc.xhscdn.com/202610011942/438c499b6c6d36048a451bad40e2d3a6/1040g00831rm72c8tis005n431ne4aftd1eone20!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011942/3fceeacfd7416dd2f815853923877b8a/1040g00831rm72c8tis0g5n431ne4aftd081m668!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011942/e8a983466ca63a074dd6c7ae0eb22939/1040g00831rm72c8tis205n431ne4aftd0eihomg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011942/eaf565e0f76c71e6507ad32c009a5678/1040g00831rm72c8tis105n431ne4aftdqedfpqg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011942/7aa00c9749098799121e08baf3fbcb3c/1040g00831rm72c8tis3g5n431ne4aftdk073gtg!nd_dft_wlteh_webp_3",
            "http://sns-webpic-qc.xhscdn.com/202610011942/569adb000fc220d19c41c4f05f05e082/1040g00831rm72c8tis2g5n431ne4aftdn5o5m9o!nd_dft_wlteh_webp_3",
        ]
    }
]

LOCAL_PRESERVED = [
    {
        "file": Path(r"C:\Users\Dell\Desktop\参考\c2cdec2326e052cc84537f41bfceafc5.jpg"),
        "author": "junyou",
        "title": "蕾姆 水蓝捧花婚纱",
        "character": "蕾姆",
        "url": "https://www.xiaohongshu.com/search_result?keyword=junyou",
    },
    {
        "file": Path(r"C:\Users\Dell\Desktop\参考\d6147e10d74b2ff8544fdf85606860aa.jpg"),
        "author": "暝儿小短腿（减肥中）",
        "title": "蕾姆 漫展超大拖尾婚纱场照",
        "character": "蕾姆",
        "url": "https://www.xiaohongshu.com/user/profile/6273b03900000000210272d3",
    },
    {
        "file": Path(r"C:\Users\Dell\Desktop\参考\f61329bceec2d6bdedd23b5a80eadc51.jpg"),
        "author": "z480376771",
        "title": "婚纱与纱裙腿部姿态教学",
        "character": "白纱姿态参考",
        "url": "https://www.xiaohongshu.com/search_result?keyword=z480376771",
    },
]


def download_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.xiaohongshu.com/",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    os.environ["LAB_DATA_DIR"] = str(REPO_ROOT / "data")
    settings = Settings.from_env()
    lib = Library(settings)

    # 1. Target project '婚纱'
    char_name = "婚纱"
    existing = [p for p in lib.projects() if p.get("character") == char_name]
    if existing:
        project_id = existing[0]["id"]
        print(f"Target project: [{char_name}] (ID: {project_id})")
    else:
        print("Error: Project '婚纱' not found!")
        sys.exit(1)

    download_cache_dir = REPO_ROOT / "data" / "downloaded_wedding"
    download_cache_dir.mkdir(parents=True, exist_ok=True)

    imported_count = 0
    errors = 0

    # 2. Download from notes
    print("\n--- Downloading & Ingesting Note Originals ---")
    for note in NOTES_DATA:
        author = note["author"]
        title_base = note["title"]
        char = note["character"]
        note_id = note["note_id"]
        page_url = f"https://www.xiaohongshu.com/explore/{note_id}"
        print(f"\nProcessing [{author}] - {title_base} ({len(note['images'])} images)")

        for img_idx, img_url in enumerate(note["images"], 1):
            try:
                cached_filename = f"{author}_{note_id}_{img_idx:02d}.webp"
                cache_path = download_cache_dir / cached_filename
                if cache_path.is_file():
                    data = cache_path.read_bytes()
                else:
                    data = download_bytes(img_url)
                    cache_path.write_bytes(data)

                # Ingest to CAS
                asset = lib.ingest_asset(data, cached_filename)
                
                # Add candidate
                sub_title = f"{title_base} #{img_idx:02d}"
                c_input = CandidateInput(
                    asset_sha=asset["id"],
                    title=sub_title,
                    source=Source(
                        obtained_as="as_received",
                        author=author,
                        page_url=page_url
                    ),
                    discovery_intent="exact_character" if char in ["蕾姆", "昔涟", "阿尔托莉雅/Saber", "时崎狂三"] else "transferable_pose",
                    discovery_reason=f"根据桌面朋友截图找回的官方无压缩高清原图 (小红书作者: {author})",
                )
                res = lib.add_candidate(project_id, c_input)
                status = "Newly Added" if res.get("created") else "Already Exists"
                print(f"  [{img_idx}/{len(note['images'])}] {status}: {cached_filename} ({len(data)} bytes, sha: {asset['id'][:8]})")
                imported_count += 1
            except Exception as e:
                print(f"  [{img_idx}/{len(note['images'])}] Error: {e}")
                errors += 1

    # 3. Ingest the 3 preserved clean files from desktop
    print("\n--- Ingesting Preserved Desktop Direct Images ---")
    for item in LOCAL_PRESERVED:
        p = item["file"]
        if not p.is_file():
            print(f"  Missing desktop file: {p}")
            continue
        try:
            data = p.read_bytes()
            asset = lib.ingest_asset(data, p.name)
            c_input = CandidateInput(
                asset_sha=asset["id"],
                title=item["title"],
                source=Source(
                    obtained_as="as_received",
                    author=item["author"],
                    page_url=item["url"]
                ),
                discovery_intent="exact_character" if item["character"] == "蕾姆" else "transferable_pose",
                discovery_reason=f"桌面朋友直接分享的高清原图 (小红书作者: {item['author']})",
            )
            res = lib.add_candidate(project_id, c_input)
            status = "Newly Added" if res.get("created") else "Already Exists"
            print(f"  {status}: {p.name} ({len(data)} bytes, sha: {asset['id'][:8]})")
            imported_count += 1
        except Exception as e:
            print(f"  Error importing {p.name}: {e}")
            errors += 1

    print("\n==========================================")
    print(f"Wedding Reference Batch Complete!")
    print(f"  Total Ingested: {imported_count}")
    print(f"  Errors:         {errors}")
    print(f"  Available at:   http://127.0.0.1:18765/#/project/{project_id}")
    print("==========================================")


if __name__ == "__main__":
    main()
