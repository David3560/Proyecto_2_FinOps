@echo off
setlocal
pushd "%~dp0" || exit /b 1
set "PYTHONUTF8=1"
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
  set "INTERPRETE=py -3"
) else (
  python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
  if errorlevel 1 goto :sinpython
  set "INTERPRETE=python"
)
%INTERPRETE% -m unittest discover -s tests -v
if errorlevel 1 goto :error
%INTERPRETE% -m finops %*
if errorlevel 1 goto :error
popd
exit /b 0

:sinpython
echo Se requiere Python 3.10 o posterior.
:error
popd
exit /b 1
