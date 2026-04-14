import { Navigate, createBrowserRouter } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/routing/ProtectedRoute';
import { RoleRoute } from './components/routing/RoleRoute';
import { DashboardPage } from './pages/DashboardPage';
import { InicioPage } from './pages/InicioPage';
import { LoginPage } from './pages/LoginPage';
import { CadastroPage } from './pages/CadastroPage';
import { MinhaTrilhaPage } from './pages/MinhaTrilhaPage';
import { TaskDetailPage } from './pages/TaskDetailPage';
import { TasksPage } from './pages/TasksPage';
import { TrilhaDetailPage } from './pages/TrilhaDetailPage';
import { TextoUnicoPage } from './pages/TextoUnicoPage';
import { TextoEditorPage } from './pages/TextoEditorPage';
import { QuadrosPage } from './pages/QuadrosPage';
import { FormulariosPage } from './pages/FormulariosPage';
import { RevisoesPage } from './pages/RevisoesPage';
import { PareceresPage } from './pages/PareceresPage';
import { ComentariosPage } from './pages/ComentariosPage';
import { NotificacoesPage } from './pages/NotificacoesPage';
import { BibliotecaPage } from './pages/BibliotecaPage';
import { CadernosPage } from './pages/CadernosPage';
import { CadernoDetailPage } from './pages/CadernoDetailPage';
import { MuralPage } from './pages/MuralPage';
import { AjudaPage } from './pages/AjudaPage';
import { PppPage } from './pages/PppPage';
import { PppDetailPage } from './pages/PppDetailPage';
import { AdminMuralPage } from './pages/AdminMuralPage';
import { AdminPppPage } from './pages/AdminPppPage';
import { AdminTrilhasPage } from './pages/AdminTrilhasPage';
import { AdminConsolePage } from './pages/AdminConsolePage';
import { AdminModulePage } from './pages/AdminModulePage';
import { RedatorInboxPage } from './pages/RedatorInboxPage';
import { RedatorReviewDetailPage } from './pages/RedatorReviewDetailPage';
import { RedatorConteudosPage } from './pages/RedatorConteudosPage';
import { RedatorMuralPage } from './pages/RedatorMuralPage';
import { ExportacoesPage } from './pages/ExportacoesPage';
import { DiffPage } from './pages/DiffPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { ReportsPage } from './pages/ReportsPage';
import { ConsultasPublicasPage } from './pages/ConsultasPublicasPage';
import { ConsultaPublicaPublicPage } from './pages/ConsultaPublicaPublicPage';
import { ScoreConfigPage } from './pages/ScoreConfigPage';
import { ThrottleBlocksPage } from './pages/ThrottleBlocksPage';
import { PlanoEditorPage } from './pages/PlanoEditorPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'dashboard',
        element: <Navigate to="/" replace />,
      },
      {
        path: 'cursos',
        element: <Navigate to="/" replace />,
      },
      {
        path: 'cursos/:id',
        element: <Navigate to="/" replace />,
      },
      {
        path: 'cursos/:id/modulo/:moduloId',
        element: <Navigate to="/" replace />,
      },
      {
        path: 'plano/:id/editar',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <PlanoEditorPage />
          </RoleRoute>
        ),
      },
      {
        path: 'inicio',
        element: (
          <RoleRoute allowed={['membro_gt']}>
            <InicioPage />
          </RoleRoute>
        ),
      },
      {
        path: 'minha-trilha',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <MinhaTrilhaPage />
          </RoleRoute>
        ),
      },
      {
        path: 'minha-trilha/:trilhaId',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <TrilhaDetailPage />
          </RoleRoute>
        ),
      },
      {
        path: 'texto',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <TextoEditorPage />
          </RoleRoute>
        ),
      },
      {
        path: 'texto/:id',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <TextoEditorPage />
          </RoleRoute>
        ),
      },
      {
        path: 'cadernos',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <CadernosPage />
          </RoleRoute>
        ),
      },
      {
        path: 'cadernos/:id',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <CadernoDetailPage />
          </RoleRoute>
        ),
      },
      {
        path: 'mural',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <MuralPage />
          </RoleRoute>
        ),
      },
      {
        path: 'ajuda',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <AjudaPage />
          </RoleRoute>
        ),
      },
      {
        path: 'ppp',
        element: (
          <RoleRoute allowed={['diretor', 'coordenador_pedagogico', 'professor', 'articulador', 'admin_cliente', 'super_admin']}>
            <PppPage />
          </RoleRoute>
        ),
      },
      {
        path: 'ppp/:id',
        element: (
          <RoleRoute allowed={['diretor', 'coordenador_pedagogico', 'professor', 'articulador', 'admin_cliente', 'super_admin']}>
            <PppDetailPage />
          </RoleRoute>
        ),
      },
      {
        path: 'tarefas',
        children: [
          {
            index: true,
            element: (
              <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
                <TasksPage />
              </RoleRoute>
            ),
          },
          {
            path: ':tarefaId',
            element: (
              <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
                <TaskDetailPage />
              </RoleRoute>
            ),
          },
        ],
      },
      {
        path: 'texto-unico',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <TextoUnicoPage />
          </RoleRoute>
        ),
      },
      {
        path: 'quadros',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <QuadrosPage />
          </RoleRoute>
        ),
      },
      {
        path: 'formularios',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <FormulariosPage />
          </RoleRoute>
        ),
      },
      {
        path: 'revisoes',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <RevisoesPage />
          </RoleRoute>
        ),
      },
      {
        path: 'pareceres',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <PareceresPage />
          </RoleRoute>
        ),
      },
      {
        path: 'comentarios',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <ComentariosPage />
          </RoleRoute>
        ),
      },
      {
        path: 'notificacoes',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <NotificacoesPage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/cursos',
        element: <Navigate to="/admin/console" replace />,
      },
      {
        path: 'admin/cursos/:id/banco-planos',
        element: <Navigate to="/admin/console" replace />,
      },
      {
        path: 'admin/mural',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <AdminMuralPage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/console',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <AdminConsolePage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/console/:moduleId',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <AdminModulePage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/trilhas',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <AdminTrilhasPage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/ppp',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <AdminPppPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/painel',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <DashboardPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/revisoes',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <RedatorInboxPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/conteudos',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <RedatorConteudosPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/mural',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <RedatorMuralPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/exportacoes',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <ExportacoesPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/revisoes/:alvoTipo/:alvoId',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <RedatorReviewDetailPage />
          </RoleRoute>
        ),
      },
      {
        path: 'redator/fila',
        element: <Navigate to="/redator/revisoes" replace />,
      },
      {
        path: 'redator/diff',
        element: <Navigate to="/redator/revisoes?tab=diff" replace />,
      },
      {
        path: 'redator/comentarios',
        element: <Navigate to="/redator/revisoes?tab=comentarios" replace />,
      },
      {
        path: 'redator/pareceres',
        element: <Navigate to="/redator/revisoes?tab=parecer" replace />,
      },
      {
        path: 'redator/referencias',
        element: <Navigate to="/redator/revisoes?tab=referencias" replace />,
      },
      {
        path: 'biblioteca',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <BibliotecaPage />
          </RoleRoute>
        ),
      },
      {
        path: 'banco',
        element: <Navigate to="/" replace />,
      },
      {
        path: 'documentos/ppp',
        element: (
          <RoleRoute allowed={['diretor', 'coordenador_pedagogico', 'professor', 'articulador', 'admin_cliente', 'super_admin']}>
            <PppPage />
          </RoleRoute>
        ),
      },
      {
        path: 'documentos/referencial',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <MinhaTrilhaPage />
          </RoleRoute>
        ),
      },
      {
        path: 'analytics',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <ReportsPage />
          </RoleRoute>
        ),
      },
      {
        path: 'consultas-publicas',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <ConsultasPublicasPage />
          </RoleRoute>
        ),
      },
      {
        path: 'exportacoes',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <ExportacoesPage />
          </RoleRoute>
        ),
      },
      {
        path: 'diff',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <DiffPage />
          </RoleRoute>
        ),
      },
      {
        path: 'auditoria',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <AuditLogsPage />
          </RoleRoute>
        ),
      },
      {
        path: 'relatorios',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <ReportsPage />
          </RoleRoute>
        ),
      },
      {
        path: 'admin/producao-redatores',
        element: <Navigate to="/relatorios" replace />,
      },
      {
        path: 'gamificacao',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <ScoreConfigPage />
          </RoleRoute>
        ),
      },
      {
        path: 'bloqueios',
        element: (
          <RoleRoute allowed={['admin_cliente', 'super_admin']}>
            <ThrottleBlocksPage />
          </RoleRoute>
        ),
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/cadastro',
    element: <CadastroPage />,
  },
  {
    path: '/consultas-publicas/:token',
    element: <ConsultaPublicaPublicPage />,
  },
]);
