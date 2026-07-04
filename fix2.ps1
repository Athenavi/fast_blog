# Simple script: add import line to frontmatter of each astro file
$files = Get-ChildItem frontend-astro/src/pages -Recurse -Filter "*.astro" -File -ErrorAction SilentlyContinue

$importLine = "import '@/styles/globals.css';"
$count = 0

foreach ($f in $files) {
    $content = [System.IO.File]::ReadAllText($f.FullName)
    
    # Skip files that already have the import
    if ($content -match [regex]::Escape($importLine)) {
        continue
    }
    
    # Check if file has a frontmatter (starts with ---)
    if ($content -match '^---\r?\n') {
        # Find the closing --- of the frontmatter
        $lines = $content -split '\r?\n'
        $inFrontmatter = $false
        $newLines = @()
        foreach ($line in $lines) {
            if ($line -eq '---') {
                if (-not $inFrontmatter) {
                    $inFrontmatter = $true
                    $newLines += $line
                } else {
                    # Closing ---, add import before it
                    $newLines += $importLine
                    $newLines += $line
                    $inFrontmatter = $false
                }
            } else {
                $newLines += $line
            }
        }
        [System.IO.File]::WriteAllText($f.FullName, ($newLines -join "`r`n"), [System.Text.UTF8Encoding]::new($false))
        $count++
    }
}

Write-Host "Added import to $count files"
