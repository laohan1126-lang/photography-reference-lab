"""Reviewed source-media references for the learning document only.

An entry permits a browser reference to an observed public image, not redistribution.
Keep the exact URLs linked by the source; never infer alternate CDN versions.
"""

COMMONS_IMAGE_SOURCE = "https://thumb.wikimedia.org/wikipedia/commons/thumb/"

SOURCE_CASE_MEDIA = {
    "sword-forward": ("https://cosplaymode.net/wp-content/uploads/2022/06/nihontou043.jpg",),
    "sword-hip-back": ("https://cosplaymode.net/wp-content/uploads/2022/06/nihontou011.jpg",),
    "sword-hip-side": ("https://cosplaymode.net/wp-content/uploads/2022/06/nihontou012.jpg",),
    "sword-transfer-quiet": ("https://cosplaymode.net/wp-content/uploads/2022/06/nihontou025.jpg",),
    "sword-transfer-western": ("https://cosplaymode.net/wp-content/uploads/2020/06/10_MG_3967.jpg",),
    "sword-transfer-ninja": ("https://cosplaymode.net/wp-content/uploads/2020/06/06_MG_3956.jpg",),
    "marsh-before": (
        "https://images.contentstack.io/v3/assets/blt0e5ec1de4817c440/bltfd6b7105c060e86e/65cf8ca6cf0d4229544a68bf/distraction-1-before.jpg",
    ),
    "marsh-after": (
        "https://images.contentstack.io/v3/assets/blt0e5ec1de4817c440/bltdd0e01250b80f2a4/65cf8ca8d9d2ef4f1d250d6d/distraction-1-after-fixed.jpg",
    ),
    "center-portrait": (
        "https://images.contentstack.io/v3/assets/blt0e5ec1de4817c440/blt9b80b5c24625373e/65cf7e6ae7cf9557c40d8f6c/Tamara-Lackey-laughing-girl-portrait.jpg",
    ),
    "angle-grid": ("https://petapixel.com/assets/uploads/2017/04/portraittest_1.jpg",),
    "faulds-portrait": (
        "https://d1kw7y14plrcrj.cloudfront.net/assets/images/ppmag_articles/201711-8vh_1901_header.jpg",
    ),
    "allan-head-turn": ("https://thelenslounge.com/wp-content/uploads/2020/03/butterfly-light-portraits.jpg",),
    "hobby-ambient-sequence": (
        "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjMEM1vTKrvAcH32joHeDALxRlnrb-hOk0rnMrJdSZmRKPvbc9fhUHBcMLOAHdzuJbbhOIOxJsWe8olSSr-KsaUCJo_o_P7-VfhkhXUapaD0aoY-hc25a4WXKOrz9hCc1eFnoVHew/s1600/Shade.jpg",
        "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhnoYibIPZhFZM35edo5JqGvXsUDV_oyNVowML1fI0a8-vR21fpnhhOJ0ffJPP4KeLSaSJOkgUV9VyTqJ1FvN1gEAggm4m6xXiTlr-geWHYW3e9sA29nuxo9yMutGmxJvxkFP67XQ/s1600/Dark.jpg",
        "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjJQmg_5EoGsaHWS9y9kKJoowzCifY9kDyNqY6tJ0V0JPL6K9T4cmXNuUOqcg0JCSPpeMusbHUpoojbWe2MzjE5lZC5gYgtXcPdDk8b1N-9PzX1OMgtSqX-qaUwC2Y36Io3xuzGiA/s1600/Final.jpg",
    ),
}

SOURCE_IMAGE_CSP = " ".join([
    COMMONS_IMAGE_SOURCE,
    *(url for images in SOURCE_CASE_MEDIA.values() for url in images),
])
