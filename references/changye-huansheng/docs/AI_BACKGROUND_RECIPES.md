# 王昭君·长夜焕生 AI 背景扩展与生成配方 (AI_BACKGROUND_RECIPES)

> **版本**：V2.1 Expo Field Edition  
> **核心使命**：解决漫展背景杂乱、场馆空间狭小的现实约束。通过科学的 AI 背景扩展（Background Extension）技术，生成真实自然、透视严密、绝无“一眼 AI 假画感”的深海视觉空间。  
> **红线铁律**：**严禁重新生成 Coser 模特身体、面部、假发、手部与王昭君长夜焕生服装道具！仅对背景非主体选区进行扩展与填充！**

---

## 一、 AI 背景真假质感的“五大物理匹配法则”

为什么很多 AI 换背景的片子看起来假？因为违反了真实相机的物理光学。成功的 AI 背景必须严密匹配拍摄时的原始参数：

```
                    [真实拍摄原片参数 (Sony A7M4 + Godox V100)]
                                        ↓
         +------------------------------+------------------------------+
         |                              |                              |
[1. 透视与相机高度匹配]        [2. 主光光向与反差匹配]        [3. 景深与镜头虚化匹配]
 仰拍对应低地平线               V100闪光灯从右侧打入           50mm f/1.8 对应大虚化
 俯拍对应高视平线               背景高光与光束必须在同侧       背景清晰度严禁超过前景主体
         |                              |                              |
         +------------------------------+------------------------------+
                                        ↓
                         +--------------+--------------+
                         |                             |
                [4. 地面接触与影子保留]        [5. 色温与环境色漫射]
                 严禁抠掉脚底真实阴影           深蓝背景必须通过图层混合
                 必须保留靴底触地真实反光       在人物边缘透出冷青微光
```

---

## 二、 核心 AI 背景配方 (Recipe 01 ~ Recipe 04)

---

### 配方一：【深海海渊破晓巨幕】(The Abyssal Dawn Horizon)

- **最适配原片**：Shot 01（全身站姿迎光）、Shot 07（低机位仰拍长腿）、Chain 07。
- **最适主光光向**：Godox V100 位于模特右上方或右侧 45°（高位主光）。
- **背景必须包含的元素**：
  - 深邃暗调靛蓝海水渐变（`#060C1B` ~ `#0E1B38`）；
  - 从画面右上角斜向射入深渊的微弱晨曦丁达尔光柱（God Rays）；
  - 远景极度虚化的小型发光浮游生物光斑（Bokeh Orbs）；
  - 平整干净的深暗色海床或无反光礁石地面（承接模特真实站位）。
- **背景绝对不能包含的元素**：
  - ❌ 绝对不能出现巨大的、塑料感强烈的热带珊瑚礁；
  - ❌ 绝对不能出现热带小丑鱼或海龟（破坏深海孤寂高冷神性）；
  - ❌ 绝对不能出现水族馆玻璃框或现代人造建筑。
- **图像生成 / 扩展提示词模板 (Prompt)**：
  > *Positive Prompt:*  
  > `cinematic photo of vast deep dark abyssal ocean interior, mysterious deep indigo and cyan water, subtle god rays penetrating from top right corner into deep water, soft floating bioluminescent particles out of focus, clean dark ocean floor with realistic ground perspective, shallow depth of field, 50mm lens perspective, high dynamic range, natural underwater atmosphere, 8k, photorealistic, no people, empty scene`  
  > *Negative Prompt:*  
  > `people, woman, face, hands, colorful tropical coral, clownfish, cartoon, 3d render, plastic texture, text, watermark, bright daylight, overexposed`
- **最易出现的 AI 假感与翻车点**：
  - AI 容易在背景生成过于刺眼的五彩珊瑚，导致画面廉价俗气；
  - AI 生成的破晓光束方向如果与右手握持法杖的实际闪光灯方向相反，会导致物理光源矛盾。
- **Photoshop 最终融合秘诀**：
  1. 将 AI 背景置于人物图层下方；
  2. 人物脚底保留 10% 漫展真实地面的羽化蒙版，并在地面图层上加一层“正片叠底”的黑色深海投影；
  3. 用大口径软画笔，以 `#2CE8D6`（青蓝）在人物边缘外侧刷出 5% 透明度的微光，完成冷调空气包裹。

---

### 配方二：【万千水母群游星海】(Jellyfish Swarm Sanctuary)

- **最适配原片**：Shot 02（手托微光）、Shot 09（法杖群游大招）、Chain 04。
- **最适主光光向**：正面大柔光附件（如 V100 加圆形柔光罩正向打亮面部）。
- **背景必须包含的元素**：
  - 数量在 6~12 只、大小各异、景深层次分明的半透明白青色水母（Medusozoa）；
  - 远景水母必须有重度高斯模糊，中景水母保持半透明透光，近景（仅 1~2 只）掠过画面边缘；
  - 水下星尘般的悬浮发光微粒。
- **背景绝对不能包含的元素**：
  - ❌ 绝对不能出现密密麻麻如蚊群般刺眼密恐的光点；
  - ❌ 水母绝对不能长得像外星异形或机械怪物，必须是自然界海月水母或灯塔水母形态。
- **图像生成 / 扩展提示词模板 (Prompt)**：
  > *Positive Prompt:*  
  > `dark blue ocean background filled with delicate translucent glowing white jellyfish floating, deep sea environment, ethereal soft bioluminescence, natural volumetric depth, out of focus jellyfish in far background, clean minimalist composition, peaceful aquatic world, shot on Sony A7IV, cinematic film still, atmospheric haze, no people, empty background`  
  > *Negative Prompt:*  
  > `dense crowd of jellyfish, monster, neon overload, messy, clutter, low quality, high saturation green, human, text`
- **最易出现的 AI 假感与翻车点**：
  - 水母亮度过高，盖过王昭君面部亮度，抢夺视觉主体地位；
  - 水母没有景深虚化，所有水母都是 100% 锐利的平贴贴纸。
- **Photoshop 最终融合秘诀**：
  - 背景图层整体透明度压至 80%，让人物的冷白面孔与晶体法杖保持全画面最高明度。

---

### 配方三：【幽暗水族巨幕暗调】(The Minimalist Aquarium Wall)

- **最适配原片**：Shot 04（面部美妆特写）、Shot 06（美背回眸）、Chain 03。
- **最适主光光向**：侧光或侧逆光（展现面部立体感与露背线条）。
- **背景必须包含的元素**：
  - 极简、微弧形的深蓝冷暗巨幅玻璃水幕；
  - 隐隐约约的流动水波光纹（Caustics），波纹细腻柔和；
  - 远景隐现一条巨大的幽灵蓝鲸半透明剪影（呼应王昭君大招巨鲸设定）。
- **背景绝对不能包含的元素**：
  - ❌ 绝对不能出现水族馆游客的倒影或指示牌；
  - ❌ 水波纹绝对不能粗大锐利像蜘蛛网。
- **图像生成 / 扩展提示词模板 (Prompt)**：
  > *Positive Prompt:*  
  > `minimalist dark blue aquarium glass wall background, deep moody ambient light, subtle soft water caustics reflecting softly in distance, faint translucent silhouette of a giant whale gliding far away in deep water, smooth color gradient from navy blue to deep black, clean premium aesthetic, bokeh, no people`  
  > *Negative Prompt:*  
  > `reflections of visitors, signs, bright spots, noisy water ripples, cheap led lights, human figure, text`
- **Photoshop 最终融合秘诀**：
  - 极度适合 50mm f/1.8 特写！背景只需提供细腻的冷蓝渐变虚化，将模特清冷神性的五官衬托得如同顶级奢侈品广告。

---

### 配方四：【沉船静谧古殿礁石】(Sunken Palace Ruins)

- **最适配原片**：Shot 03（小马扎坐姿）、Shot 07（孤寂守护）、Chain 02。
- **最适主光光向**：顶光或微侧顶光。
- **背景必须包含的元素**：
  - 古老风化、长满海藻的深海青石柱基底；
  - 小马扎下方无缝融入古代神殿石阶边缘；
  - 水汽充盈的冷青色景深雾霭。
- **图像生成 / 扩展提示词模板 (Prompt)**：
  > *Positive Prompt:*  
  > `ancient sunken stone steps in deep blue ocean abyss, mysterious temple ruins underwater, covered in subtle bioluminescent moss, smooth stone platform in foreground with realistic perspective for seating, atmospheric haze, volumetric blue light, cinematic fantasy, empty environment, no people`  
  > *Negative Prompt:*  
  > `statues with human faces, modern objects, rubbish, messy debris, oversaturated colors, human, text`
- **Photoshop 最终融合秘诀**：
  - 将小马扎的椅腿部分，通过蒙版融入 AI 生成的古石阶落差边缘，形成“王昭君正端坐在沉船神殿遗迹之上”的自然物理透视！
