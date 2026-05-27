param(
    [string]$ClientRoot = "G:\Battle.net Games\World of Warcraft\_anniversary_",
    [string]$AddonName = "BigBiSList",
    [switch]$NoClean,
    [switch]$AllowOtherClient
)

$ErrorActionPreference = "Stop"

function Get-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function Assert-SafeAddonTarget {
    param(
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][string]$AddonName
    )

    $fullTarget = Get-FullPath $TargetPath
    $expectedSuffix = "\Interface\AddOns\$AddonName"
    if (-not $fullTarget.EndsWith($expectedSuffix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean unsafe target path: $fullTarget"
    }
}

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$tocPath = Join-Path $repoRoot "$AddonName.toc"
if (-not (Test-Path -LiteralPath $tocPath -PathType Leaf)) {
    throw "Could not find addon TOC: $tocPath"
}

$clientRootPath = Resolve-Path -LiteralPath $ClientRoot
$clientRootFull = Get-FullPath $clientRootPath
$clientLeaf = Split-Path -Leaf $clientRootFull.TrimEnd("\")
if (-not $AllowOtherClient -and $clientLeaf -ne "_anniversary_") {
    throw "Refusing to deploy to non-anniversary client root: $clientRootFull. Pass -AllowOtherClient to override."
}

$addonsRoot = Join-Path $clientRootFull "Interface\AddOns"
$targetRoot = Join-Path $addonsRoot $AddonName
Assert-SafeAddonTarget -TargetPath $targetRoot -AddonName $AddonName

$tocEntries = Get-Content -LiteralPath $tocPath | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $line
    }
}

$deployEntries = [System.Collections.Generic.List[string]]::new()
[void]$deployEntries.Add("$AddonName.toc")
foreach ($entry in $tocEntries) {
    if (-not $deployEntries.Contains($entry)) {
        [void]$deployEntries.Add($entry)
    }
}

if (-not $NoClean -and (Test-Path -LiteralPath $targetRoot)) {
    Remove-Item -LiteralPath $targetRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null

$copied = 0
foreach ($entry in $deployEntries) {
    $source = Join-Path $repoRoot $entry
    $target = Join-Path $targetRoot $entry

    if (-not (Test-Path -LiteralPath $source)) {
        throw "TOC entry not found in repo: $entry"
    }

    $targetParent = Split-Path -Parent $target
    New-Item -ItemType Directory -Path $targetParent -Force | Out-Null

    if (Test-Path -LiteralPath $source -PathType Container) {
        Copy-Item -LiteralPath $source -Destination $targetParent -Recurse -Force
    } else {
        Copy-Item -LiteralPath $source -Destination $target -Force
    }
    $copied += 1
}

Write-Host "Deployed $copied addon entries to $targetRoot"
