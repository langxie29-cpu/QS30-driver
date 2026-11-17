param([string]$EvidencePath)
$ErrorActionPreference = 'Stop'
$qsTarget = (Resolve-Path -LiteralPath $EvidencePath).Path
$qsAllowed = ($qsTarget -like 'D:\PROJECTS\dsharness\QS30-power-loop-*\projects\QS30-9_24V\power_loop_*') -or ($qsTarget -like 'D:\PROJECTS\dsharness\QS30-power-loop-*\projects\QS30-9_24V\safety_r1') -or ($qsTarget -eq 'D:\PROJECTS\dsharness\QS30-1\projects\QS30-9_24V\safety_r1') -or ($qsTarget -eq 'D:\PROJECTS\dsharness\QS30-1\projects\QS30-9_24V\sim\s06c_current_cell_v3\ST_AUX12_1ns')
if (-not $qsAllowed) { throw 'Target outside named evidence roots' }
$qsIdentity = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-21-4065676245-3946077577-4150095191-500')
$qsAcl = Get-Acl -LiteralPath $qsTarget
foreach ($qsDeny in @($qsAcl.Access | Where-Object { $_.AccessControlType -eq 'Deny' -and -not $_.IsInherited -and $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value -eq $qsIdentity.Value })) { [void]$qsAcl.RemoveAccessRuleSpecific($qsDeny) }
# Explicit access bits; icacls W adds Synchronize and would also prevent ordinary reads.
$qsRule = [System.Security.AccessControl.FileSystemAccessRule]::new($qsIdentity,[System.Security.AccessControl.FileSystemRights]0x10156,[System.Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit',[System.Security.AccessControl.PropagationFlags]::None,[System.Security.AccessControl.AccessControlType]::Deny)
$qsAcl.AddAccessRule($qsRule)
Set-Acl -LiteralPath $qsTarget -AclObject $qsAcl
Get-Acl -LiteralPath $qsTarget | Select-Object Path,Sddl | ConvertTo-Json
