# 钢铁前线 · Netlify 一键部署脚本
# 用法 (先跑一次 netlify login 授权):
#   powershell -ExecutionPolicy Bypass -File web_deploy.ps1
$ErrorActionPreference = "Stop"
$Root = "C:\Users\Lenovo\Desktop\tank game"
$SiteName = "lanm-tank-game"
$BuildDir = Join-Path $Root "web_app\build\web"

Set-Location $Root
if (-not (Test-Path $BuildDir)) {
    Write-Host "[!] 找不到网页构建产物: $BuildDir" -ForegroundColor Red
    Write-Host "    先运行: cd web_app; python -m pygbag --build --disable-sound-format-error main.py (记得 PYTHONUTF8=1)"
    exit 1
}

# 复用已有站点, 没有则创建
$site = netlify sites:list --json | ConvertFrom-Json |
    Where-Object { $_.name -eq $SiteName } | Select-Object -First 1
if (-not $site) {
    Write-Host "[i] 首次部署: 创建站点 $SiteName ..."
    $created = netlify sites:create --name $SiteName --json | ConvertFrom-Json
    $siteId = $created.id
    Write-Host "[i] 站点已创建: $($created.ssl_url)"
} else {
    $siteId = $site.id
    Write-Host "[i] 复用已有站点: $($site.ssl_url)"
}

Write-Host "[i] 上传 build/web → 生产环境 ..."
netlify deploy --dir $BuildDir --prod --site $siteId
Write-Host "[OK] 完成! 打开 $site.ssl_url 即可游玩" -ForegroundColor Green
