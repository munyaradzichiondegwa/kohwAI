KohwAI SMS delivery source correction

1. Save kohwai-sms-delivery-fix.zip in your Downloads folder.
2. Open PowerShell in C:\Users\TechCharities\Desktop\kohwAI.
3. Extract the archive:
     Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\kohwai-sms-delivery-fix.zip" -DestinationPath . -Force
4. Run the script from the repository root:
     .\kohwai_sms_fix\Apply-KohwaiSmsFix.ps1

The script first verifies all expected original code snippets. It creates timestamped backups, then changes only:
  backend\app\core\config.py
  backend\app\utils\sms.py
  backend\app\modules\identity\service.py

It does not modify .env, Docker configuration, databases, or volumes.
