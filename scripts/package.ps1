param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$addonSource = Join-Path $repoRoot "addon\BigBiSList"
$dist = Join-Path $repoRoot "dist"
$stagingRoot = Join-Path $dist "package"
$addonStage = Join-Path $stagingRoot "BigBiSList"
$zipPath = Join-Path $dist "BigBiSList-$Version.zip"

if (!(Test-Path -LiteralPath $addonSource)) {
    throw "Addon source not found: $addonSource"
}

New-Item -ItemType Directory -Path $dist -Force | Out-Null

$resolvedDist = (Resolve-Path $dist).Path
$resolvedStageParent = [System.IO.Path]::GetFullPath($stagingRoot)
if (!$resolvedStageParent.StartsWith($resolvedDist, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to stage package outside dist: $resolvedStageParent"
}

if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Path $addonStage -Force | Out-Null
Copy-Item -Path (Join-Path $addonSource "*") -Destination $addonStage -Recurse -Force

foreach ($doc in @("LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md")) {
    $source = Join-Path $repoRoot $doc
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $addonStage $doc) -Force
    }
}

$tocPath = Join-Path $addonStage "BigBiSList.toc"
$toc = Get-Content -LiteralPath $tocPath -Raw
$toc = $toc.Replace("@project-version@", $Version)
Set-Content -LiteralPath $tocPath -Value $toc -NoNewline

Compress-Archive -Path $addonStage -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item -LiteralPath $stagingRoot -Recurse -Force

Write-Output $zipPath
