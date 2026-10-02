"""Counterexamples to broad hard filters; synthetic pixels are not vision evidence."""
import io
import pytest
from PIL import Image, ImageDraw
from tools.collect_adapter import (build_policy, result_metadata_allowed, validate_downloaded_image,
                                   white_background_ratio, process_and_expand_image)


def policy():
    return build_policy({'project_snapshot':{'character':'托尔'},'notes':''})


@pytest.mark.parametrize('title',['托尔 cos正片，展开翅膀','托尔 c服 cos正片，假发自己整理','托尔 cos正片 和搭子合照','托尔 cos正片 求一个温柔的拥抱','托尔 棚拍 cos正片 对镜自拍','托尔 cos正片 自制道具出镜'])
def test_generic_words_do_not_blacklist_photography(title):
    assert result_metadata_allowed({'t':title,'purl':'https://example.invalid/photo'},policy())[0]


@pytest.mark.parametrize('title',['托尔 想拍正片求搭子','托尔 cos服出租','托尔 道具制作教程','托尔 游戏截图 cos','托尔 商品展示 cos','求助 托尔 c服怎么穿'])
def test_explicit_noise_intent_is_not_rescued_by_positive_words(title):
    ok,reason=result_metadata_allowed({'t':title},policy())
    assert not ok and reason.startswith('negative_type:')


def test_author_name_and_url_do_not_classify_post_type():
    record={'t':'托尔 cos正片','author':'人台假发制作教程','purl':'https://example.invalid/商品展示'}
    assert result_metadata_allowed(record,policy())[0]


def test_high_white_ratio_is_warning_not_product_classification():
    image=Image.new('RGB',(800,1200),'white')
    ImageDraw.Draw(image).rectangle((350,350,450,950),fill=(85,115,145))
    out=io.BytesIO();image.save(out,'JPEG',quality=95);raw=out.getvalue()
    assert white_background_ratio(raw)>0.60
    assert validate_downloaded_image(raw,{'portrait_only':False})[0]
    source={'source':{'obtained_as':'as_received'},'title':'合成边界样本','discovery_reason':'测试，不是真实人像'}
    result=process_and_expand_image(raw,'jpg',source,set(),[],allow_split=False)
    assert len(result)==1 and result[0][1]==raw
    assert '不能据此判断商品/文档' in result[0][2]['discovery_reason']
    assert 'preflight' not in result[0][2]
    assert source['discovery_reason']=='测试，不是真实人像'


def test_collage_splitter_dependency_is_declared_and_available():
    """A clean install must not silently turn the shipped splitter off."""
    import tomllib
    from pathlib import Path
    from tools import collect_adapter as adapter
    from tools.collage_splitter import CollageSplitter

    manifest = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert any(dep.startswith("numpy>=") for dep in manifest["project"]["dependencies"])
    assert adapter.CollageSplitter is CollageSplitter
