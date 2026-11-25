"""Estrutura do Anexo I do PDF indicado. Os textos de produção começam vazios.

Fonte: https://deg.unb.br/wp-content/uploads/plano_nacional_educacao_2026_2036.pdf
Conferido em 25/11/2026, páginas 5–18. Não inclui o Anexo II.
Cada categoria tem um objetivo; as metas conservam as letras da fonte.
"""

FONTE_PNE = "https://deg.unb.br/wp-content/uploads/plano_nacional_educacao_2026_2036.pdf"

CATEGORIAS_PNE = (
    ("Acesso à Educação Infantil", 3),
    ("Qualidade da Educação Infantil", 2),
    ("Alfabetização", 3),
    ("Acesso, Trajetória e Conclusão no Ensino Fundamental e no Ensino Médio", 4),
    ("Aprendizagem no Ensino Fundamental e no Ensino Médio", 6),
    ("Educação Integral em Tempo Integral", 1),
    ("Conectividade, educação digital e integração das Tecnologias Digitais de Informação e Comunicação (TDICs) à educação", 2),
    ("Sustentabilidade Socioambiental na Educação", 3),
    ("Educação Escolar Indígena, Educação do Campo e Educação Escolar Quilombola", 7),
    ("Educação Especial Inclusiva e Educação Bilíngue de Surdos", 4),
    ("Educação de Jovens, Adultos e Idosos", 5),
    ("Acesso, permanência e conclusão na Educação Profissional e Tecnológica", 6),
    ("Qualidade da Educação Profissional e Tecnológica", 3),
    ("Acesso, Permanência e Conclusão na Graduação", 4),
    ("Qualidade da Graduação", 4),
    ("Pós-Graduação stricto sensu", 1),
    ("Formação e Valorização dos Profissionais da Educação Básica", 6),
    ("Participação e Controle Social e Gestão Democrática na Educação Pública", 3),
    ("Financiamento e Infraestrutura da Educação", 6),
)

# Quantidade de estratégias por categoria, na ordem do Anexo I.
# Conserva a numeração nacional: 1.1 a 1.13, 2.1 a 2.24 etc.
ESTRATEGIAS_PNE = (13, 24, 16, 16, 26, 15, 20, 25, 24, 31, 25, 15, 14, 18, 16, 14, 28, 12, 20)
