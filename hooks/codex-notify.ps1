param(
    [string]$Message = ""
)

# 保底逻辑：如果 Codex 没传内容或者传了原始占位符 %s
if ($Message -eq "%s" -or [string]::IsNullOrWhiteSpace($Message)) {
    $DisplayMessage = "任务已完成，点击查看代码。"
} else {
    $DisplayMessage = $Message
}

# 确保模块已安装
if (-not (Get-Module -ListAvailable -Name BurntToast)) {
    Install-Module -Name BurntToast -Force -Scope CurrentUser -Confirm:$false
}

$iconPath = "D:\wcs_project\AGENT\hooks\codex.png"

$params = @{
    Text  = "OpenAI Codex", $DisplayMessage 
    Sound = 'Reminder'
}

if (Test-Path $iconPath) {
    $params.Add("AppLogo", $iconPath)
}

New-BurntToastNotification @params