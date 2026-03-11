---
name: sql-to-bean
description: "根据数据库现有表结构或 SQL DDL 自动生成 Java Bean、DAO 和 Service。只要用户提到数据库名+表名、MySQL 表、CREATE TABLE、实体类、MyBatis-Plus DAO/Service、三层代码生成，就优先使用此技能。优先直接连库读取真实表结构；对 wh_drg/wh-drg 场景要联动 wh-drg-mysql skill 自动查询，只有拿不到表结构时才要求用户提供 SQL DDL。"
---

# SQL To Bean

这个技能用于根据数据库表结构自动生成标准的 Java Bean、DAO 和 Service 文件。

优先使用数据库直连模式，直接读取真实表结构；只有在当前会话没有可用的数据库连接能力时，才退回到 SQL DDL 模式。不要一上来就要求用户粘贴 `CREATE TABLE`。

## 触发场景

当用户需要下面任意一种能力时使用本技能：

1. 根据数据库中的现有表生成 Java 实体类
2. 为数据库表生成 MyBatis-Plus / MPJ 的 DAO、Service 骨架
3. 根据 `CREATE TABLE` 语句生成标准三层代码
4. 从“数据库名 + 表名”直接反推 Java 三层代码

## 输入模式

### 模式 A：数据库直连模式（优先）

当用户提供以下信息时，优先使用数据库直连模式：

1. 数据库名
2. 表名
3. 目标 Java 包路径，例如 `com.whxx.drg.dip`

如果用户同时给了数据库名、表名和 DDL：

1. 默认优先以数据库中的真实表结构为准
2. 只有在用户明确说明“DDL 比数据库更新”时，才改用 DDL

### 模式 B：SQL DDL 模式（回退）

仅当出现下列情况时，才让用户提供 DDL：

1. 当前会话没有可用的数据库连接能力
2. 目标库不是 `wh_drg`，且当前会话也没有其他对应的数据库技能或连接方式
3. 用户明确要求以手头的 `CREATE TABLE` 语句为准

## 数据库直连工作流

### 1. 识别数据库来源

1. 如果用户提到 `wh-drg` 数据库，把它规范化为实际数据库名 `wh_drg`
2. 如果目标库是 `wh_drg`，立即联动 `wh-drg-mysql` skill
3. 不要先要求用户补 DDL；先尝试自行读取表结构

### 2. 读取表结构

对 `wh_drg` 场景，优先使用 `wh-drg-mysql` skill 中的 `scripts\mysql_query.py`。

优先顺序：

1. 先执行 `SHOW CREATE TABLE`，把数据库中的建表语句取出来
2. 再按 DDL 解析流程生成代码
3. 如果 `SHOW CREATE TABLE` 不足以判断列注释、可空、主键或长度，再补查 `information_schema`

具体查询参考 `references\mysql-introspection.md`。

为什么这样做：

1. `SHOW CREATE TABLE` 最接近用户手写 DDL，能复用已有解析思路
2. `DESCRIBE` 缺少注释信息，不能作为唯一结构来源
3. `SELECT *` 是查数据，不是查结构，不要拿样例数据倒推字段定义
4. 如果表不存在或数据库报错，要把错误直接暴露给用户，不要生成伪造代码

### 3. 非 wh_drg 数据库

如果用户只给了“数据库名 + 表名”，但当前会话没有该数据库的连接技能或可执行查询方式：

1. 明确告诉用户当前缺少该库的连接能力
2. 显式要求用户提供 `CREATE TABLE` DDL
3. 不要伪造结构，不要根据表名猜字段

## SQL DDL 模式工作流

当用户提供本地 `.sql` 文件路径或直接提供 `CREATE TABLE` 语句时：

1. 读取 DDL 内容
2. 提取表名、字段名、字段类型、字段注释
3. 提取表注释
4. 按下面的代码规范生成 Bean、DAO、Service

## 代码生成规范

### Bean 实体类

参考 `references\bean-template.java`。

Bean 类需要包含：

1. `@ApiModel(description = "表注释")`
2. `@Data`
3. `@TableName(value = "表名")`

字段规则：

1. 字段名转为驼峰命名
2. 主键字段使用 `@TableId`
3. 普通字段使用 `@TableField(value = "字段名")`
4. 所有字段添加 `@ApiModelProperty(value = "字段注释")`
5. 根据字段约束添加 `@NotBlank`、`@NotNull`、`@Size`
6. 生成出来的字段以真实表结构为准，不要凭空补数据库里不存在的列

项目中常见标准字段通常包括：

1. `create_time`
2. `create_by`
3. `update_time`
4. `update_by`
5. `remark`
6. `del`

如果这些字段真实存在，就按模板添加对应注解；如果表里没有，就不要硬加，应该向用户暴露这个差异。

主键规则：

1. 如果主键是约定俗成的 `id`，可以沿用模板中的 `IdType.ASSIGN_ID`
2. 如果主键不是 `id`，仍然使用 `@TableId`，但字段名和 Java 类型要按真实结构生成

### DAO 接口

参考 `references\dao-template.java`。

DAO 接口需要：

1. 继承 `MPJBaseMapper<Bean类名>`
2. 添加 `@Mapper`
3. 保持接口为空，不添加自定义方法

### Service 类

参考 `references\service-template.java`。

Service 类需要：

1. 继承 `MPJBaseServiceImpl<DAO类名, Bean类名>`
2. 添加 `@Service`
3. 类体保持为空，不添加任何自定义方法

### 数据类型映射

1. `varchar` → `String`
2. `char` → `String`
3. `tinyint` → `Integer`
4. `int` → `Integer`
5. `bigint` → `Long`
6. `decimal` → `BigDecimal`
7. `datetime` → `LocalDateTime`
8. `timestamp` → `LocalDateTime`
9. `date` → `LocalDate`
10. `text` / `longtext` → `String`

## 输出路径

将包路径转成目录后，按下面结构输出：

1. Bean：`{base_path}\bean\{BeanName}.java`
2. DAO：`{base_path}\dao\{DaoName}.java`
3. Service：`{base_path}\service\{ServiceName}.java`

## 注意事项

1. 包路径必须是完整 Java 包名，例如 `com.whxx.drg.dip`
2. 对 `wh_drg` 场景，优先使用数据库直连模式，不要先索要 DDL
3. 用户口语里的 `wh-drg` 应视为数据库 `wh_drg`
4. Service 类的方法体必须保持为空
5. 表注释优先来自数据库真实结构；DDL 模式下来自 `CREATE TABLE ... COMMENT`
6. 字段注释优先来自数据库真实结构；DDL 模式下来自字段 `COMMENT`
7. 如果目标表不存在，直接告知用户表不存在，不要猜测字段结构

## 示例

**示例 1：优先直连数据库**

用户输入：

```text
帮我给 wh-drg 数据库的 drg_cc 表生成标准三层代码，包路径用 com.whxx.drg.cc
```

期望动作：

1. 识别 `wh-drg` = `wh_drg`
2. 使用 `wh-drg-mysql` skill 查询 `wh_drg.drg_cc` 的建表结构
3. 生成 `bean`、`dao`、`service` 三个文件

**示例 2：无法直连时回退到 DDL**

用户输入：

```text
目标库是 billing_prod，表是 invoice_record，包路径 com.demo.billing。当前环境没法连库，你按这段 CREATE TABLE 来生成。
```

期望动作：

1. 明确当前没有库连接能力
2. 使用用户提供的 DDL 继续生成

**示例 3：传统 DDL 输入**

用户输入：

```text
@path\to\table.sql
使用包路径：com.whxx.drg.dip
```

生成结果：

1. `com\whxx\drg\dip\bean\TableName.java`
2. `com\whxx\drg\dip\dao\TableNameDao.java`
3. `com\whxx\drg\dip\service\TableNameService.java`
