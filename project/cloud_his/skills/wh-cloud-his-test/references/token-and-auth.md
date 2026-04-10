# cloud_his Token 与鉴权

## 请求头

- `cloud_his` 常规请求头使用 `token`
- 不要默认改成 `Authorization: Bearer ...`

## Redis 键

- 登录态常用键前缀：
  - `TOKEN:SYS:`
- 一个可复用的测试 token 例子：
  - header: `token: codex-cloud-his-dev-token`
  - redis key: `TOKEN:SYS:codex-cloud-his-dev-token`

## Redis 值格式

- 不是 JDK 二进制序列化
- 是 Fastjson 文本，且带 `@type`
- 目标类型：
  - `com.whxx.base.domain.bo.OnlineUserModel`

示例值：

```json
{
  "@type": "com.whxx.base.domain.bo.OnlineUserModel",
  "token": "codex-cloud-his-dev-token",
  "loginSuccess": 1,
  "hospitalId": "2002215039761940480",
  "hospitalName": "开发环境测试医院",
  "userId": "codex-dev-user",
  "userCode": "codex",
  "userName": "Codex Dev",
  "appId": "HIS-PC",
  "loginSoftId": "10001",
  "loginOfficeCode": "DEV",
  "loginOfficeName": "开发联调科室"
}
```

## 最小必填建议

跨服务联调时，优先至少提供这些字段：

- `@type`
- `token`
- `loginSuccess=1`
- `hospitalId`
- `hospitalName`
- `userId`
- `userCode`
- `userName`
- `appId`
- `loginSoftId`

如果目标链路还会读取科室、病区、职称，再补这些字段：

- `loginOfficeId`
- `loginOfficeCode`
- `loginOfficeName`
- `loginWardCode`
- `loginWardName`
- `jobTitle`
- `jobTitleName`

## 生成方式

使用脚本生成 payload 或直接写 Redis：

```bash
python3 /home/wcs/.codex/skills/wh-cloud-his-test/scripts/build_online_user_model.py \
  --token codex-cloud-his-dev-token \
  --hospital-id 2002215039761940480 \
  --hospital-name 开发环境测试医院
```

如果要直接写入 Redis：

```bash
python3 /home/wcs/.codex/skills/wh-cloud-his-test/scripts/build_online_user_model.py \
  --token codex-cloud-his-dev-token \
  --hospital-id 2002215039761940480 \
  --hospital-name 开发环境测试医院 \
  --apply \
  --redis-host 192.168.10.206 \
  --redis-port 6379 \
  --ttl-seconds 604800
```

## 使用准则

- 优先复用固定测试 token，避免每次重新造一套。
- 默认不要删除测试 token，方便后续联调复用。
- 如果接口链路只依赖 `hospitalId`，也不要偷懒只塞一个字段；保持一份完整、稳定的 dev 登录态更省事。
- Redis 连接信息以目标服务当前实际运行配置为准，不要硬编码沿用旧环境。
