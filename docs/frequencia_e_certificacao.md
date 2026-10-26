# Frequência e certificação dos cursos AVA

No cadastro do curso, configure progresso mínimo, nota mínima e frequência mínima (padrão: 75%). A frequência é calculada pela proporção de encontros realizados em que o cursista esteve presente; não é o percentual de visualização de conteúdo. Zero dispensa o critério de frequência, por exemplo em cursos inteiramente assíncronos. Se a frequência mínima for maior que zero e não houver encontros realizados, a certificação fica bloqueada.

Em **Frequência**, selecione o curso e crie uma aula/reunião. O responsável pode editar o título e a data, marcar os presentes na lista de matriculados e salvar a chamada. Somente encontros marcados como realizados entram no cálculo; encontros previstos não entram. Falta de registro de presença em um encontro realizado equivale a ausência. A lista mostra matrículas ativas ou concluídas e usuários ativos. A frequência considera todos os encontros realizados do curso, inclusive quando a matrícula foi feita depois deles.

Para reuniões on-line, abra o link de presença e informe uma validade futura. Compartilhe o endereço exibido na chamada durante a reunião. O cursista precisa entrar na própria conta, estar matriculado no curso e confirmar por botão; abrir a página não registra presença. Repetir a confirmação não duplica a presença. Feche o link após a reunião ou aguarde o vencimento. O checklist permite corrigir a frequência. Operações de confirmação e chamada ficam no histórico de auditoria.

Administradores do município e responsáveis do curso (autor, gestor ou tutor autorizado) têm acesso à chamada, respeitando os municípios disponíveis para o usuário.

A emissão em lote exibe os motivos das pendências e emite somente para matrículas concluídas que atendam aos critérios de progresso, nota e frequência e cujo curso permita certificação. A antiga opção de aprovar pendentes foi removida. A opção legada `aprovar_pendente` do serviço não dispensa mais os critérios. O download pelo cursista também verifica a elegibilidade atual; certificados antigos não são apagados.

## Liberação dos certificados para o cursista

A emissão prepara o certificado e enfileira a geração do PDF; a liberação é um passo separado que decide quando o cursista enxerga o arquivo. Um certificado só aparece no painel do cursista quando tem PDF gerado e a data de liberação já passou. Enquanto isso, o cursista vê no curso concluído o aviso "Certificado aguardando liberação".

Em **Certificados**, a listagem mostra a situação de cada registro (não liberado, programado ou liberado) e se o PDF já existe, com filtros por situação e por disponibilidade de PDF. Há três caminhos para liberar:

- **Um por um**: botão *Liberar* na linha do certificado, que abre a tela de confirmação com a opção de liberar na hora ou programar a data.
- **Selecionados**: marque as linhas e use a ação *Liberar certificados selecionados para os cursistas* (imediata) ou *Programar liberação dos selecionados* (escolhe a data).
- **Todos de uma vez**: link *Liberar todos para os cursistas* no topo da listagem, que abrange todos os certificados visíveis para o usuário, respeitando o escopo do município.

Somente certificados com PDF são liberados. Os que ainda não têm PDF são contados na mensagem de retorno e reenviados para a fila de geração — repita a liberação quando o worker terminar. A liberação usa atualização em massa no banco, então "liberar todos" não carrega os registros na memória do processo web.

A revogação (*Revogar* na linha ou a ação *Revogar liberação dos selecionados*) apenas oculta o certificado: o PDF e o código de validação são preservados e a liberação pode ser refeita. O download continua verificando a elegibilidade atual do cursista, portanto uma matrícula que deixe de cumprir os critérios perde o acesso mesmo com o certificado liberado.

Aplicação: execute `python manage.py migrate` antes de publicar o código. A migração não emite certificados nem altera presenças existentes no Diário de Bordo ou nas salas de GT. Os encontros de cursos possuem controle próprio para não somar registros de outros fluxos à certificação.
