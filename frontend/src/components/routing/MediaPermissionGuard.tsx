/**
 * Guard de rota para verificar permissões da Media Library
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Lock, AlertCircle } from 'lucide-react';
import { useMediaPermissions } from '../../hooks/useMediaPermissions';
import { FullPageLoader } from '../common/FullPageLoader';

interface MediaPermissionGuardProps {
  children: React.ReactNode;
  requiredPermission?: 'upload' | 'createFolders' | 'manageTags' | 'shareFiles';
  allowViewerAccess?: boolean;
}

export const MediaPermissionGuard: React.FC<MediaPermissionGuardProps> = ({
  children,
  requiredPermission,
  allowViewerAccess = true
}) => {
  const location = useLocation();
  const { 
    canUpload, 
    canCreateFolders, 
    canManageTags, 
    canShareFiles,
    isViewer,
    isGuest,
    isLoading,
    role 
  } = useMediaPermissions();

  // Mostrar loading enquanto carrega as permissões
  if (isLoading) {
    return <FullPageLoader message="Verificando permissões..." />;
  }

  // Verificar se o usuário tem acesso básico à Media Library
  const hasBasicAccess = !isGuest || allowViewerAccess;

  if (!hasBasicAccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <Lock className="w-8 h-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Acesso Negado
          </h2>
          <p className="text-gray-600 mb-4">
            Você não tem permissão para acessar a Biblioteca de Mídia.
          </p>
          <p className="text-sm text-gray-500 mb-6">
            Perfil atual: <span className="font-medium">{role}</span>
          </p>
          <button
            onClick={() => window.history.back()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Voltar
          </button>
        </div>
      </div>
    );
  }

  // Verificar permissão específica se requerida
  if (requiredPermission) {
    let hasPermission = false;

    switch (requiredPermission) {
      case 'upload':
        hasPermission = canUpload;
        break;
      case 'createFolders':
        hasPermission = canCreateFolders;
        break;
      case 'manageTags':
        hasPermission = canManageTags;
        break;
      case 'shareFiles':
        hasPermission = canShareFiles;
        break;
    }

    if (!hasPermission) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-yellow-100 rounded-full flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-yellow-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Permissão Insuficiente
            </h2>
            <p className="text-gray-600 mb-4">
              Você não tem permissão para acessar esta funcionalidade.
            </p>
            <div className="text-sm text-gray-500 mb-6">
              <p>Perfil atual: <span className="font-medium">{role}</span></p>
              <p>Permissão necessária: <span className="font-medium">{getPermissionLabel(requiredPermission)}</span></p>
            </div>
            <div className="flex gap-2 justify-center">
              <button
                onClick={() => window.history.back()}
                className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                Voltar
              </button>
              <Navigate to="/media" replace state={{ from: location }} />
            </div>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
};

function getPermissionLabel(permission: string): string {
  const labels = {
    upload: 'Upload de arquivos',
    createFolders: 'Criação de pastas',
    manageTags: 'Gerenciamento de tags',
    shareFiles: 'Compartilhamento de arquivos'
  };
  return labels[permission as keyof typeof labels] || permission;
}