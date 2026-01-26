# Relatório — Admin Console Didático

## O que foi feito
- Admin Console ganhou camada pedagógica: atalhos, checklist de configuração mínima e ajuda rápida.
- Catálogo de módulos foi enriquecido com nomes humanos, exemplos, tags e dificuldade.
- CRUD ganhou **Modo simples (padrão)** e **Modo avançado** com JSON.
- Filtros rápidos aplicados em módulos críticos.
- Sidebar ajustada por perfil e header exibindo cliente selecionado para superadmin.

## Arquivos principais alterados
- `frontend/src/pages/AdminConsolePage.tsx`
- `frontend/src/pages/AdminConsolePage.css`
- `frontend/src/pages/AdminModulePage.tsx`
- `frontend/src/pages/AdminModulePage.css`
- `frontend/src/pages/adminModules.ts`
- `frontend/src/components/layout/AppLayout.tsx`
- `frontend/src/components/layout/AppLayout.css`
- `docs/admin_didatico.md`

## Observações
- Rotas existentes foram preservadas.
- CRUD genérico foi mantido, apenas com camada didática.
- Sem mudanças de backend nesta etapa.
