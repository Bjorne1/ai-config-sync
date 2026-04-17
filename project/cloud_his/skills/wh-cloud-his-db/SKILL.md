---
name: wh-cloud-his-db
description: 兼容壳。数据库只读核对已并入 `wh-cloud-his-runtime-test`，当前文件只保留跳转说明。
---

# wh-cloud-his-db

该入口已被 [wh-cloud-his-runtime-test](/home/wcs/projects/work-project/cloud_his/.agents/skills/wh-cloud-his-runtime-test/SKILL.md) 统一替代。

当前文件只保留兼容跳转作用，不再定义数据库核对规则。

## 现在该用什么

- 开发库只读查询
- 六个库范围判断
- 联调后数据核对

以上全部改走 [wh-cloud-his-runtime-test](/home/wcs/projects/work-project/cloud_his/.agents/skills/wh-cloud-his-runtime-test/SKILL.md)。

## 兼容壳边界

- 本文件不是运行时控制面。
- 本文件不再定义数据库连接或库范围规则。
- 如果本文件和新统一入口冲突，一律以新统一入口为准。
- 兼容壳退出条件：
  - 新统一入口连续覆盖 10 次真实测试任务且无回退
  - 或新统一入口发布满 14 天且没有旧入口依赖

满足其一，即允许删除本兼容壳。
