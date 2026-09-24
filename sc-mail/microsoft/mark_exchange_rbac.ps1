param(
  [string]$TenantId = "890486d6-532e-4054-a508-02e1e4b48806",
  [string]$AdminUpn = "msorrillo@numbersetcandetc.com",
  [string]$TargetMailbox = "Marks@numbersetcandetc.com",
  [string]$AppId = "5dd759b8-affa-474a-9973-7e1ec0f4fe20"
)
$ErrorActionPreference = "Stop"
$ScopeName = "Supreme Mail - Mark mailbox only"
$AssignmentName = "Supreme Mail - Mark - Application Mail.Send"

if (-not (Get-Module -ListAvailable -Name Microsoft.Graph.Authentication)) { Install-Module Microsoft.Graph -Scope CurrentUser -Force -AllowClobber }
if (-not (Get-Module -ListAvailable -Name ExchangeOnlineManagement)) { Install-Module ExchangeOnlineManagement -Scope CurrentUser -Force -AllowClobber }
Import-Module Microsoft.Graph.Authentication
Import-Module Microsoft.Graph.Applications
Import-Module ExchangeOnlineManagement

Connect-MgGraph -TenantId $TenantId -Scopes "Application.ReadWrite.All" -NoWelcome
$sp = Get-MgServicePrincipal -Filter "appId eq " | Select-Object -First 1
if (-not $sp) { $sp = New-MgServicePrincipal -AppId $AppId }

Connect-ExchangeOnline -UserPrincipalName $AdminUpn -ShowBanner:$false
$exoSp = Get-ServicePrincipal -Identity $AppId -ErrorAction SilentlyContinue
if (-not $exoSp) {
  New-ServicePrincipal -AppId $AppId -ObjectId $sp.Id -DisplayName "Supreme Mail Mark" | Out-Null
}
$scope = Get-ManagementScope -Identity $ScopeName -ErrorAction SilentlyContinue
if (-not $scope) {
  New-ManagementScope -Name $ScopeName -RecipientRestrictionFilter "PrimarySmtpAddress -eq " | Out-Null
}
$assignment = Get-ManagementRoleAssignment -Identity $AssignmentName -ErrorAction SilentlyContinue
if (-not $assignment) {
  New-ManagementRoleAssignment -Name $AssignmentName -App $sp.Id -Role "Application Mail.Send" -CustomResourceScope $ScopeName | Out-Null
}
$test = Test-ServicePrincipalAuthorization -Identity $sp.Id -Resource $TargetMailbox
$permit = @($test | Where-Object { $_.RoleName -eq "Application Mail.Send" -and $_.InScope -eq $true }).Count -gt 0
[ordered]@{
  state = $(if ($permit) {"PERMIT"} else {"HOLD"})
  tenant_id = $TenantId
  app_id = $AppId
  service_principal_object_id = $sp.Id
  mailbox = $TargetMailbox
  role = "Application Mail.Send"
  in_scope = $permit
  tenant_wide_mail_send_permission = $false
  observed_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json -Compress
Disconnect-ExchangeOnline -Confirm:$false
Disconnect-MgGraph | Out-Null
if (-not $permit) { exit 12 }
