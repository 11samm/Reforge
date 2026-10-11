Set-Location -LiteralPath 'D:\Samuel\Downloads\Code\ReforgerData\brightness-clean-start-verification'
& 'D:\Samuel\Downloads\Code\Reforge\.venv\Scripts\python.exe' -m learning.brightness --config brightness.config.json *> 'verification\live-console.log'
exit $LASTEXITCODE
