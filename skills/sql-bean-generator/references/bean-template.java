package com.whxx.drg.dip.bean;

import com.baomidou.mybatisplus.annotation.*;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;
import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * @author  wcs
 * @description {表描述}
 * @date  {生成日期}
 */
@ApiModel(description = "{表描述}")
@Data
@TableName(value = "{表名}")
public class {ClassName} implements Serializable {
    private static final long serialVersionUID = 1L;

    /**
     * 主键ID
     */
    @TableId(value = "id", type = IdType.ASSIGN_ID)
    @ApiModelProperty(value = "主键ID")
    @Size(max = 20, message = "主键ID最大长度要小于 20")
    @NotBlank(message = "主键ID不能为空")
    private String id;

    /**
     * {字段注释}
     */
    @TableField(value = "{字段名}")
    @ApiModelProperty(value = "{字段注释}")
    @Size(max = {max_length}, message = "{字段注释}最大长度要小于 {max_length}")
    @NotBlank(message = "{字段注释}不能为空")  // 对于NOT NULL的varchar字段
    // @NotNull(message = "{字段注释}不能为null")  // 对于NOT NULL的数值字段
    private String {fieldName};  // 根据SQL类型映射为对应的Java类型

    /**
     * 创建时间
     */
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    @ApiModelProperty(value = "创建时间")
    private LocalDateTime createTime;

    /**
     * 创建者
     */
    @TableField(value = "create_by")
    @ApiModelProperty(value = "创建者")
    @Size(max = 255, message = "创建者最大长度要小于 255")
    private String createBy;

    /**
     * 更新时间
     */
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    @ApiModelProperty(value = "更新时间")
    private LocalDateTime updateTime;

    /**
     * 更新者
     */
    @TableField(value = "update_by")
    @ApiModelProperty(value = "更新者")
    @Size(max = 255, message = "更新者最大长度要小于 255")
    private String updateBy;

    /**
     * 备注
     */
    @TableField(value = "remark")
    @ApiModelProperty(value = "备注")
    @Size(max = 255, message = "备注最大长度要小于 255")
    private String remark;

    /**
     * 删除标识0正常1删除
     */
    @TableField(value = "del")
    @ApiModelProperty(value = "删除标识0正常1删除")
    @NotNull(message = "删除标识0正常1删除不能为null")
    private Integer del;
}
