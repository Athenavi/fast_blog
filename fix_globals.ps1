$files = Get-ChildItem frontend-astro/src -Recurse -Filter "*.astro" -File -ErrorAction SilentlyContinue | Select-String -Pattern "/src/styles/globals" -SimpleMatch | Select-Object -ExpandProperty Path

foreach ($f in $files) {
    $content = [System.IO.File]::ReadAllText($f)
    $oldLink = '<link rel="stylesheet" href="/src/styles/globals.css"/>'
    $importLine = "import '@/styles/globals.css';"
    
    # Remove the hardcoded link line
    $newContent = $content -replace [regex]::Escape($oldLink), ''
    # Remove leftover blank lines (line with only whitespace)
    $newContent = $newContent -replace '^\s*\r?\n', ''
    
    # Add import to frontmatter - find the last import line before --- and add after it
    # Pattern: frontmatter ends with ---, find the last import line
    if ($newContent -match '^---') {
        $parts = $newContent -split '^---\r?\n', 3
        if ($parts.Count -ge 3) {
            $fm = $parts[1]
            $rest = $parts[2]
            # Check if import already exists
            if ($fm -notmatch [regex]::Escape($importLine)) {
                $fm = $fm.TrimEnd() + "`r`n" + $importLine + "`r`n"
                $newContent = '---' + "`r`n" + $fm + '---' + "`r`n" + $rest
            }
        }
    }
    
    [System.IO.File]::WriteAllText($f, $newContent, [System.Text.UTF8Encoding]::new($false))
}

Write-Host "Done processing $($files.Count) files"
