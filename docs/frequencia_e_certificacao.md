# Frequência e certificação dos cursos AVA

No cadastro do curso, configure progresso mínimo, nota mínima e frequência mínima (padrão: 75%). A frequência é calculada pela proporção de encontros realizados em que o cursista esteve presente; não é o percentual de visualização de conteúdo. Zero dispensa o critério de frequência, por exemplo em cursos inteiramente assíncronos. Se a frequência mínima for maior que zero e não houver encontros realizados, a certificação fica bloqueada.

Em **Frequência**, selecione o curso e crie uma aula/reunião. O responsável pode editar o título e a data, marcar os presentes na lista de matriculados e salvar a chamada. Somente encontros marcados como realizados entram no cálculo; encontros previstos não entram. Falta de registro de presença em um encontro realizado equivale a ausência. A lista mostra matrículas ativas ou concluídas e usuários ativos. A frequência considera todos os encontros realizados do curso, inclusive quando a matrícula foi feita depois deles.

Para reuniões on-line, abra o link de presença e informe uma validade futura. Compartilhe o endereço exibido na chamada durante a reunião. O cursista precisa entrar na própria conta, estar matriculado no curso e confirmar por botão; abrir a página não registra presença. Repetir a confirmação não duplica a presença. Feche o link após a reunião ou aguarde o vencimento. O checklist permite corrigir a frequência. Operações de confirmação e chamada ficam no histórico de auditoria.

Administradores do município e responsáveis do curso (autor, gestor ou tutor autorizado) têm acesso à chamada, respeitando os municípios disponíveis para o usuário.

A emissão em lote exibe os motivos das pendências e emite somente para matrículas concluídas que atendam aos critérios de progresso, nota e frequência e cujo curso permita certificação. A antiga opção de aprovar pendentes foi removida. A opção legada `aprovar_pendente` do serviço não dispensa mais os critérios. O download pelo cursista também verifica a elegibilidade atual; certificados antigos não são apagados.

Aplicação: execute `python manage.py migrate` antes de publicar o código. A migração não emite certificados nem altera presenças existentes no Diário de Bordo ou nas salas de GT. Os encontros de cursos possuem controle próprio para não somar registros de outros fluxos à certificação.
