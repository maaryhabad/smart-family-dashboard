@echo off
echo Iniciando o Servidor de Dashboard...

:: 1. Inicia o Ollama (o processo do Ollama costuma rodar em background, mas garantimos aqui)
start "Ollama" ollama serve

:: 2. Inicia o n8n
start "n8n" n8n start

:: 3. Dá um tempo para os serviços subirem (5 segundos)
timeout /t 5

:: 4. Roda a sua aplicação Flask (no terminal atual)
echo Rodando a aplicacao Python...
"C:/Users/Mariana Abad/.venv_dashboard/Scripts/python.exe" e:/dashboard_familia/app.py

pause