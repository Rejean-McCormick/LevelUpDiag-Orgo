param(
  [ValidateSet('baseline','quick','standard','embedded','database','build','security','deep','acceptance')]
  [string]$Campaign = 'quick',
  [string]$Target = ''
)
$ErrorActionPreference = 'Stop'
# Never initialize or change credentials, permissions, databases or packages here.
$DiagArgs = @("$PSScriptRoot/levelupdiag.py")
if ($Target) { $DiagArgs += @('--target', $Target) }
$DiagArgs += @('run', $Campaign)
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3 @DiagArgs
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  & python @DiagArgs
} else {
  Write-Error 'Install Python 3.10+ and reopen PowerShell.'
  exit 30
}
exit $LASTEXITCODE
