param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$node = 'C:\Users\25113\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$artifact = Join-Path $root 'formal_artifacts\system_visualization'
$raw = Join-Path $artifact 'raw'
$logs = Join-Path $artifact 'logs'
$runStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$edgeProfileRoot = Join-Path $artifact ("edge-profile-$runStamp")

foreach ($required in $python, $node, $edge) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required executable not found: $required"
    }
}

New-Item -ItemType Directory -Force -Path $raw, $logs, $edgeProfileRoot | Out-Null

function Wait-Endpoint {
    param([string]$Uri)
    for ($attempt = 1; $attempt -le 40; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri $Uri
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "Service did not become ready: $Uri"
}

function Seed-ReviewDemo {
    param([string]$BaseUri)

    $recognitionResults = @(
        [ordered]@{
            enterprise_id = 'DEMO-001'
            enterprise_name = '演示样本—综合赛事运营企业'
            credit_code = 'DEMO-CREDIT-001'
            sport_score = 0.51
            sport_category = '体育赛事'
            code_type = 'non_sport_code'
            evidence_relation = 'text_code_conflict'
            confidence = 0.48
            is_sport = $true
            is_crossover = $true
            keywords = @('赛事运营', '场馆服务')
            total_business_lines = 4
            sport_business_lines = 2
        },
        [ordered]@{
            enterprise_id = 'DEMO-002'
            enterprise_name = '演示样本—跨界健身服务企业'
            credit_code = 'DEMO-CREDIT-002'
            sport_score = 0.68
            sport_category = '健身休闲'
            code_type = 'non_sport_code'
            evidence_relation = 'text_supports_sport'
            confidence = 0.63
            is_sport = $true
            is_crossover = $true
            keywords = @('健身服务')
            total_business_lines = 5
            sport_business_lines = 1
        },
        [ordered]@{
            enterprise_id = 'DEMO-003'
            enterprise_name = '演示样本—体育用品制造企业'
            credit_code = 'DEMO-CREDIT-003'
            sport_score = 0.91
            sport_category = '体育用品'
            code_type = 'sport_code'
            evidence_relation = 'text_code_consistent'
            confidence = 0.92
            is_sport = $true
            is_crossover = $false
            keywords = @('体育用品', '运动器材')
            total_business_lines = 3
            sport_business_lines = 3
        },
        [ordered]@{
            enterprise_id = 'DEMO-004'
            enterprise_name = '演示样本—文旅融合运营企业'
            credit_code = 'DEMO-CREDIT-004'
            sport_score = 0.57
            sport_category = '健身休闲'
            code_type = 'non_sport_code'
            evidence_relation = 'ambiguous'
            confidence = 0.52
            is_sport = $true
            is_crossover = $true
            keywords = @('户外运动', '旅游服务')
            total_business_lines = 6
            sport_business_lines = 2
        }
    )

    $generateBody = [ordered]@{
        batch_id = 20260809
        recognition_results = $recognitionResults
    } | ConvertTo-Json -Depth 8

    $generated = Invoke-RestMethod -Method Post -Uri "$BaseUri/api/review/tasks/generate" `
        -ContentType 'application/json; charset=utf-8' -Body $generateBody
    if ($generated.code -ne 200 -or $generated.data.tasks.Count -lt 4) {
        throw 'Failed to seed review demo tasks.'
    }

    $tasks = $generated.data.tasks
    foreach ($index in 1..3) {
        $taskId = $tasks[$index].id
        $assignBody = [ordered]@{
            task_ids = @($taskId)
            reviewer_a = '演示复核员A'
            reviewer_b = '演示复核员B'
        } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$BaseUri/api/review/tasks/$taskId/assign" `
            -ContentType 'application/json; charset=utf-8' -Body $assignBody | Out-Null
    }

    $confirmedId = $tasks[2].id
    foreach ($role in 'A', 'B') {
        $recordBody = [ordered]@{
            review_task_id = $confirmedId
            reviewer_name = "演示复核员$role"
            reviewer_role = $role
            sport_attribute = 'yes'
            sport_category_override = '体育用品'
            sport_share_override = 0.82
            reason = '演示流程：文本与代码证据一致。'
        } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$BaseUri/api/review/records" `
            -ContentType 'application/json; charset=utf-8' -Body $recordBody | Out-Null
    }

    $disputedId = $tasks[3].id
    $disputedRecords = @(
        [ordered]@{ reviewer_role = 'A'; sport_attribute = 'yes'; sport_category_override = '健身休闲'; sport_share_override = 0.55 },
        [ordered]@{ reviewer_role = 'B'; sport_attribute = 'uncertain'; sport_category_override = '体育旅游'; sport_share_override = 0.35 }
    )
    foreach ($record in $disputedRecords) {
        $recordBody = [ordered]@{
            review_task_id = $disputedId
            reviewer_name = "演示复核员$($record.reviewer_role)"
            reviewer_role = $record.reviewer_role
            sport_attribute = $record.sport_attribute
            sport_category_override = $record.sport_category_override
            sport_share_override = $record.sport_share_override
            reason = '演示流程：双人意见存在差异，进入仲裁。'
        } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$BaseUri/api/review/records" `
            -ContentType 'application/json; charset=utf-8' -Body $recordBody | Out-Null
    }
}

$backend = $null
$frontend = $null
try {
    $backend = Start-Process `
        -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', $BackendPort `
        -WorkingDirectory (Join-Path $root 'backend') `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "backend-$runStamp.out.log") `
        -RedirectStandardError (Join-Path $logs "backend-$runStamp.err.log") `
        -PassThru

    $frontend = Start-Process `
        -FilePath $node `
        -ArgumentList (Join-Path $root 'frontend\node_modules\vite\bin\vite.js'), '--host', '127.0.0.1', '--port', $FrontendPort `
        -WorkingDirectory (Join-Path $root 'frontend') `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "frontend-$runStamp.out.log") `
        -RedirectStandardError (Join-Path $logs "frontend-$runStamp.err.log") `
        -PassThru

    Wait-Endpoint -Uri "http://127.0.0.1:$BackendPort/"
    Wait-Endpoint -Uri "http://127.0.0.1:$FrontendPort/monitoring"
    Seed-ReviewDemo -BaseUri "http://127.0.0.1:$BackendPort"

    $manifestPath = Join-Path $PSScriptRoot 'route_manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $captures = @()
    foreach ($item in $manifest) {
        $target = Join-Path $raw ($item.id + '.png')
        $url = "http://127.0.0.1:$FrontendPort$($item.route)"
        $edgeProfile = Join-Path $edgeProfileRoot $item.id
        New-Item -ItemType Directory -Force -Path $edgeProfile | Out-Null
        $edgeArgs = @(
            '--headless=new',
            '--disable-gpu',
            '--hide-scrollbars',
            '--no-first-run',
            '--force-device-scale-factor=1',
            '--window-size=1920,1080',
            '--virtual-time-budget=12000',
            "--user-data-dir=$edgeProfile",
            "--screenshot=$target",
            $url
        )
        & $edge @edgeArgs | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Edge capture failed for $url with exit code $LASTEXITCODE"
        }
        $file = Get-Item -LiteralPath $target
        if ($file.Length -lt 10000) {
            throw "Screenshot is unexpectedly small: $target"
        }
        $captures += [ordered]@{
            id = $item.id
            route = $item.route
            title = $item.title
            focus = $item.focus
            url = $url
            path = $file.FullName
            bytes = $file.Length
        }
    }

    $metadata = [ordered]@{
        captured_at = (Get-Date).ToString('o')
        commit = (git -C $root rev-parse HEAD).Trim()
        viewport = '1920x1080'
        backend_url = "http://127.0.0.1:$BackendPort"
        frontend_url = "http://127.0.0.1:$FrontendPort"
        captures = $captures
    }
    $metadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $artifact 'capture_metadata.json') -Encoding UTF8
}
finally {
    if ($frontend -and -not $frontend.HasExited) {
        Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}

