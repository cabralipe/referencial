import { createBrowserRouter } from 'react-router-dom';

import { AppLayout } from './components/layout/AppLayout';
import { ProtectedRoute } from './components/routing/ProtectedRoute';
import { MediaPermissionGuard } from './components/routing/MediaPermissionGuard';
import { DashboardPage } from './pages/DashboardPage';
import { LoginPage } from './pages/LoginPage';
import { TaskDetailPage } from './pages/TaskDetailPage';
import { TextoUnicoPage } from './pages/TextoUnicoPage';
import { QuadroPage } from './pages/QuadroPage';
import { ReviewsPage } from './pages/ReviewsPage';
import { ReviewDetailPage } from './pages/ReviewDetailPage';
import { MediaLibraryPage } from './pages/MediaLibraryPage';
import { MediaUploadPage } from './pages/MediaUploadPage';
import { MediaFolderPage } from './pages/MediaFolderPage';
import { WebSocketTestPage } from './pages/WebSocketTestPage';

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
        path: 'tarefas/:tarefaId',
        element: <TaskDetailPage />,
      },
      {
        path: 'textos-unicos/:tarefaId',
        element: <TextoUnicoPage />,
      },
      {
        path: 'quadros/:tarefaId',
        element: <QuadroPage />,
      },
      {
        path: 'reviews',
        element: <ReviewsPage />,
      },
      {
        path: 'reviews/:id',
        element: <ReviewDetailPage />,
      },
      {
        path: 'media',
        element: (
          <MediaPermissionGuard allowViewerAccess={true}>
            <MediaLibraryPage />
          </MediaPermissionGuard>
        ),
      },
      {
        path: 'media/upload',
        element: (
          <MediaPermissionGuard requiredPermission="upload" allowViewerAccess={false}>
            <MediaUploadPage />
          </MediaPermissionGuard>
        ),
      },
      {
        path: 'media/folder/:folderId',
        element: (
          <MediaPermissionGuard allowViewerAccess={true}>
            <MediaFolderPage />
          </MediaPermissionGuard>
        ),
      },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/test-websocket',
    element: <WebSocketTestPage />,
  },
]);
