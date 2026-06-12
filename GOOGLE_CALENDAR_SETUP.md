# Guia de Configuração: Integração com o Google Calendar 📅

Este documento orienta sobre como configurar a integração entre o **DashFamília** e o **Google Calendar** utilizando o fluxo de **Conta de Serviço (Service Account)**. Este fluxo permite que o assistente de IA e o dashboard sincronizem compromissos localmente de forma segura, automática e sem necessidade de login manual do usuário pelo navegador a cada execução.

---

## Passo a Passo de Configuração

### Passo 1: Criar um Projeto no Google Cloud Console
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Clique na caixa de seleção de projetos no topo esquerdo e clique em **Novo Projeto**.
3. Dê um nome amigável ao projeto (ex: `Smart Family Dashboard`) e clique em **Criar**.

### Passo 2: Ativar a API do Google Calendar
1. No menu lateral esquerdo, vá em **APIs e Serviços** -> **Biblioteca**.
2. Digite **Google Calendar API** no campo de busca.
3. Clique no resultado correspondente e selecione **Ativar**.

### Passo 3: Criar uma Conta de Serviço
1. Vá em **APIs e Serviços** -> **Credenciais**.
2. No topo da tela, clique em **+ Criar Credenciais** e selecione **Conta de serviço**.
3. Preencha os detalhes (ex: Nome da conta: `calendar-sync-agent`).
4. Clique em **Criar e Continuar**.
5. Na etapa opcional de atribuição de papéis, pode clicar diretamente em **Concluído**.

### Passo 4: Baixar a Chave JSON (`credentials.json`)
1. Na lista de **Contas de Serviço** (na parte inferior da tela de Credenciais), clique no e-mail correspondente à conta criada.
2. Acesse a aba **Chaves** (Keys).
3. Clique em **Adicionar chave** -> **Criar nova chave**.
4. Selecione o tipo de chave **JSON** e clique em **Criar**.
5. Um arquivo `.json` será baixado no seu computador.
6. **Renomeie o arquivo para `credentials.json`** e coloque-o na raiz do seu projeto (`dashboard_familia/credentials.json`).
   > ⚠️ **Nota de Segurança:** Este arquivo contém chaves privadas. Ele já está configurado no `.gitignore` para nunca ser enviado ao GitHub. Nunca compartilhe este arquivo com ninguém.

### Passo 5: Compartilhar o Google Calendar Familiar com a Conta de Serviço
1. Abra o arquivo `credentials.json` que você baixou e copie o valor do campo `"client_email"` (ex: `calendar-sync-agent@seu-projeto-123.iam.gserviceaccount.com`).
2. Acesse o [Google Calendar](https://calendar.google.com/) da sua conta pessoal.
3. No menu lateral, passe o mouse sobre a agenda que deseja sincronizar (ex: "Família" ou sua agenda principal), clique nos três pontinhos e selecione **Configurações e compart. de agendas**.
4. Role até a seção **Compartilhar com pessoas ou grupos específicos** e clique em **Adicionar pessoas**.
5. Cole o e-mail da Conta de Serviço copiado no subpasso 1.
6. **Importante:** Altere a permissão para **"Fazer alterações em eventos"** (para que o aplicativo possa criar, editar e excluir compromissos).
7. Clique em **Enviar**.

### Passo 6: Configurar o ID da Agenda no arquivo `.env`
1. Na mesma tela de configurações do seu Google Calendar, role até a seção **Integrar agenda** e copie o **ID da agenda** (se for a sua agenda pessoal principal, será o seu próprio e-mail do Gmail, ex: `seu-nome@gmail.com`; se for uma agenda secundária, será algo como `hash@group.calendar.google.com`).
2. Abra o arquivo `.env` na raiz do seu projeto e defina a chave `GOOGLE_CALENDAR_ID` com o valor copiado:
   ```env
   GOOGLE_CALENDAR_ID=seu-id-de-agenda@gmail.com
   ```
3. Salve o arquivo `.env`.

---

## Recursos e Funcionamento

Com os passos acima concluídos, os seguintes recursos estarão funcionando:
* **Agendamento Inteligente via Chatbot**: Comandos de voz ou texto como *"marca no calendário que dia 24/06 às 17:00 tem festa junina na empresa do Cassi"* serão entendidos localmente pelo modelo de IA, cadastrados no banco de dados local SQLite e sincronizados com o Google Agenda em segundo plano.
* **Sincronização Bidirecional**: O botão **Sincronizar Google** na tela de Calendário no painel faz uma varredura completa:
  - Envia compromissos novos do painel para o Google Calendar.
  - Baixa novos compromissos e alterações feitas diretamente no Google Calendar (eventos baixados do Google aparecem em verde identificados como criados pelo usuário `Google`).
  - Limpa localmente compromissos que foram deletados no Google Calendar (numa janela de sincronização de -30 dias a +90 dias).

---

## Solução de Problemas (Troubleshooting)

### Erro 403: "Google Calendar API has not been used... or it is disabled"
* **Causa:** Você esqueceu de ativar a API do Google Calendar no projeto ou está utilizando o projeto do Google Cloud errado.
* **Solução:** O dashboard mostrará o link exato para ativação na tela em caso de falha. Clique no link, selecione o projeto correspondente no console e clique em **Ativar**. Aguarde 2 minutos e tente sincronizar novamente.

### Erro: "credentials.json não encontrado"
* **Causa:** O arquivo de credenciais da conta de serviço não está na raiz do projeto ou está com o nome incorreto.
* **Solução:** Verifique se o arquivo está na pasta raiz e se o nome está exatamente como `credentials.json` (tudo em minúsculas).
