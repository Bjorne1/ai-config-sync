---
name: wh-cloud-his-runtime-test
description: "cloud_his 统一真实联调测试入口。用于 ai-service、drg-service、emr-service、his-service、interface-service、pay-service、report-service 的真实启动、真实请求、Redis token、数据库只读核对、失败分层。凡是用户要求不要只跑 Test、要实际启动服务并联调接口时使用。"
---

# wh-cloud-his-runtime-test

统一真实联调测试入口。先按契约判断能不能测，再用脚本自动化预检、启动、请求、核对、清理。

## 运行时控制面

运行时只认以下契约和脚本，不从其他文档推导行为：

- `contracts/service-capability-matrix.yaml`
- `contracts/test-task-spec.yaml`
- `references/verification-plan.md`
- `scripts/` 下的可执行脚本

## 服务范围

`ai-service` · `drg-service` · `emr-service` · `his-service` · `interface-service` · `pay-service` · `report-service`

## 执行原则

- 先验契约，后跑服务。契约不完整直接停。
- 示例任务用于复用高频场景，不是接口白名单；用户直接指定接口时不要求先出现在示例里。
- 不对缺证据服务做静默降级。
- 数据写入只通过真实接口，不靠 skill 直写数据库。
- 只有接口本身产生可核对的业务数据变更才做数据库核对；纯转发/纯查询/仅写日志的接口不强行查库。
- 控制器家族模板复用共性规则，不把子接口的查库要求强压给整个前缀。
- Redis 地址/库号严格从服务配置解析，禁止默认 127.0.0.1。
- `ensure-dev-token.py` 只负责"写入和校验模拟 token"，它的 Redis 配置不代表项目运行时实际连接的 Redis。报告中必须将"模拟 token 用的 Redis"和"项目运行时 Redis"分开标注。
- 就绪检查和接口存在性检查必须同时传 `--endpoint` 和 `--method`，不能只传路径。
- 每次测试前运行 `scripts/clear-service-logs.sh --service <name>` 清空日志，确保日志核对只扫描本次测试产生的记录。
- 请求后不检查 token TTL 变化。项目运行时可能续期或刷新 TTL，TTL 漂移是正常现象。skill 只需证明"请求前 token 可用"，必要时补"请求后 token 仍可读"。

## 运行流程

### 1. 契约校验

运行 `scripts/run-preflight.sh --service <name> --task-id <id> --json` 或 `--endpoint <path> --method <METHOD> --json`。

脚本自动完成：服务矩阵存在性、必填字段、枚举合法性、占位值检测、db_scope 校验、BLOCKED/REQUIRES_MANUAL_CONFIRMATION 门控、启动计划解析。

### 2. 预检（复用已运行服务时必做）

| 检查项 | 脚本 | 判定 |
|--------|------|------|
| 构建产物新鲜度 | `scripts/check-build-freshness.sh --module-path <path> --run-mode classes --json` | `verdict=stale` → 先重新构建 |
| 接口存在性 | `scripts/check-endpoint-exists.py --port <port> --endpoint <path> --method <METHOD> --json` | `found=false` → 判定旧进程 |
| emr→ai 转发可达 | `scripts/check-ai-relay.sh --json`（仅 emr-service + /v1/aiAssistant/* 时，可加 `--probe-path <业务接口>` 提高准确率） | `verdict≠reachable` → 先启动 ai-service |

产物新鲜度或接口存在性任一未通过 → 先重启到最新代码再继续。

### 3. 启动

- 按契约的启动计划启动服务。
- **启动前**：运行 `scripts/clear-service-logs.sh --service <name> --json` 清空服务日志，确保后续日志核对不受历史记录干扰。
- **启动失败诊断**：启动失败时按以下优先级排查：① 端口被占用（`ss -tlnp | grep :<port>`）→ 报 `port_conflict`；② 配置错误（日志中搜索 `BeanCreationException`/`ConfigurationException`）→ 报 `config_error`；③ 依赖服务未起（日志中搜索 `Connection refused`）→ 报 `dependency_not_ready`。
- **就绪检查**：运行 `scripts/check-service-ready.sh --port <port> --endpoint <path> --method <METHOD> --timeout 300 --json`，`ready=false` 判 `startup_timeout`。必须同时传 `--endpoint` 和 `--method`。
- **脚本误报处理**：如果就绪检查报失败，但端口已监听且直接 curl 业务接口有 HTTP 响应（非 000），判定为脚本误报而非服务未就绪，继续执行后续步骤。

### 4. 请求与核对

- **HTTP 请求**：运行 `scripts/exec-http-request.py --url <url> --method <METHOD> --json`（SSE 加 `--sse --sse-timeout 30`）。
  - `failure_category=http_failed_404_possible_stale_process` → 重跑 check-build-freshness + check-endpoint-exists 确认是否旧进程，是则重启后重试。
  - **瞬时重连判定**：如果请求失败且响应体/日志中出现 `Connection reset`、`Broken pipe`、`连接被重置` 等信号，但同时段日志中又出现重连成功记录，归类为"项目内部瞬时 Redis 波动"。此时不重启服务、不重编译、不重建环境，仅短等待（5~10s）后重放同一请求。第一次失败、第二次成功 → 判本次测试通过，但报告中标注 `transient_reconnect: true`。重试后仍然失败 → 归因为 `runtime_redis_transient`（项目运行时 Redis 短时异常），不归为 skill 配置问题。
- **日志核对**：运行 `scripts/check-log-markers.py --log-file <path> --markers '<json>' --json`，`verdict=fail` 判 `log_evidence_missing`。因为测试前已清空日志，匹配到的一定是本次请求产生的记录。markers 优先使用本次请求中的唯一标识（如请求体中的特征词），其次才用 controller 中的 log.info 通用关键词。
- **Redis 核对**：运行 `scripts/check-redis-token.py --service <name> --json`。脚本自动从服务配置解析真实 Redis 地址/库号，校验连通性 + token 存在性。不检查 TTL 值。`verdict=redis_unreachable` 时优先输出"实际 Redis 地址、库号、连通性"三项诊断信息，再排查接口问题。报告中必须分开标注"模拟 token Redis"和"项目运行时 Redis"。
- **数据库核对**：运行 `scripts/query-dev-db.sh <db> --sql "<sql>"`，仅在 `expected_db_checks` 声明为 `required` 或具体子接口要求时执行。
- **下游证据**：按契约的 `expected_downstream_evidence` 在日志中查找。

### 5. 清理

- Token 不做额外管理；过期后下次写入时自动设置 `TTL=-1`。
- Redis 临时数据走自身过期。
- 非 Redis 数据按 `cleanup_targets` 执行。

## 直接接口模式

常规能力，不是例外路径：

1. 定位所属服务 → controller 确认请求方式。
2. 预检（命中家族前缀时自动复用模板规则）。
3. 启动 → 请求 → 核对。

## 失败分类

| 类别 | 来源 |
|------|------|
| `contract_invalid` | 契约校验 |
| `preflight_blocked` / `launch_blocked` | 预检 |
| `manual_confirmation_required` | 服务需人工确认 |
| `startup_timeout` | check-service-ready (300s) |
| `port_conflict` / `config_error` / `dependency_not_ready` | 启动失败诊断 |
| `script_false_negative` | 脚本报失败但端口+真实请求正常 |
| `request_timeout` | exec-http-request (普通 60s / SSE 30s) |
| `http_failed` / `http_failed_auth` / `http_failed_404_possible_stale_process` | exec-http-request |
| `sse_business_error` | exec-http-request SSE 模式业务级失败（HTTP 200 但内容含错误信号） |
| `log_evidence_missing` | check-log-markers |
| `redis_check_failed` / `redis_unreachable` / `db_check_failed` | 核对阶段 |
| `runtime_redis_transient` | 项目运行时 Redis 瞬时波动（重试后仍失败时） |
| `downstream_evidence_missing` | 下游证据缺失 |
| `cleanup_failed` | 清理阶段 |

## 通过标准

服务启动成功 + HTTP 响应符合预期 + 日志证据存在 + Redis 核对通过 + 数据库核对通过（仅适用时）+ 下游证据存在 + 失败层级可定位。

## 速查：各服务核对要求

| 服务 | Token | Redis核对 | DB核对 | 下游证据 | 前置动作 |
|------|-------|----------|--------|---------|---------|
| ai-service | ✗ | ✗ | 按接口 | dify | 无 |
| drg-service | 条件 | ✓(runtime file) | wh_drg | - | prepare-drg-wsl-config |
| emr-service | ✓ | ✓(profile config) | 按子接口 | ai+his | 无 |
| his-service | ✓ | ✓(profile config) | his | - | 无 |
| interface-service | 条件 | 待确认 | his+wh_system | - | 需人工确认 |
| pay-service | 条件 | 待确认 | wh_pay+wh_system | - | 需人工确认 |
| report-service | ✓ | 待确认 | wh_report+wh_system | - | BLOCKED |

## 脚本清单

| 脚本 | 用途 |
|------|------|
| `run-preflight.sh` | 契约校验 + 启动计划 |
| `resolve-launch-plan.py` | 启动计划解析 |
| `ensure-dev-token.py` | Token 写入（默认 TTL=-1） |
| `check-build-freshness.sh` | 构建产物新鲜度检测 |
| `check-endpoint-exists.py` | 接口存在性校验 |
| `check-redis-token.py` | Redis 连通性 + token 存在性（自动解析服务配置地址） |
| `check-service-ready.sh` | 服务就绪轮询 |
| `exec-http-request.py` | HTTP 请求执行 + 结构化校验 |
| `check-log-markers.py` | 日志标记扫描 |
| `check-ai-relay.sh` | emr→ai 转发可达性 |
| `clear-service-logs.sh` | 测试前清空服务日志 |
| `mysql_query.py` / `query-dev-db.sh` | 数据库只读查询 |
