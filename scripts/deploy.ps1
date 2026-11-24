param(
    [string]$ClientRoot,
    [string]$AddonName = "BigBiSList",
    [string]$LuaPath,
    [switch]$NoClean,
    [switch]$AllowOtherClient,
    [switch]$Prerelease,
    [ValidateSet("anniversary", "forever")][string]$Flavor = "anniversary"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

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
$expectedClient = if ($Flavor -eq "forever") { "_forever_" } else { "_anniversary_" }
$tocName = if ($Flavor -eq "forever") { "${AddonName}_Camelot.toc" } else { "$AddonName.toc" }
$tocPath = Join-Path $repoRoot $tocName
if (-not $ClientRoot) {
    $ClientRoot = Join-Path "G:\Battle.net Games\World of Warcraft" $expectedClient
}
if (-not (Test-Path -LiteralPath $tocPath -PathType Leaf)) {
    throw "Could not find addon TOC: $tocPath"
}

$clientRootPath = Resolve-Path -LiteralPath $ClientRoot
$clientRootFull = Get-FullPath $clientRootPath
$clientLeaf = Split-Path -Leaf $clientRootFull.TrimEnd("\")
if (-not $AllowOtherClient -and $clientLeaf -ne $expectedClient) {
    throw "The $Flavor payload requires a $expectedClient client root. Pass -AllowOtherClient to override."
}
if ($Prerelease -and ($Flavor -ne "forever" -or $clientLeaf -ne "_forever_")) {
    throw "The local prerelease option requires a Forever client."
}

$addonsRoot = Join-Path $clientRootFull "Interface\AddOns"
$targetRoot = Join-Path $addonsRoot $AddonName
Assert-SafeAddonTarget -TargetPath $targetRoot -AddonName $AddonName

if ($Flavor -eq "forever") {
    $pythonPath = $null
    $pythonCandidates = @((Join-Path $repoRoot "build\release-venv\Scripts\python.exe"))
    $pythonCandidates += @(Get-Command python -All -CommandType Application -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    foreach ($candidate in $pythonCandidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        try {
            & $candidate -B -c "import sys; raise SystemExit(sys.version_info < (3, 10))" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $pythonPath = $candidate
                break
            }
        } catch {
            continue
        }
    }
    if (-not $pythonPath) {
        throw "No Python 3.10+ environment was found for the Forever data checks."
    }
    $scoringArgs = @("scoring-audit", "--flavor", "forever", "--strict")
    if ($LuaPath) {
        $scoringArgs += @("--lua", $LuaPath)
    }
    $scoringOutput = & $pythonPath (Join-Path $repoRoot "tools\scrape_wowhead.py") @scoringArgs
    if ($LASTEXITCODE -ne 0) {
        $scoringOutput | Write-Host
        throw "Forever scoring needs all 56 verified talent-aware contexts before deployment."
    }
    $levelingOutput = & $pythonPath (Join-Path $repoRoot "tools\scrape_wowhead.py") coverage --flavor forever --family leveling --summary --strict
    $levelingExit = $LASTEXITCODE
    if ($levelingExit -ne 0) {
        if (-not $Prerelease -or $levelingExit -ne 1) {
            throw "Forever leveling coverage is incomplete; the installed addon has not been changed."
        }
        $leveling = ($levelingOutput -join "`n") | ConvertFrom-Json
        if ($leveling.ok -ne $false -or $null -eq $leveling.summary.uncovered_combinations -or
            $leveling.summary.uncovered_combinations -le 0 -or $leveling.summary.review_issues -ne 0 -or
            $leveling.summary.reviewed_rules -ne $true -or @($leveling.errors).Count -ne 0) {
            throw "Forever leveling has validation errors or stale reviews. Resolve them before deploying a prerelease."
        }
        Write-Warning "Local Forever prerelease with $($leveling.summary.uncovered_combinations) uncovered leveling combinations."
    }
    & $pythonPath (Join-Path $repoRoot "tools\scrape_wowhead.py") coverage --flavor forever --family bis_lists --summary --strict
    if ($LASTEXITCODE -ne 0) {
        throw "Forever pre-raid coverage is incomplete; the installed addon has not been changed."
    }
    & $pythonPath (Join-Path $repoRoot "tools\generate_lua.py") --flavor forever --check
    if ($LASTEXITCODE -ne 0) {
        throw "Forever bundled data is stale or invalid; the installed addon has not been changed."
    }
}

$tocEntries = [System.Collections.Generic.List[string]]::new()
$iconTexture = $null
foreach ($tocLine in Get-Content -LiteralPath $tocPath) {
    $line = $tocLine.Trim()
    if (-not $line) {
        continue
    }

    if ($line -match "^##\s*IconTexture\s*:\s*(.+)$") {
        $iconTexture = $Matches[1].Trim()
    }

    if (-not $line.StartsWith("#")) {
        [void]$tocEntries.Add($line)
    }
}

$deployEntries = [System.Collections.Generic.List[string]]::new()
[void]$deployEntries.Add($tocName)
foreach ($entry in $tocEntries) {
    if (-not $deployEntries.Contains($entry)) {
        [void]$deployEntries.Add($entry)
    }
}

if ($iconTexture) {
    $addonTexturePrefix = "Interface\AddOns\$AddonName\"
    if ($iconTexture.StartsWith($addonTexturePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $iconEntry = $iconTexture.Substring($addonTexturePrefix.Length)
        if ($iconEntry -and -not $deployEntries.Contains($iconEntry)) {
            [void]$deployEntries.Add($iconEntry)
        }
    }
}

# Runtime textures can be referenced from Lua without appearing in the TOC.
$assetsRoot = Join-Path $repoRoot "assets"
if (Test-Path -LiteralPath $assetsRoot -PathType Container) {
    foreach ($asset in Get-ChildItem -LiteralPath $assetsRoot -File -Recurse) {
        $entry = $asset.FullName.Substring($repoRoot.Path.Length + 1)
        if (-not $deployEntries.Contains($entry)) {
            [void]$deployEntries.Add($entry)
        }
    }
}

$luac = Get-Command luac -ErrorAction SilentlyContinue
if ($LuaPath -or $luac) {
    $luaFiles = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $deployEntries) {
        if ([System.IO.Path]::GetExtension($entry) -ieq ".lua") {
            [void]$luaFiles.Add((Join-Path $repoRoot $entry))
        }
    }
    if ($luaFiles.Count -gt 0) {
        if ($LuaPath) {
            $luaFiles | & $LuaPath -e 'for file in io.lines() do assert(loadfile(file)) end'
        } else {
            & $luac.Source -p @luaFiles
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Lua compile preflight failed; refusing to deploy."
        }
    }
} else {
    Write-Warning "luac not found; skipping Lua compile preflight."
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
        if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash) {
            throw "Verification failed for installed entry $entry."
        }
    }
    $copied += 1
}

$packageLabel = if ($Prerelease) { "Forever prerelease" } else { "$Flavor addon" }
Write-Host "Deployed $copied entries for the $packageLabel to $targetRoot"
