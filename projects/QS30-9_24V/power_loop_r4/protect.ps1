param([string]$EvidencePath)
$ErrorActionPreference = 'Stop'
$qsTarget = (Resolve-Path -LiteralPath $EvidencePath).Path
$qsAllowed = $qsTarget.StartsWith('D:\PROJECTS\dsharness\QS30-power-loop-r4\projects\QS30-9_24V\power_loop_r4\experiments\') -or ($qsTarget -eq 'D:\PROJECTS\dsharness\QS30-power-loop-r3\projects\QS30-9_24V\power_loop_r3')
if (-not $qsAllowed) { throw 'Outside the named evidence roots' }
$qsIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$qsAcl = Get-Acl -LiteralPath $qsTarget
$qsRule = [System.Security.AccessControl.FileSystemAccessRule]::new($qsIdentity,[System.Security.AccessControl.FileSystemRights]0x10156,[System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit',[System.Security.AccessControl.PropagationFlags]::None,[System.Security.AccessControl.AccessControlType]::Deny)
$qsAcl.AddAccessRule($qsRule)
Set-Acl -LiteralPath $qsTarget -AclObject $qsAcl
Get-Acl -LiteralPath $qsTarget | Select-Object Path,Sddl | ConvertTo-Json
