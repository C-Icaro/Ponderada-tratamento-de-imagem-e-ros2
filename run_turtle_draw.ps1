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

wsl -d Ubuntu-24.04 -- bash -lc "cd '$linuxWorkspace' && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch turtle_draw_dog turtle_draw.launch.py max_points:=1800 target_width:=230 stroke_speed:=4.0"
