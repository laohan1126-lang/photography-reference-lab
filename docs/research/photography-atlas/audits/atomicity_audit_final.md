# 摄影能力树：最终原子性与前置依赖审计

本审计只读根目录候选与canonical文件，审计产物写在本worktree。审阅时实际canonical为 **241 项**、SOURCE_MAP为 **193 条**；初始消息中的238项已在审阅期间更新。已逐项遍历current tree全ID与所有raw `*_candidates.json`（12份、262条候选），完整ID表见JSON。

## 核验结果

- canonical前置ID、来源ID、必要字段和模块链接均可解析；所有技能均有练习、验收和至少一条eligible的全文直接来源。107条high均通过两条独立A/B来源检查；个人状态全为`unassessed`。
- canonical无`project_checklists`字段或独立清单文件，但raw候选确实把若干被降级技能用作前置项。canonical前置都有效，不代表被拿掉的现场准备步骤无用。建议将下述被保留的操作门槛写进独立项目清单，不要恢复为非原子化L3。
- 262个raw候选ID中，241个在canonical，10个有`merged_candidate_ids`映射，另11个没有映射或排除理由。JSON列出全部未映射ID。
- 所有canonical技能有练习与验收；235项练习为`project_designed`，6项为`source_exercise`。依赖“表达自然/符合意图/观者先看”的验收应预先说明目标、展示条件及反馈来自作者、扮演者还是观察者。

## 需要保留的工作检查项

角色意图转译、移动主体的AF策略选择、灯距变化的效应隔离、全身姿势顺序复查、合成亮度修正前的高光/阴影检查，都曾出现在被移除或未定义的前置链里。建议作为项目工作清单保留；清单字段、触发场景与检查项在JSON中逐项说明。原始合成候选引用了未定义的`post-composite-highlight-check`和`post-composite-shadow-check`，建议核对后映射至现有`post-composite-tone-check`。

## 特别审查

**Cosplay小道具持握位置**有一个直接来源并且练习可执行。持握位置/朝向是一个控制变量，但角色表达和面部轮廓遮挡是两个可能独立失败的结果；目前宜保留一个技能、两条分别验收，不推导匕首朝向规则。

**地点与情境复盘**：拍前查人物和场景关联、时段与地点可行性等候选有直接来源；`field-location-reflection`只有adapted证据，不进入正式技能。较窄的`field-intent-result-review`有直接来源，但不能扩大成“地点故事线索必然成立”。

**图像证据**：当前21个链接案例均为文字/图注级引用；本次没有打开像素，不构成照片审美审查。

## 产物

- 机器可读完整审计：`research/atomicity_audit_final.json`
- 前一轮跨scope原子性建议：`research/atomicity_audit.json`
