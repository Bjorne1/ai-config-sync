---
name: wh-cloud-his-test
description: 兼容壳。`wh-cloud-his-test` 已被 `wh-cloud-his-runtime-test` 统一入口替代，当前文件只保留跳转说明。
---

# wh-cloud-his-test

该入口已被 [wh-cloud-his-runtime-test](/home/wcs/projects/work-project/cloud_his/.agents/skills/wh-cloud-his-runtime-test/SKILL.md) 统一替代。

当前文件只保留兼容跳转作用，不再提供运行规则。

## 现在该用什么

- 真实启动服务
- 真实请求接口
- token 准备
- Redis 库位判断
- 数据库只读核对
- 失败分层

以上全部改走 [wh-cloud-his-runtime-test](/home/wcs/projects/work-project/cloud_his/.agents/skills/wh-cloud-his-runtime-test/SKILL.md)。

## 兼容壳边界

- 本文件不是运行时控制面。
- 本文件不再定义启动规则、鉴权规则、数据库规则。
- 如果本文件和新统一入口冲突，一律以新统一入口为准。
- 兼容壳退出条件：
  - 新统一入口连续覆盖 10 次真实测试任务且无回退
  - 或新统一入口发布满 14 天且没有旧入口依赖

满足其一，即允许删除本兼容壳。
