#Requires -Version 7.0

<#
.SYNOPSIS
Runs the non-destructive Big BiS List release gate.

.DESCRIPTION
Validates release metadata, the Python and Lua 5.1 toolchain, tests, generated
data, canonical data, and scrape coverage from the repository root. Pass
-FullData for the snapshot, requirements, item-corpus, suffix, and
recommendation audits required before publishing a release.

.PARAMETER Version
The plain numeric release version, for example 0.12.0.

.PARAMETER PythonPath
Optional Python executable path or command name. The interpreter must be
Python 3.10 or newer and have the dependencies declared in pyproject.toml.

.PARAMETER FullData
Runs every committed-snapshot and generated-recommendation audit. This switch
is required by the release process before tagging.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')]
    [string]$Version,

    [string]$PythonPath,

    [switch]$FullData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-ExecutablePath {
    param(
        [Parameter(Mandatory = $true)][string]$Candidate
    )

    if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
        return [System.IO.Path]::GetFullPath($Candidate)
    }

    $command = Get-Command $Candidate -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($command) {
        return $command.Source
    }

    return $null
}

function Get-ReleasePython {
    param(
        [string]$RequestedPath
    )

    $candidates = if ($RequestedPath) {
        @($RequestedPath)
    } else {
        @("python", "python3", "py")
    }

    foreach ($candidate in $candidates) {
        $executable = Get-ExecutablePath -Candidate $candidate
        if (-not $executable) {
            continue
        }

        $versionText = & $executable -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Python: $executable ($versionText)"
            return $executable
        }
    }

    if ($RequestedPath) {
        throw "PythonPath '$RequestedPath' is unavailable or is older than Python 3.10."
    }
    throw "Python 3.10 or newer was not found. Pass -PythonPath with the release environment's Python executable."
}

function Get-LuaTool {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string[]]$CommandNames,
        [Parameter(Mandatory = $true)][string[]]$KnownPaths,
        [Parameter(Mandatory = $true)][string[]]$ProbeArguments,
        [Parameter(Mandatory = $true)][string]$ExpectedPattern
    )

    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($name in $CommandNames) {
        $path = Get-ExecutablePath -Candidate $name
        if ($path -and -not $candidates.Contains($path)) {
            [void]$candidates.Add($path)
        }
    }
    foreach ($knownPath in $KnownPaths) {
        $path = Get-ExecutablePath -Candidate $knownPath
        if ($path -and -not $candidates.Contains($path)) {
            [void]$candidates.Add($path)
        }
    }

    foreach ($candidate in $candidates) {
        $probeOutput = & $candidate @ProbeArguments 2>&1
        $probeText = ($probeOutput | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $probeText -match $ExpectedPattern) {
            Write-Host "${Label}: $candidate"
            return $candidate
        }
    }

    throw "$Label for Lua 5.1 was not found. Install Lua 5.1 and ensure its runtime and compiler are available on PATH."
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "`n== $Label =="
    & $Executable @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Label failed with exit code $exitCode."
    }
}

function Get-DeclaredPythonRequirements {
    param(
        [Parameter(Mandatory = $true)][string]$PyprojectPath
    )

    $pyproject = Get-Content -Raw -LiteralPath $PyprojectPath
    $dependencyBlock = [regex]::Match(
        $pyproject,
        '(?ms)^\s*dependencies\s*=\s*\[(?<body>.*?)^\s*\]'
    )
    if (-not $dependencyBlock.Success) {
        throw "Could not read [project].dependencies from $PyprojectPath."
    }

    $requirements = [System.Collections.Generic.List[string]]::new()
    foreach ($match in [regex]::Matches($dependencyBlock.Groups['body'].Value, '"(?<requirement>[^"]+)"')) {
        [void]$requirements.Add($match.Groups['requirement'].Value)
    }
    return $requirements.ToArray()
}

function Test-PythonEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExecutable,
        [Parameter(Mandatory = $true)][string]$PyprojectPath
    )

    $requirements = @(Get-DeclaredPythonRequirements -PyprojectPath $PyprojectPath)
    if ($requirements.Count -gt 0) {
        $dependencyProbe = @'
import importlib.metadata as metadata
import sys

try:
    from packaging.requirements import Requirement
except ImportError:
    from pip._vendor.packaging.requirements import Requirement

problems = []
for requirement_text in sys.argv[1:]:
    requirement = Requirement(requirement_text)
    if requirement.marker and not requirement.marker.evaluate():
        continue
    try:
        installed = metadata.version(requirement.name)
    except metadata.PackageNotFoundError:
        problems.append(f"{requirement.name} is not installed")
        continue
    if requirement.specifier and not requirement.specifier.contains(installed, prereleases=True):
        problems.append(f"{requirement.name} {installed} does not satisfy {requirement.specifier}")
    else:
        print(f"{requirement.name}=={installed}")

if problems:
    print("Declared Python dependency preflight failed:", file=sys.stderr)
    for problem in problems:
        print(f"- {problem}", file=sys.stderr)
    raise SystemExit(1)
'@
        Invoke-CheckedCommand -Label "Declared Python dependency preflight" -Executable $PythonExecutable -Arguments (@("-c", $dependencyProbe) + $requirements)
    }

    Invoke-CheckedCommand -Label "Python dependency consistency" -Executable $PythonExecutable -Arguments @("-m", "pip", "check")
}

function Assert-GitReleaseState {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseVersion
    )

    $git = Get-ExecutablePath -Candidate "git"
    if (-not $git) {
        throw "Git was not found on PATH."
    }

    $insideWorkTree = & $git rev-parse --is-inside-work-tree
    if ($LASTEXITCODE -ne 0 -or $insideWorkTree.Trim() -ne "true") {
        throw "The release gate must run inside a Git worktree."
    }

    $statusLines = @(& $git status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect Git worktree state."
    }
    if ($statusLines.Count -gt 0) {
        $details = $statusLines -join [Environment]::NewLine
        throw "The release commit must have a clean worktree before running the gate:`n$details"
    }

    $prefixedTag = @(& $git tag --list "v$ReleaseVersion")
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect Git tags."
    }
    if ($prefixedTag.Count -gt 0) {
        throw "Invalid prefixed release tag found: v$ReleaseVersion. Release tags must be plain numeric versions."
    }

    $existingTag = @(& $git tag --list $ReleaseVersion)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect Git tags."
    }
    if ($existingTag.Count -gt 0) {
        $tagCommit = (& $git rev-list -n 1 $ReleaseVersion).Trim()
        $headCommit = (& $git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $tagCommit -ne $headCommit) {
            throw "Release tag $ReleaseVersion already exists on a different commit."
        }
        Write-Host "Release tag $ReleaseVersion already points at HEAD; validating the tagged commit."
    }
}

function Assert-VersionMetadata {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseVersion,
        [Parameter(Mandatory = $true)][string]$RepositoryRoot
    )

    $config = Get-Content -Raw -LiteralPath (Join-Path $RepositoryRoot "Config.lua")
    $configMatch = [regex]::Match($config, '(?m)^\s*version\s*=\s*"(?<version>\d+\.\d+\.\d+)"\s*$')
    if (-not $configMatch.Success -or $configMatch.Groups['version'].Value -ne $ReleaseVersion) {
        throw "Config.lua fallback version must be $ReleaseVersion."
    }

    $readme = Get-Content -Raw -LiteralPath (Join-Path $RepositoryRoot "README.md")
    $readmeVersions = @(
        @(
            [regex]::Matches($readme, '`(?<version>\d+\.\d+\.\d+)`')
            [regex]::Matches($readme, '(?m)-Version\s+(?<version>\d+\.\d+\.\d+)')
        ) |
            ForEach-Object { $_.Groups['version'].Value } |
            Sort-Object -Unique
    )
    if ($readmeVersions.Count -eq 0 -or $readmeVersions.Count -ne 1 -or $readmeVersions[0] -ne $ReleaseVersion) {
        $found = if ($readmeVersions.Count -gt 0) { $readmeVersions -join ", " } else { "none" }
        throw "README.md release references must consistently use $ReleaseVersion (found: $found)."
    }

    $toc = Get-Content -Raw -LiteralPath (Join-Path $RepositoryRoot "BigBiSList.toc")
    if ($toc -notmatch '(?m)^##\s+Version:\s+@project-version@\s*$') {
        throw "BigBiSList.toc must keep ## Version: @project-version@ for tag packaging."
    }
}

function Assert-ReadmeDataCounts {
    param(
        [Parameter(Mandatory = $true)][object]$ValidationPayload,
        [Parameter(Mandatory = $true)][string]$ReadmePath
    )

    if (-not $ValidationPayload.ok) {
        throw "Canonical validation did not report an ok result."
    }

    $readme = Get-Content -Raw -LiteralPath $ReadmePath
    $countLabels = [ordered]@{
        classes = "classes"
        specs = "specs"
        phases = "phases"
        bis_lists = "BiS slot lists"
        items = "item records"
        item_stats = "item stat records"
        gems = "gem rows"
        enchants = "enchant rows"
        consumables = "consumable rows"
        leveling = "leveling rows"
        leveling_gear = "guide-backed leveling gear rows"
        leveling_recommendations = "computed leveling recommendations"
    }

    $errors = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $countLabels.GetEnumerator()) {
        $property = $ValidationPayload.summary.PSObject.Properties[$entry.Key]
        if (-not $property) {
            [void]$errors.Add("validator summary is missing '$($entry.Key)'")
            continue
        }

        $labelPattern = [regex]::Escape($entry.Value)
        $readmeMatch = [regex]::Match($readme, "(?m)^-\s+(?<count>[\d,]+)\s+$labelPattern\s*$")
        if (-not $readmeMatch.Success) {
            [void]$errors.Add("README is missing the '$($entry.Value)' count")
            continue
        }

        $publishedCount = [int64]::Parse($readmeMatch.Groups['count'].Value.Replace(",", ""))
        $canonicalCount = [int64]$property.Value
        if ($publishedCount -ne $canonicalCount) {
            [void]$errors.Add("$($entry.Value): README has $publishedCount, canonical data has $canonicalCount")
        }
    }

    if ($errors.Count -gt 0) {
        throw "README data counts do not match tools/validate_data.py --json:`n- $($errors -join "`n- ")"
    }
    Write-Host "README data counts match canonical validation."
}

function Invoke-CanonicalValidation {
    param(
        [Parameter(Mandatory = $true)][string]$PythonExecutable,
        [Parameter(Mandatory = $true)][string]$RepositoryRoot
    )

    Write-Host "`n== Canonical data validation =="
    $jsonText = & $PythonExecutable "tools/validate_data.py" "--json" | Out-String
    $exitCode = $LASTEXITCODE
    Write-Host $jsonText.TrimEnd()
    if ($exitCode -ne 0) {
        throw "Canonical data validation failed with exit code $exitCode."
    }

    try {
        $payload = $jsonText | ConvertFrom-Json
    } catch {
        throw "Canonical validation did not return valid JSON: $($_.Exception.Message)"
    }
    Assert-ReadmeDataCounts -ValidationPayload $payload -ReadmePath (Join-Path $RepositoryRoot "README.md")
}

function Invoke-LuaCompile {
    param(
        [Parameter(Mandatory = $true)][string]$LuaCompiler,
        [Parameter(Mandatory = $true)][string]$RepositoryRoot
    )

    $tocPath = Join-Path $RepositoryRoot "BigBiSList.toc"
    $luaFiles = [System.Collections.Generic.List[string]]::new()
    foreach ($tocLine in Get-Content -LiteralPath $tocPath) {
        $entry = $tocLine.Trim()
        if (-not $entry -or $entry.StartsWith("#") -or [System.IO.Path]::GetExtension($entry) -ine ".lua") {
            continue
        }
        $luaPath = Join-Path $RepositoryRoot $entry
        if (-not (Test-Path -LiteralPath $luaPath -PathType Leaf)) {
            throw "TOC Lua entry does not exist: $entry"
        }
        [void]$luaFiles.Add($luaPath)
    }
    if ($luaFiles.Count -eq 0) {
        throw "BigBiSList.toc contains no Lua files to compile."
    }

    Invoke-CheckedCommand -Label "Lua 5.1 compilation" -Executable $LuaCompiler -Arguments (@("-p") + $luaFiles.ToArray())
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$originalPath = $env:PATH
Push-Location -LiteralPath $repoRoot
try {
    Write-Host "Big BiS List release gate for $Version"
    Write-Host "Repository: $repoRoot"

    $python = Get-ReleasePython -RequestedPath $PythonPath
    $luaRuntime = Get-LuaTool `
        -Label "Lua runtime" `
        -CommandNames @("lua", "lua5.1", "lua51") `
        -KnownPaths @("C:\Program Files (x86)\Lua\5.1\lua.exe", "C:\Program Files\Lua\5.1\lua.exe") `
        -ProbeArguments @("-e", "io.write(_VERSION)") `
        -ExpectedPattern '^Lua 5\.1$'
    $luaCompiler = Get-LuaTool `
        -Label "Lua compiler" `
        -CommandNames @("luac", "luac5.1", "luac51") `
        -KnownPaths @("C:\Program Files (x86)\Lua\5.1\luac.exe", "C:\Program Files\Lua\5.1\luac.exe") `
        -ProbeArguments @("-v") `
        -ExpectedPattern '\bLua 5\.1\b'

    $toolDirectories = @((Split-Path -Parent $luaRuntime), (Split-Path -Parent $luaCompiler)) | Sort-Object -Unique
    $env:PATH = (($toolDirectories + @($env:PATH)) -join [System.IO.Path]::PathSeparator)

    Test-PythonEnvironment -PythonExecutable $python -PyprojectPath (Join-Path $repoRoot "pyproject.toml")
    Assert-GitReleaseState -ReleaseVersion $Version
    Assert-VersionMetadata -ReleaseVersion $Version -RepositoryRoot $repoRoot
    Invoke-CheckedCommand -Label "Changelog history and generated release notes" -Executable $python -Arguments @("tools/generate_release_notes.py", "--version", $Version, "--check")

    Invoke-CheckedCommand -Label "Unit tests" -Executable $python -Arguments @("-m", "unittest", "discover", "-s", "tests")
    Invoke-LuaCompile -LuaCompiler $luaCompiler -RepositoryRoot $repoRoot
    Invoke-CanonicalValidation -PythonExecutable $python -RepositoryRoot $repoRoot
    Invoke-CheckedCommand -Label "Generated Lua consistency" -Executable $python -Arguments @("tools/generate_lua.py", "--check")
    Invoke-CheckedCommand -Label "Canonical scrape audit" -Executable $python -Arguments @("tools/scrape_wowhead.py", "audit")
    Invoke-CheckedCommand -Label "Strict manifest coverage" -Executable $python -Arguments @("tools/scrape_wowhead.py", "coverage", "--summary", "--strict")

    if ($FullData) {
        Invoke-CheckedCommand -Label "Item corpus audit" -Executable $python -Arguments @("tools/scrape_wowhead.py", "item-corpus-audit")
        Invoke-CheckedCommand -Label "Random suffix audit" -Executable $python -Arguments @("tools/scrape_wowhead.py", "suffix-audit")
        Invoke-CheckedCommand -Label "Leveling recommendation audit" -Executable $python -Arguments @("tools/scrape_wowhead.py", "recommendation-audit")

        $dataFamilies = @(
            @{ Name = "bis_lists"; InputDirectory = "data/raw/wowhead/full_bis" },
            @{ Name = "gems"; InputDirectory = "data/raw/wowhead/full_gems" },
            @{ Name = "enchants"; InputDirectory = "data/raw/wowhead/full_enchants" },
            @{ Name = "consumables"; InputDirectory = "data/raw/wowhead/full_consumables" },
            @{ Name = "leveling"; InputDirectory = "data/raw/wowhead/full_leveling" }
        )
        foreach ($family in $dataFamilies) {
            Invoke-CheckedCommand `
                -Label "$($family.Name) snapshot audit" `
                -Executable $python `
                -Arguments @("tools/scrape_wowhead.py", "snapshot-audit", "--input-dir", $family.InputDirectory, "--family", $family.Name)
            Invoke-CheckedCommand `
                -Label "$($family.Name) requirements audit" `
                -Executable $python `
                -Arguments @("tools/scrape_wowhead.py", "requirements-audit", "--input-dir", $family.InputDirectory, "--family", $family.Name)
        }
    } else {
        Write-Warning "Full-data audits were skipped. This run is not sufficient for a release; record the reason for any intentional skip."
    }

    Write-Host "`nRelease gate passed for $Version$(if ($FullData) { ' with full-data audits' } else { '' })."
} finally {
    $env:PATH = $originalPath
    Pop-Location
}
