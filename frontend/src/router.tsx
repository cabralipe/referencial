import { createBrowserRouter } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/routing/ProtectedRoute';
import { RoleRoute } from './components/routing/RoleRoute';
import { DashboardPage } from './pages/DashboardPage';
import { InicioPage } from './pages/InicioPage';
import { LoginPage } from './pages/LoginPage';
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
import { ExportacoesPage } from './pages/ExportacoesPage';
import { DiffPage } from './pages/DiffPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { ReportsPage } from './pages/ReportsPage';
import { ConsultasPublicasPage } from './pages/ConsultasPublicasPage';
import { ConsultaPublicaPublicPage } from './pages/ConsultaPublicaPublicPage';
import { ScoreConfigPage } from './pages/ScoreConfigPage';
import { ThrottleBlocksPage } from './pages/ThrottleBlocksPage';

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
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
            <PppPage />
          </RoleRoute>
        ),
      },
      {
        path: 'ppp/:id',
        element: (
          <RoleRoute allowed={['membro_gt', 'articulador', 'admin_cliente', 'super_admin']}>
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
        path: 'redator/revisoes',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <RedatorInboxPage />
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
        path: 'biblioteca',
        element: (
          <RoleRoute allowed={['articulador', 'admin_cliente', 'super_admin']}>
            <BibliotecaPage />
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
    path: '/consultas-publicas/:token',
    element: <ConsultaPublicaPublicPage />,
  },
]);
