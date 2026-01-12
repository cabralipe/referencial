import { createBrowserRouter } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/routing/ProtectedRoute';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { TaskDetailPage } from './pages/TaskDetailPage';
import { TasksPage } from './pages/TasksPage';
import { TextoUnicoPage } from './pages/TextoUnicoPage';
import { QuadrosPage } from './pages/QuadrosPage';
import { FormulariosPage } from './pages/FormulariosPage';
import { RevisoesPage } from './pages/RevisoesPage';
import { PareceresPage } from './pages/PareceresPage';
import { ComentariosPage } from './pages/ComentariosPage';
import { NotificacoesPage } from './pages/NotificacoesPage';
import { BibliotecaPage } from './pages/BibliotecaPage';
import { ExportacoesPage } from './pages/ExportacoesPage';
import { DiffPage } from './pages/DiffPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { ReportsPage } from './pages/ReportsPage';
import { ConsultasPublicasPage } from './pages/ConsultasPublicasPage';
import { ConsultaPublicaPublicPage } from './pages/ConsultaPublicaPublicPage';
import { ScoreConfigPage } from './pages/ScoreConfigPage';

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
        path: 'tarefas',
        children: [
          {
            index: true,
            element: <TasksPage />,
          },
          {
            path: ':tarefaId',
            element: <TaskDetailPage />,
          },
        ],
      },
      {
        path: 'texto-unico',
        element: <TextoUnicoPage />,
      },
      {
        path: 'quadros',
        element: <QuadrosPage />,
      },
      {
        path: 'formularios',
        element: <FormulariosPage />,
      },
      {
        path: 'revisoes',
        element: <RevisoesPage />,
      },
      {
        path: 'pareceres',
        element: <PareceresPage />,
      },
      {
        path: 'comentarios',
        element: <ComentariosPage />,
      },
      {
        path: 'notificacoes',
        element: <NotificacoesPage />,
      },
      {
        path: 'biblioteca',
        element: <BibliotecaPage />,
      },
      {
        path: 'consultas-publicas',
        element: <ConsultasPublicasPage />,
      },
      {
        path: 'exportacoes',
        element: <ExportacoesPage />,
      },
      {
        path: 'diff',
        element: <DiffPage />,
      },
      {
        path: 'auditoria',
        element: <AuditLogsPage />,
      },
      {
        path: 'relatorios',
        element: <ReportsPage />,
      },
      {
        path: 'gamificacao',
        element: <ScoreConfigPage />,
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
