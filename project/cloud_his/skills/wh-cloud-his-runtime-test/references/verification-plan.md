# verification-plan

这份文档只负责定义“怎么验证新统一入口符合批准规格”，不替代运行时契约。

## 验证前提

- 运行时控制面只认：
  - `contracts/service-capability-matrix.yaml`
  - `contracts/test-task-spec.yaml`
- 如果验证过程发现契约之外的文档仍在决定运行行为，判失败。

## 验证顺序

1. 先验证服务契约完整性。
2. 再验证任务输入契约完整性。
3. 先验证“直接点接口”模式可用。
4. 最后验证代表性场景。

## 0. 直接接口模式

目标：

- 证明用户直接指定接口时，不需要它先出现在示例任务里。

检查点：

- `SKILL.md` 明确说明示例任务不是接口白名单。
- `run-preflight.sh` 同时支持：
  - `--task-id`
  - `--endpoint <path> --method <HTTP_METHOD>`

通过信号：

- 像 `/v1/aiAssistant/aiCustomChatFlow` 这种接口，只要能锁定服务和请求方式，就能进入预检。
- 如果接口命中了控制器家族模板前缀，预检结果里会带出对应模板标识。

失败信号：

- 仍要求必须先补 task_id
- 或仍因为“示例任务里没有这条接口”直接拦住

## 1. ai-service 无 token

目标：

- 证明 `ai-service` 在统一入口里允许无 token 测试路径。

检查点：

- `service-capability-matrix.yaml` 中 `ai-service.token_requirement=not_required`
- `service-capability-matrix.yaml` 中 `ai-service.redis_db_rule=not_applicable`
- `test-task-spec.yaml` 至少有一个 `ai-service` 示例任务，且 `expected_redis_checks.mode=skip`

通过信号：

- 没有任何规则要求 ai-service 默认必须带 token
- 无 token 示例不会被契约层直接拦住

失败信号：

- ai-service 被写成 `required`
- ai-service 示例仍要求 Redis 校验

## 2. emr-service 联动 ai-service / his-service

目标：

- 证明 emr 任务默认依赖和下游证据都被硬写进契约。

检查点：

- `service-capability-matrix.yaml` 中 `emr-service.default_dependencies` 同时包含 `ai-service`、`his-service`
- `service-capability-matrix.yaml` 中 `emr-service.notes` 明确写出 AI 助手家族先走本机 `http://localhost:19087/ai`
- `service-capability-matrix.yaml` 中 `ai-service.notes` 明确写出给 emr 做联调时，本地访问口径是 `http://localhost:19087/ai`
- `test-task-spec.yaml` 中至少一个 `emr-service` 示例任务声明了：
  - 控制器家族前缀 `/v1/aiAssistant`
  - `target_endpoint.match_mode=prefix`
  - `known_paths` 至少覆盖：
    - `/v1/aiAssistant/aiCustomChatFlow`
    - `/v1/aiAssistant/medicalRecordQuality`
    - `/v1/aiAssistant/inspectionReportInterpret`
  - token 校验
  - `ai-service` 下游证据
  - 数据库核对按子接口副作用决定，而不是整个前缀统一硬绑

通过信号：

- 统一入口在任务层面不能只测 emr 自己，且能把同前缀子接口归到同一个模板家族
- `aiCustomChatFlow` 这种纯转发子接口不会被错误要求查业务表
- 做 emr AI 联调时，不会再把“按服务名找 ai-service”当成默认前提，而是先检查本机 `19087/ai`

失败信号：

- emr 默认依赖缺任一项
- 示例任务没有下游证据要求
- 前缀模板仍把某个子接口的查库规则强加给全部子接口
- 仍把 emr 到 ai 的链路误判成注册中心服务发现直连

## 3. drg-service 前置脚本

目标：

- 证明 drg 必须先跑前置脚本，再按运行时文件启动。

检查点：

- `service-capability-matrix.yaml` 中 `drg-service.prelaunch_actions=prepare-drg-wsl-config`
- `service-capability-matrix.yaml` 中 `drg-service.redis_db_rule=from_runtime_file`
- 启动来源同时包含：
  - `.vscode/tasks.json`
  - `.vscode/launch.json`
  - `bootstrap-wcs.yaml`

通过信号：

- 契约明确要求前置脚本，不允许把 drg 当普通 Spring Boot 服务处理

失败信号：

- 前置动作缺失
- 仍按通用 profile 猜启动方式

## 4. report-service 证据不足

目标：

- 证明 `report-service` 不会被误写成自动可执行。

检查点：

- `service-capability-matrix.yaml` 中 `report-service.evidence_status` 不是 `READY`
- `report-service.notes` 明确写出证据不足原因
- `SKILL.md` 明确说明证据不足服务不能静默降级

通过信号：

- `report-service` 只能是 `BLOCKED` 或 `REQUIRES_MANUAL_CONFIRMATION`
- 未确认时不能执行

失败信号：

- `report-service` 被写成 `READY`
- 没写明阻塞原因

## 5. TTL = -1

目标：

- 证明长期测试 token 的目标 TTL 被写死为不过期。

检查点：

- `test-task-spec.yaml` 中所有需要长期 token 的示例都写 `ttl_should_be: -1`
- `SKILL.md` 明确长期 token 目标是 `TTL=-1`
- `SKILL.md` 明确要求在执行前记录 token 当前 TTL 作为基线
- `SKILL.md` 明确要求测试结束后按基线恢复 TTL；基线为 `-1` 时优先用 `PERSIST`

通过信号：

- 契约没有再沿用秒级 TTL
- 统一入口不会只做“测后看 TTL”，而是会先记基线再恢复

失败信号：

- 仍保留短期 TTL 默认值
- 没有写明 `-1`
- 没有基线恢复规则

## 6. 旧进程识别

目标：

- 证明复用本地服务前，统一入口会先确认当前运行产物没有落后于源码，再确认当前进程里真的有目标接口，不会把旧进程误当成最新代码。

检查点：

- `SKILL.md` 明确写出“先做构建产物新鲜度校验，再做接口存在性校验”
- `SKILL.md` 明确写出产物时间与源码时间的比较规则：
  - 运行产物可取 `target/classes`、`target/*.jar`、部署目录 jar
  - 源码取目标模块相关文件的最新修改时间
  - 源码时间晚于产物时间时，要直接判定为旧产物
- `SKILL.md` 明确写出“不能只看端口活着就复用服务”
- `SKILL.md` 明确写出目标接口存在性校验的优先顺序：
  - `/v2/api-docs`
  - 启动日志
  - 接口映射证据
- `SKILL.md` 明确写出：时间校验命中旧产物时，要先重新构建；jar 或部署包方式还要重新打包部署
- `SKILL.md` 明确写出：目标接口不存在时，要直接判定为旧进程并先重启
- `SKILL.md` 明确写出：新增接口或刚改过的接口，如果首个请求返回 `404`，要先回查是不是旧进程或旧产物

通过信号：

- 统一入口能在真正发请求前，就先发现“产物时间落后于源码”
- 统一入口不会再把“旧进程缺接口”误报成链路 `404`
- 新增接口测试前就能发现当前进程没加载最新代码

失败信号：

- 没有产物时间与源码时间的比对步骤
- 仍然只靠端口存活判断服务可复用
- 没有旧进程识别步骤
- 把这类 `404` 直接记成接口失败

## 7. 六库覆盖

目标：

- 证明统一入口的数据库核对范围已经扩到六个库，不停留在旧四库。

检查点：

- `service-capability-matrix.yaml` 全部 `db_scopes` 的并集必须覆盖：
  - `his`
  - `wh_ai`
  - `wh_drg`
  - `wh_pay`
  - `wh_report`
  - `wh_system`
- `test-task-spec.yaml` 明确要求 `expected_db_checks[*].db_scope` 必须落在目标服务允许范围内

通过信号：

- 六个库都能在契约里找到落点

失败信号：

- 仍只有四个库
- `wh_report` 或 `wh_system` 无法在契约中定位

## 8. 清理规则

目标：

- 证明 Redis 和非 Redis 临时数据的处理规则已经分开写死。

检查点：

- `SKILL.md` 明确：
  - 长期 token 不清理
  - Redis 临时数据不额外清理
  - 非 Redis 临时数据按任务契约清理
- `service-capability-matrix.yaml` 的每个服务都存在 `cleanup_rule`
- `test-task-spec.yaml` 的 `cleanup_targets` 是必填字段

通过信号：

- 没有再出现“测试结束后看情况清理”

失败信号：

- 清理规则缺字段
- 非 Redis 清理没有输入位

## 9. 控制面边界

目标：

- 证明统一入口只认契约，不依赖其他文档决定运行行为。

检查点：

- `SKILL.md` 明确声明只有契约和当前目录脚本属于运行时控制面
- 本文档把“契约外文档不得决定运行行为”列为必须验证项

通过信号：

- 新统一入口不依赖契约外文档决定行为

失败信号：

- 新统一入口仍把其他文档当输入
- 控制面边界缺失

## 判定门槛

以下条件同时成立才算本轮文档和契约通过：

- 两份契约存在且字段完整
- `report-service` 不是 `READY`
- 至少一个示例任务可用于直接填充真实测试输入
- 9 类验证项全部有明确检查点和通过/失败信号
