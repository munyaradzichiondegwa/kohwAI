$ErrorActionPreference = 'Stop'

$root = (Get-Location).Path
$relativeFiles = @(
    'backend\app\core\config.py',
    'backend\app\utils\sms.py',
    'backend\app\modules\identity\service.py'
)
foreach ($relative in $relativeFiles) {
    $full = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        throw "Cannot find $relative. Run this script from the KohwAI repository root."
    }
}

function Replace-ExactOnce {
    param(
        [string]$Text,
        [string]$OldText,
        [string]$NewText,
        [string]$Description
    )
    $first = $Text.IndexOf($OldText, [StringComparison]::Ordinal)
    if ($first -lt 0) { throw "Could not find the expected original code for: $Description. No files have been changed." }
    $second = $Text.IndexOf($OldText, $first + $OldText.Length, [StringComparison]::Ordinal)
    if ($second -ge 0) { throw "Found multiple matches for: $Description. No files have been changed." }
    return $Text.Remove($first, $OldText.Length).Insert($first, $NewText)
}

function Replace-RegexOnce {
    param(
        [string]$Text,
        [string]$Pattern,
        [string]$Replacement,
        [string]$Description
    )
    $matches = [regex]::Matches($Text, $Pattern)
    if ($matches.Count -ne 1) { throw "Expected exactly one match for: $Description; found $($matches.Count). No files have been changed." }
    $regex = [regex]::new($Pattern)
    return $regex.Replace($Text, [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $Replacement }, 1)
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$paths = @{}
$contents = @{}
foreach ($relative in $relativeFiles) {
    $full = Join-Path $root $relative
    $paths[$relative] = $full
    $contents[$relative] = [System.IO.File]::ReadAllText($full).Replace("`r`n", "`n")
}

# 1. Do not use the placeholder sender ID "123".
$configKey = 'backend\app\core\config.py'
$configReplacement = '    # Leave empty until Africa''s Talking approves a sender ID / shortcode.' + "`n" + '    AT_SHORTCODE: str = ""'
$contents[$configKey] = Replace-ExactOnce -Text $contents[$configKey] -OldText '    AT_SHORTCODE: str = "123"' -NewText $configReplacement -Description 'AT_SHORTCODE default'

# 2. Require both credentials, omit an unapproved sender ID, and log provider rejection details safely.
$smsKey = 'backend\app\utils\sms.py'
$contents[$smsKey] = Replace-ExactOnce $contents[$smsKey] '    return bool(settings.AT_API_KEY)' '    return bool(settings.AT_API_KEY.strip() and settings.AT_USERNAME.strip())' 'SMS gateway credential check'

$oldPost = @'
        resp = requests.post(
            AT_URL,
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"username": settings.AT_USERNAME, "to": ",".join(recipients), "message": message,
                  "from": settings.AT_SHORTCODE},
            timeout=20,
        )
'@.TrimEnd("`r", "`n")
$newPost = @'
        data = {
            "username": settings.AT_USERNAME.strip(),
            "to": ",".join(recipients),
            "message": message,
        }
        # Do not send the old placeholder "123" as a sender ID. Include
        # this field only after a real sender ID / shortcode is approved.
        sender = (settings.AT_SHORTCODE or "").strip()
        if sender:
            data["from"] = sender

        resp = requests.post(
            AT_URL,
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data=data,
            timeout=20,
        )
'@.TrimEnd("`r", "`n")
$contents[$smsKey] = Replace-ExactOnce $contents[$smsKey] $oldPost $newPost 'SMS request sender-ID handling'

$oldCatch = @'
    except Exception as e:  # noqa: BLE001
        logger.error("SMS gateway call failed: %s", e)
        return {r: SmsResult(False, "gateway_error") for r in recipients}
'@.TrimEnd("`r", "`n")
$newCatch = @'
    except requests.RequestException as e:
        response = getattr(e, "response", None)
        status_code = getattr(response, "status_code", None)
        provider_message = (getattr(response, "text", "") or "").strip()
        logger.error(
            "SMS gateway request failed (HTTP %s): %s",
            status_code if status_code is not None else "transport error",
            provider_message[:300] if provider_message else str(e),
        )
        return {r: SmsResult(False, "gateway_error") for r in recipients}
    except Exception:  # noqa: BLE001
        logger.exception("Unexpected error while processing SMS gateway response")
        return {r: SmsResult(False, "gateway_error") for r in recipients}
'@.TrimEnd("`r", "`n")
$contents[$smsKey] = Replace-ExactOnce $contents[$smsKey] $oldCatch $newCatch 'SMS provider error logging'

# 3. Do not return HTTP 200 when the provider rejected the OTP or no delivery route exists.
$serviceKey = 'backend\app\modules\identity\service.py'
$otpPattern = '(?ms)^    dev_otp = None\n    if settings\.AT_API_KEY:\n        send_sms\(\[phone\], f"Your KohwAI verification code is \{otp\}\. Valid for \{OTP_TTL_MINUTES\} minutes\."\)\n    elif settings\.ENVIRONMENT == "development" and settings\.EXPOSE_DEV_OTP:\n        # Explicit opt-in, development only\..*\n        # without an SMS gateway the code is simply not delivered\.\n        dev_otp = otp'
$newOtpBlock = @'
    dev_otp = None
    if settings.AT_API_KEY.strip() and settings.AT_USERNAME.strip():
        accepted = send_sms(
            [phone],
            f"Your KohwAI verification code is {otp}. Valid for {OTP_TTL_MINUTES} minutes.",
        )
        if not accepted:
            # Invalidate the stored code: the user was not given a usable OTP.
            otp_log.used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The SMS provider did not accept the verification message. Please try again later.",
            )
    elif settings.ENVIRONMENT == "development" and settings.EXPOSE_DEV_OTP:
        # Explicit opt-in, development only. Any other environment fails closed:
        # without an SMS gateway the code is simply not delivered.
        dev_otp = otp
    else:
        # Never report a successful OTP request when no delivery path exists.
        otp_log.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMS delivery is not configured. Please try again later.",
        )
'@.TrimEnd("`r", "`n")
$contents[$serviceKey] = Replace-RegexOnce $contents[$serviceKey] $otpPattern $newOtpBlock 'OTP SMS delivery handling'

# All expected source patterns were found. Create backups before writing any file.
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
foreach ($relative in $relativeFiles) {
    $full = $paths[$relative]
    $backup = "$full.before-sms-delivery-fix-$timestamp.bak"
    Copy-Item -LiteralPath $full -Destination $backup
}
foreach ($relative in $relativeFiles) {
    [System.IO.File]::WriteAllText($paths[$relative], $contents[$relative], $utf8NoBom)
}

Write-Host ''
Write-Host 'KohwAI SMS source corrections applied.' -ForegroundColor Green
Write-Host 'Backups created beside the three original files.'
Write-Host 'Changes:'
Write-Host ' - Requires both AT_API_KEY and AT_USERNAME.'
Write-Host ' - Does not send placeholder sender ID 123.'
Write-Host ' - Logs Africa''s Talking HTTP rejection details without logging the API key.'
Write-Host ' - Returns HTTP 502/503 instead of false OTP-request success when SMS cannot be accepted.'
Write-Host ''
Write-Host 'This script does not modify .env, Docker configuration, or any database.'
