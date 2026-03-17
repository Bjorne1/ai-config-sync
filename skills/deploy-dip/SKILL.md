---
name: deploy-dip
description: 打包并部署 DIP 前端页面到 Windows 目录。当用户说「打包 dip」、「部署 dip」、「build dip」、「deploy dip」、「构建 dip」、「发布 dip」、「上线 dip」时触发此 skill。即使用户只是说「dip 打包一下」或「帮我把 dip 发布出去」也应触发。
---

# deploy-dip

按以下步骤完整执行 DIP 前端的构建、压缩、传输流程。每步完成后告知用户进度。

## 环境信息

- 项目根目录：`/home/wcs/projects/work-project/cloud-his-web`
- Node 版本：v24.13.0（通过 nvm 管理）
- 构建产物目录：`dist/micro_dip`
- 目标路径：`/mnt/e/deploy-project/micro_dip.tar.gz`

## 执行步骤

所有命令都需要先激活 nvm 环境，统一用以下前缀：

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use v24.13.0
```

### 第 1 步：构建 @db/postcss 依赖

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use v24.13.0 && \
  cd /home/wcs/projects/work-project/cloud-his-web && \
  pnpm run --filter "@db/postcss" build
```

这一步确保 PostCSS 配置包已构建，DIP 构建时会依赖它。

### 第 2 步：构建 @his/dip

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use v24.13.0 && \
  cd /home/wcs/projects/work-project/cloud-his-web && \
  pnpm run --filter "@his/dip" build
```

### 第 3 步：压缩并传输

```bash
cd /home/wcs/projects/work-project/cloud-his-web && \
  tar -czf /mnt/e/deploy-project/micro_dip.tar.gz -C dist micro_dip && \
  echo "传输完成"
```

## 常见问题处理

- **node_modules 缺失**：在第 1 步前先执行 `pnpm install`
- **@db/postcss dist 不存在**：第 1 步会解决此问题，不要跳过
- **路径大小写错误**：`core/components/index.ts` 中引用的是 `./src/exCol`（小写 e），如遇到 `ExCol` 解析失败需检查此文件
- **/mnt/e 不可访问**：检查 Windows E 盘是否正常挂载
