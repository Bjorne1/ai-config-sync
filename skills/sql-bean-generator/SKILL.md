---
name: sql-bean-generator
description: "根据SQL数据库表结构自动生成Java的Bean、DAO和Service文件的代码生成器。当用户需要：(1) 根据SQL表结构生成Java实体类、(2) 为数据库表生成MyBatis-Plus的DAO和Service层代码、(3) 快速搭建标准的三层架构代码时使用此技能。"
---

# SQL Bean Generator

这个技能用于根据SQL数据库表结构自动生成标准的Java Bean、DAO和Service文件。

## 使用场景

当用户提供：
1. SQL DDL语句（CREATE TABLE语句）
2. 目标Java包路径（例如：`com.whxx.drg.dip`）

自动生成：
1. Bean实体类（放在指定包的`bean`子包下）
2. DAO接口（放在指定包的`dao`子包下）
3. Service服务类（放在指定包的`service`子包下，方法体保持为空）

## 代码规范

### Bean实体类规范

参考 `references/bean-template.java` 中的模板，Bean类需要包含：

1. **注解**:
   - `@ApiModel(description = "表注释")`
   - `@Data`
   - `@TableName(value = "表名")`

2. **字段规范**:
   - 使用驼峰命名
   - 主键字段使用 `@TableId(value = "id", type = IdType.ASSIGN_ID)`
   - 普通字段使用 `@TableField(value = "字段名")`
   - 所有字段添加 `@ApiModelProperty(value = "字段注释")`
   - 根据需要添加校验注解：`@NotBlank`、`@NotNull`、`@Size`

3. **标准字段**（所有表都应包含）:
   - `createTime` (LocalDateTime) - 创建时间，使用 `fill = FieldFill.INSERT`
   - `createBy` (String) - 创建者
   - `updateTime` (LocalDateTime) - 更新时间，使用 `fill = FieldFill.INSERT_UPDATE`
   - `updateBy` (String) - 更新者
   - `remark` (String) - 备注
   - `del` (Integer) - 删除标识，0正常1删除

4. **数据类型映射**:
   - `varchar` → `String`
   - `tinyint` → `Integer`
   - `int` → `Integer`
   - `bigint` → `Long`
   - `decimal` → `BigDecimal`
   - `datetime` → `LocalDateTime`
   - `date` → `LocalDate`
   - `text` → `String`

### DAO接口规范

参考 `references/dao-template.java` 中的模板，DAO接口需要：

1. 继承 `MPJBaseMapper<Bean类名>`
2. 添加 `@Mapper` 注解
3. 保持接口为空（不添加自定义方法）

### Service类规范

参考 `references/service-template.java` 中的模板，Service类需要：

1. 继承 `MPJBaseServiceImpl<DAO类名, Bean类名>`
2. 添加 `@Service` 注解
3. **类体保持为空**（不添加任何自定义方法）

## 工作流程

1. **解析SQL结构**:
   - 读取SQL文件内容
   - 提取表名、字段名、字段类型、字段注释
   - 提取表注释

2. **生成Bean类**:
   - 根据表名生成类名（转为驼峰命名，首字母大写）
   - 根据字段生成属性（转为驼峰命名）
   - 添加所有必要的注解和校验
   - 包含标准的创建/更新/删除字段

3. **生成DAO接口**:
   - 使用Bean类名生成DAO接口名（Bean类名 + "Dao"）
   - 继承MPJBaseMapper
   - 添加必要的导入和注解

4. **生成Service类**:
   - 使用Bean类名生成Service类名（Bean类名 + "Service"）
   - 继承MPJBaseServiceImpl
   - 添加必要的导入和注解
   - **保持类体为空，不添加任何方法**

5. **保存文件**:
   - Bean保存到：`{base_path}/bean/{BeanName}.java`
   - DAO保存到：`{base_path}/dao/{DaoName}.java`
   - Service保存到：`{base_path}/service/{ServiceName}.java`

## 注意事项

1. **包路径**必须是完整的Java包路径，例如：`com.whxx.drg.dip`
2. **SQL文件**可以是本地文件路径或直接的CREATE TABLE语句
3. Service类的方法体**必须保持为空**，具体业务方法由用户后续添加
4. 所有生成的代码都遵循项目现有的编码规范
5. 字段注释从SQL的COMMENT中提取
6. 表注释从CREATE TABLE语句的COMMENT中提取

## 示例用法

**用户输入**:
```
@path/to/table.sql
使用包路径：com.whxx.drg.dip
```

**生成结果**:
- `com/whxx/drg/dip/bean/TableName.java`
- `com/whxx/drg/dip/dao/TableNameDao.java`
- `com/whxx/drg/dip/service/TableNameService.java`
