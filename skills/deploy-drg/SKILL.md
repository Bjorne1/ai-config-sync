---
name: deploy-drg
description: 打包并部署 drg-service 到 Windows 目录。当用户说「打包 drg」、「部署 drg」、「build drg」、「deploy drg」、「构建 drg」、「发布 drg」、「上线 drg」时触发此 skill。即使用户只是说「drg 打包一下」或「帮我把 drg 发布出去」也应触发。
---

# deploy-drg

按以下步骤完整执行 drg-service 的打包、部署流程。每步完成后告知用户进度。

## 环境信息

- 项目根目录：`/home/wcs/projects/work-project/cloud_his`
- Java 路径：`/home/wcs/.local/opt/jdk8`
- 打包产物：`wh-modules/drg-service/target/drg-service.jar`
- 目标路径：`/mnt/e/deploy-project/drg-service.jar`

## 执行步骤

所有命令都需要先设置 JAVA_HOME 环境变量：

```bash
export JAVA_HOME=/home/wcs/.local/opt/jdk8 && export PATH=$JAVA_HOME/bin:$PATH
```

### 第 1 步：打包 drg-service

```bash
export JAVA_HOME=/home/wcs/.local/opt/jdk8 && export PATH=$JAVA_HOME/bin:$PATH && \
  cd /home/wcs/projects/work-project/cloud_his && \
  mvn clean package -pl wh-modules/drg-service -am -DskipTests
```

此命令会同时构建 drg-service 的所有依赖模块（base-domain、base-core、api-system、base-redis、base-log 等）。

### 第 2 步：拷贝到目标目录

```bash
cp -f /home/wcs/projects/work-project/cloud_his/wh-modules/drg-service/target/drg-service.jar /mnt/e/deploy-project/
```

## 常见问题处理

- **JAVA_HOME 未设置**：务必在命令前加 `export JAVA_HOME=/home/wcs/.local/opt/jdk8 && export PATH=$JAVA_HOME/bin:$PATH`
- **依赖下载慢**：首次打包需从 alimaven/maven_central 下载依赖，耐心等待，后续会使用本地缓存
- **BUILD FAILURE**：检查编译错误信息，通常是代码问题
- **/mnt/e 不可访问**：检查 Windows E 盘是否正常挂载
