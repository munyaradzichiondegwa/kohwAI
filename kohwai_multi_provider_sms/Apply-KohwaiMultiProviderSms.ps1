$ErrorActionPreference = 'Stop'

$repoRoot = (Get-Location).Path
$servicePath = Join-Path $repoRoot 'backend\app\modules\identity\service.py'
$smsPath = Join-Path $repoRoot 'backend\app\utils\sms.py'
$providerTarget = Join-Path $repoRoot 'backend\app\utils\sms_providers'
$payloadRoot = Join-Path $PSScriptRoot 'payload\backend\app\utils'
$payloadSms = Join-Path $payloadRoot 'sms.py'
$payloadProviders = Join-Path $payloadRoot 'sms_providers'

foreach ($path in @($servicePath, $smsPath, $payloadSms, $payloadProviders)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required file or folder not found: $path. No changes have been made."
    }
}
if (Test-Path -LiteralPath $providerTarget) {
    throw "The target folder already exists: $providerTarget. Review it manually; this installer will not overwrite an existing provider implementation."
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$serviceText = [System.IO.File]::ReadAllText($servicePath)
$smsText = [System.IO.File]::ReadAllText($smsPath)

# The existing compatibility module must expose the current single-provider API.
if ($smsText -notmatch 'def\s+send_sms_detailed\s*\(' -or $smsText -notmatch 'def\s+send_sms\s*\(') {
    throw 'The existing sms.py does not match the expected KohwAI interface. No changes have been made.'
}

$oldImport = 'from app.utils.sms import send_sms'
$newImport = 'from app.utils.sms import gateway_configured, send_sms_detailed'
if ($serviceText.Contains($oldImport)) {
    $serviceText = $serviceText.Replace($oldImport, $newImport)
} elseif (-not $serviceText.Contains($newImport)) {
    throw 'Could not identify the expected SMS import in identity/service.py. No changes have been made.'
}

$otpPattern = '(?ms)^    dev_otp = None\r?\n.*?^    return \{"phone": phone, "expires_in_seconds": OTP_TTL_MINUTES \* 60, "dev_otp": dev_otp\}\s*$'
$otpMatches = [regex]::Matches($serviceText, $otpPattern)
if ($otpMatches.Count -ne 1) {
    throw "Expected exactly one original OTP delivery block in identity/service.py; found $($otpMatches.Count). No changes have been made."
}
$newOtpBlock = @'
    delivery_status = "not_configured"
    dev_otp = None

    if gateway_configured():
        delivery = send_sms_detailed(
            [phone],
            f"Your KohwAI verification code is {otp}. Valid for {OTP_TTL_MINUTES} minutes.",
        ).get(phone)
        if delivery and delivery.ok:
            # Provider acceptance is not the same as confirmed handset delivery.
            delivery_status = "accepted"
        elif delivery and delivery.uncertain:
            # Keep this OTP valid. The provider may have accepted the send before
            # a timeout/5xx occurred; automatically failing over could duplicate it.
            delivery_status = "unknown"
        else:
            otp_log.used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The SMS providers did not accept the verification message. Please try again later.",
            )
    elif settings.ENVIRONMENT == "development" and settings.EXPOSE_DEV_OTP:
        # Explicit opt-in for local development only.
        dev_otp = otp
        delivery_status = "development"
    else:
        otp_log.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMS delivery is not configured. Please try again later.",
        )

    return {
        "phone": phone,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "dev_otp": dev_otp,
        "delivery_status": delivery_status,
    }
'@
$otpRegex = [regex]::new($otpPattern)
$serviceText = $otpRegex.Replace($serviceText, $newOtpBlock.TrimEnd("`r", "`n"), 1)

# All checks are complete. Back up the only two files that will be replaced/edited.
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Copy-Item -LiteralPath $smsPath -Destination "$smsPath.before-multiprovider-$timestamp.bak"
Copy-Item -LiteralPath $servicePath -Destination "$servicePath.before-multiprovider-$timestamp.bak"

New-Item -ItemType Directory -Path $providerTarget | Out-Null
Copy-Item -Path (Join-Path $payloadProviders '*') -Destination $providerTarget -Recurse -Force
Copy-Item -LiteralPath $payloadSms -Destination $smsPath -Force
[System.IO.File]::WriteAllText($servicePath, $serviceText, $utf8NoBom)

Write-Host ''
Write-Host 'KohwAI multi-provider SMS framework installed.' -ForegroundColor Green
Write-Host 'Backups created for sms.py and identity/service.py.'
Write-Host 'Installed providers: SMSPoP, Infobip, Econet A2P adapter slot, optional legacy Africa''s Talking.'
Write-Host 'Econet A2P remains intentionally disabled until its official API contract is received.'
Write-Host 'No .env file, Docker configuration, database, or volume was changed.'
Write-Host ''
