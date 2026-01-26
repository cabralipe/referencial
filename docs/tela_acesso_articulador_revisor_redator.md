# Estrutura da tela de acesso (articulador / revisor / redator)

## 1) Objetivo
Tela única de autenticação para três perfis (articulador, revisor e redator), com orientação clara do papel e acesso seguro.

## 2) Layout geral
- Coluna esquerda (informativa)
  - Logo / nome do produto
  - Tagline curta (ex.: "Ambiente de produção editorial")
  - Ilustração ou imagem temática (opcional)
  - Lista de benefícios curtos (3 itens)
- Coluna direita (formulário)
  - Título principal: "Acessar"
  - Subtítulo: "Entre com suas credenciais"
  - Formulário
  - Links de ajuda
  - Rodapé com versão / suporte

## 3) Elementos do formulário
- Campo: E-mail
  - Tipo: email
  - Placeholder: "nome@dominio.com"
  - Validação: formato de e-mail
- Campo: Senha
  - Tipo: password
  - Placeholder: "••••••••"
  - Ação: botão "Mostrar/ocultar senha"
- Seleção de perfil
  - Opção A: Articulador
  - Opção B: Revisor
  - Opção C: Redator
  - Comportamento: radio buttons ou dropdown
  - Texto de ajuda: "Selecione seu perfil para entrar"
- Checkbox: "Lembrar-me neste dispositivo" (opcional)
- Botão primário: "Entrar"
  - Estado carregando: spinner + "Entrando..."
  - Estado desabilitado: enquanto campos inválidos

## 4) Links e ações secundárias
- Link: "Esqueci minha senha"
- Link: "Primeiro acesso" (se aplicável)
- Link: "Suporte" ou "Fale conosco"

## 5) Mensagens de feedback
- Erro de credenciais
  - Texto: "E-mail ou senha inválidos. Tente novamente."
- Erro de perfil não autorizado
  - Texto: "Seu usuário não possui acesso ao perfil selecionado."
- Campo obrigatório
  - Texto: "Este campo é obrigatório."
- Estado offline/servidor
  - Texto: "Não foi possível conectar. Verifique sua internet."

## 6) Estados da tela
- Estado inicial (campos vazios)
- Estado preenchido (campos válidos)
- Estado de erro (mensagens inline + banner)
- Estado de carregamento (botão e bloqueio do formulário)

## 7) Requisitos de acessibilidade
- Labels visíveis para todos os campos
- Contraste mínimo AA
- Navegação por teclado
- Foco visível
- Mensagens de erro associadas ao campo

## 8) Texto sugerido (copy)
- Título: "Acessar"
- Subtítulo: "Entre com suas credenciais"
- Perfil: "Selecione seu perfil"
- Botão: "Entrar"
- Ajuda: "Esqueceu a senha?"

## 9) Metadados técnicos (opcional)
- Rota: /login
- Evento de analytics: login_attempt, login_success, login_failure
- Telemetria: tempo de resposta do auth

## 10) Itens fora do escopo
- Cadastro de novos usuários (se não houver fluxo)
- Gestão de permissões (feita no admin)

