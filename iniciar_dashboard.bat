@echo off
:: Suporte a caminhos UNC (mapeia temporariamente caminhos de rede para uma letra de unidade caso executado de um compartilhamento)
pushd %~dp0

echo Iniciando o Servidor de Dashboard...

:: 1. Inicia o Ollama (o processo do Ollama costuma rodar em background, mas garantimos aqui)
echo Iniciando Ollama...
start "Ollama" ollama serve

:: 2. Inicia o n8n (caso esteja instalado local ou globalmente)
if exist "node_modules\.bin\n8n.cmd" (
    echo Iniciando n8n local do projeto...
    start "n8n" npx n8n start
) else (
    where n8n >nul 2>&1
    if %errorlevel% equ 0 (
        echo Iniciando n8n global...
        start "n8n" n8n start
    ) else (
        echo [AVISO] n8n nao encontrado (nem local no node_modules, nem global). Pulando inicializacao do n8n...
        echo Para usar o n8n local, instale o Node.js e depois execute: npm install n8n
    )
)

:: 3. Dá um tempo para os serviços subirem (5 segundos)
timeout /t 5

:: 4. Roda a sua aplicação Flask (usando caminhos relativos ao ambiente virtual local)
echo Rodando a aplicacao Python...

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" app.py
) else (
    python app.py
)

:: Remove o mapeamento temporário de caminho UNC
popd
pause