param([switch]$ExternalOnly)

$ErrorActionPreference = "Stop"

$workspace = $PSScriptRoot

function Convert-ToWslPath {
  param([string]$WindowsPath)

  $resolved = (Resolve-Path -LiteralPath $WindowsPath).Path
  if ($resolved -notmatch "^([A-Za-z]):\\(.*)$") {
    throw "Only drive-letter paths are supported: $resolved"
  }

  $drive = $Matches[1].ToLowerInvariant()
  $rest = $Matches[2] -replace "\\", "/"
  return "/mnt/$drive/$rest"
}

$linuxWorkspace = Convert-ToWslPath $workspace

Write-Host "Starting Turtle Draw Dog..."
Write-Host "Workspace: $workspace"
Write-Host ""

$externalOnlyValue = if ($ExternalOnly) { "true" } else { "false" }
$maxPoints = if ($ExternalOnly) { "700" } else { "1800" }

wsl -d Ubuntu-24.04 -- bash -lc "cd '$linuxWorkspace' && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch turtle_draw_dog turtle_draw.launch.py max_points:=$maxPoints target_width:=230 stroke_speed:=4.0 external_only:=$externalOnlyValue"
