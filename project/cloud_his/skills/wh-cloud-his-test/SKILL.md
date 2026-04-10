---
name: wh-cloud-his-test
description: 针对 `cloud_his` 仓库下 `wh-modules` 微服务的真实接口联调测试 skill。凡是用户提到 `cloud_his`、`ai-service`、`drg-service`、`his-service`、`emr-service`、`pay-service`、`report-service`、`interface-service` 的接口测试、联调、启动本地服务后验证、实际访问数据库/Redis/Nacos/Dify/第三方、或明确表示“只跑单测不够、要真实运行服务测”时，都应优先使用此 skill。必须优先真实启动目标 Java 服务并发起真实 HTTP 请求，不要只用 mock、单测或静态阅读替代。
---

# wh-cloud-his-test

面向 `cloud_his` 仓库的微服务接口测试流程。目标不是“看起来像测过”，而是让本地服务真的启动、真的连到开发环境依赖、真的发出请求，并把证据留下来。

## 适用范围

- 仓库根目录：`/home/wcs/projects/work-project/cloud_his`
- 目标模块：`wh-modules/*-service`
- 典型场景：
  - 本地启动 `ai-service`、`drg-service` 等微服务并联调接口
  - 验证接口是否真实访问数据库、Redis、Nacos、Dify 或其他外部依赖
  - 复现“单测发现不了，只有真实运行才会暴露”的问题
  - 校验 multipart、SSE、上传文件、登录 token、配置拉取、启动参数差异

## 核心原则

- 优先真实运行，不用 mock 假装联调完成。
- 优先按 `.vscode/launch.json` 的真实启动方式执行，不要想当然套统一命令。
- 先确认服务实际用了哪套配置，再启动。
- 先确认请求是否依赖 `token` 和 Redis 登录态，再发接口。
- 测试结论必须区分：
  - 本地 controller 前就失败
  - 本地业务层失败
  - 下游依赖失败
  - 下游依赖已真实命中且返回异常
- 不允许“静默降级”测试路径：缺工具、代理干扰、鉴权缺失都必须先显式处理，再继续联调。
- 临时 Redis token 默认保留，方便后续复用；只有用户明确要求才删除。

## 执行流程

### 0. 执行前预检（必须）

- 先检查基础命令：
  - `command -v curl`
  - `command -v rg`
  - `command -v ss`
  - `command -v redis-cli`
- 先检查代理环境变量：
  - `env | rg -i '^(http|https|all)_proxy=|^no_proxy='`
- 只要请求目标是本地服务（`127.0.0.1` / `localhost`），默认统一使用：
  - `curl --noproxy '*' ...`
- 本地联调地址默认固定为：
  - `http://127.0.0.1:<port>/<context-path>`
  - 不要混用 `localhost` 与代理自动路由。
- 如果接口依赖 Redis 登录态且 `redis-cli` 不可用：
  - 先用固定测试 token 直接试一次目标接口。
  - 若鉴权失败且必须新建 token，立即中止并明确报“缺少 redis-cli，无法写入登录态”，不要临时改成“无 token 路径”继续冒充验证通过。
- 如果本次任务包含“验证 Nacos 配置是否生效”，在启动前先拉取对应 dataId + group，确认目标键存在。

标准预检命令（可直接执行）：

```bash
command -v curl && command -v rg && command -v ss && command -v redis-cli
env | rg -i '^(http|https|all)_proxy=|^no_proxy='
```

### 1. 确认测试目标

- 先锁定：
  - 微服务名
  - 目标接口路径
  - 请求方式
  - 是否需要文件上传
  - 是否需要真实访问外部依赖
- 优先阅读：
  - 对应 controller
  - 对应 service
  - `.vscode/launch.json`
  - `src/main/resources/bootstrap*.yaml`
- 如果用户明确要求“实际联调”，不要停留在单测或源码推断。

### 2. 判定启动方式

- 默认先看 `.vscode/launch.json`，它比 `bootstrap.yaml` 更接近开发者真实启动方式。
- `cloud_his` 是 Maven 多模块工程。不要想当然在仓库根目录直接跑：
  - `mvn -pl wh-modules/<service> -am spring-boot:run`
- 上面这种写法在 `cloud_his` 里容易把聚合根工程当成运行目标，表现为：
  - 日志里先出现 `Building cloud-his`
  - 随后报错 `Unable to find a suitable main class`
- 遇到这个特征，不要继续等待，立刻改成以下任一方式：
  - `mvn -f 'wh-modules/<service>/pom.xml' spring-boot:run ...`
  - 或把 `workdir` 切到 `wh-modules/<service>` 后再执行 `mvn spring-boot:run ...`
- 如果 launch 配置里有：
  - `preLaunchTask`
  - `spring.cloud.nacos.config.enabled=false`
  - `spring.config.additional-location`
  - 自定义 profile
  则必须按 launch 配置走。
- 如果没有特殊 launch 覆盖，再按 `bootstrap.yaml` 的 profile 和 Nacos 配置启动。
- `drg-service` 是已知特殊例子，先读 [drg-service-startup.md](/home/wcs/.codex/skills/wh-cloud-his-test/references/drg-service-startup.md)。

### 3. 确认运行时依赖

- 在启动前确认：
  - 本地端口和 context-path
  - Nacos 地址、group、profile
  - Redis 地址
  - 数据库地址
  - 是否还会调用 Dify、Coze 或其他外部服务
- 这些信息优先来源于：
  - `.vscode/launch.json`
  - 运行时 yaml
  - Nacos 已拉取配置
  - 服务启动日志
- 如果服务是直接从 Nacos 拉配置，确认本地网络能访问对应依赖。

### 4. 准备登录 token

- 只要接口链路里会读 `LoginInfo`，就默认需要看 `token`。
- `cloud_his` 常规 header 名是 `token`，不是 `Authorization`。
- 登录态通常来自 Redis 键：
  - `TOKEN:SYS:<token>`
- 该值不是 JDK 序列化，而是带 `@type` 的 Fastjson 文本。
- 先尝试复用已有专用测试 token；如果没有，再创建一个固定 dev token。
- 使用脚本生成或直接写入：
  - [build_online_user_model.py](/home/wcs/.codex/skills/wh-cloud-his-test/scripts/build_online_user_model.py)
- 具体说明见 [token-and-auth.md](/home/wcs/.codex/skills/wh-cloud-his-test/references/token-and-auth.md)。

### 5. 真实启动服务

- 启动时尽量贴近开发者平时方式：
  - 能复用 launch 配置，就复用 launch 的 profile 和 vmArgs
  - CLI 启动时，等价还原这些参数
- 对 `cloud_his` 这类多模块工程，优先使用模块级启动命令：
  - 示例：`mvn -f 'wh-modules/ai-service/pom.xml' spring-boot:run -DskipTests -Dspring-boot.run.jvmArguments='-Dspring.profiles.active=dev -Dfile.encoding=UTF-8'`
- 启动后先看最前面的 Maven 构建目标是否正确：
  - 正确：`Building ai-service`
  - 错误：`Building cloud-his`
- 如果是错误目标，先停掉再重启，不要把这次启动当成“服务启动中”继续等待。
- 需要长期运行的服务：
  - 保存 PID
  - 保存日志文件
  - 等待启动完成后再发请求
- 判断启动成功至少满足一项：
  - 启动日志出现应用启动完成信息
  - 对应端口已监听
  - 本地健康接口或目标接口能收到非连接失败响应

### 6. 发真实请求

- 使用 `curl` 或等价真实 HTTP 请求。
- 请求本地服务时必须带 `--noproxy '*'`，防止系统代理把本地联调流量转发出去导致假失败。
- 如果是 multipart 测试：
  - 真的上传文件
  - 不要伪造 `MultipartFile`
- 如果用户要验证“内部是否真的又调用了 Dify/第三方”：
  - 至少保留一次本地接口响应
  - 再保留本地服务日志中的下游调用证据
- 对 Dify 类场景，优先找这类证据：
  - `【Dify 上传文件】`
  - `【Dify 对话流】`
  - `【Dify 工作流】`

### 7. 输出结论

- 结论必须包含：
  - 本地接口是否成功
  - 服务是否真实启动
  - 是否真实连接数据库/Redis/Nacos
  - 是否真实访问到 Dify/第三方
  - 失败发生在哪一层
- 如果失败，说明是：
  - 启动失败
  - 代理干扰（请求未直达本地服务）
  - 工具缺失（如 redis-cli 不可用导致无法准备登录态）
  - 鉴权失败
  - 请求在 AOP / filter / interceptor 前后被拦截
  - 业务层校验失败
  - 下游网络或参数失败

### 8. 收尾

- 默认停止本次临时启动的服务进程，避免影响后续测试。
- 默认保留临时 Redis token，不要删除。
- 如果本次改了代码或配置，最后再做一次工作区检查。

## 针对 `ai-service` 的额外规则

- Dify 文件/图片测试，优先验证阻塞接口，再看流式接口。
- 本地启动 `ai-service` 时，默认优先使用：
  - `mvn -f 'wh-modules/ai-service/pom.xml' spring-boot:run -DskipTests -Dspring-boot.run.jvmArguments='-Dspring.profiles.active=dev -Dfile.encoding=UTF-8'`
- 不要在仓库根目录直接用 `-pl wh-modules/ai-service -am spring-boot:run` 代替，上一次实测已经证明这会误命中根工程。
- 当用户要求验证“实际调用了几次 Dify”时，必须用真实本地服务和真实 Dify 返回证明，不要只看代码。
- 如果 multipart 请求在业务层前就失败，优先排查：
  - `base-log`
  - 请求参数日志序列化
  - `MultipartFile` / `List<MultipartFile>` 处理

## 针对 `drg-service` 的额外规则

- 不要想当然按 `dev + DEFAULT_GROUP` 启动。
- 先确认 launch 是否要求：
  - `prepare-drg-wsl-config.sh`
  - `wcs` profile
  - 本地 runtime yaml
- 如果 launch 已经显式关闭 Nacos 配置拉取，就不要再假设服务会实时从 Nacos 取配置。

## 输出模板

优先用简洁结构输出：

```md
测试结果：
- 本地服务：已启动 / 未启动
- 本地接口：成功 / 失败
- 代理状态：已禁用本地代理 / 未禁用
- token准备：复用已有 / 新建写入 / 缺工具未执行
- 数据库：已连接 / 未验证 / 未连接
- Redis：已连接 / 未验证 / 未连接
- Nacos：已拉取 / 本地覆盖 / 未验证
- Dify/第三方：已访问 / 未访问 / 失败

关键证据：
- 启动命令或关键 vmArgs
- 关键请求示例
- 关键响应摘要
- 关键日志摘录

结论：
- 根因或当前阻断点
```

## 示例触发语句

- `帮我真实启动 ai-service，测一下 chatFlow 接口有没有真的访问到 Dify`
- `drg-service 这个接口别只跑单测，按本地启动方式联调一下`
- `我怀疑是 token 或 Redis 登录态的问题，你实际跑服务测一下`
- `帮我测 cloud_his 里的 multipart 接口，看看问题是在 controller 还是下游`
