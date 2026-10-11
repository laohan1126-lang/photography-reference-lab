"""Reviewed source-media references for the action-directing course only.

Separate from `learning_media` on purpose: the base chapter registry stays the
single source of truth for its own cases, and this module never mutates it.
An entry permits a browser reference to an observed public image, not
redistribution. Keep the exact URLs linked by the source; never infer alternate
CDN versions, never widen a host into a wildcard, and never add a case here
before someone actually opened the original file and checked its pixels.
"""

ACTION_DIRECTING_SOURCE_CASE_MEDIA = {
    "action-greatsword-high": ("https://cosplaymode.net/wp-content/uploads/2025/01/2205_RPGposing_34.webp",),
    "action-greatsword-low": ("https://cosplaymode.net/wp-content/uploads/2025/01/2205_RPGposing_35.webp",),
    "action-greatsword-kneel": ("https://cosplaymode.net/wp-content/uploads/2025/01/2205_RPGposing_36.webp",),
    "action-greatsword-lean": ("https://cosplaymode.net/wp-content/uploads/2025/01/2205_RPGposing_37.webp",),
    "action-greatsword-transfer": ("https://cosplaymode.net/wp-content/uploads/2025/01/2205_RPGposing_47.webp",),
    "action-hip-back": ("https://cosplaymode.net/wp-content/uploads/2022/06/nihontou011.jpg",),
    "action-jerry-solo": (
        "https://westcottu.com/wp-content/uploads/Portrait-Lit-from-the-Front-Using-One-Ice-Light-3-on-a-Boom-Arm.jpg",
    ),
    "action-jerry-transfer": (
        "https://westcottu.com/wp-content/uploads/Studio-Couples-Portrait-with-Two-Ice-Light-3-Bi-Color-Lights.jpg",
    ),
}

# Exact original files, opened and visually reviewed by Codex during this task's
# pixel check. That is not the owner's aesthetic acceptance of the photographs, and the
# course still has to earn it; the registry only says which URL a `source_remote` case
# may reference, and the course content supplies its own dimensions.
ACTION_DIRECTING_SOURCE_IMAGE_CSP = " ".join(
    url for images in ACTION_DIRECTING_SOURCE_CASE_MEDIA.values() for url in images
)
