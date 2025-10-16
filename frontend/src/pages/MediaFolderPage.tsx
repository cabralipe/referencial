/**
 * Página de visualização de pasta específica
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Home, ChevronRight, Upload } from 'lucide-react';
import { MediaLibrary } from '../components/media/MediaLibrary';
import { useMediaFolders } from '../hooks/useMediaLibrary';
import type { MediaFolder } from '../types/media';

export const MediaFolderPage: React.FC = () => {
  const { folderId } = useParams<{ folderId: string }>();
  const navigate = useNavigate();
  const { folders } = useMediaFolders();
  const [currentFolder, setCurrentFolder] = useState<MediaFolder | null>(null);

  useEffect(() => {
    if (folderId && folders.length > 0) {
      const folder = folders.find(f => f.id === folderId);
      setCurrentFolder(folder || null);
    }
  }, [folderId, folders]);

  // Gerar breadcrumbs
  const getBreadcrumbs = (): MediaFolder[] => {
    if (!currentFolder) return [];
    
    const breadcrumbs: MediaFolder[] = [];
    let folder: MediaFolder | null = currentFolder;
    
    while (folder) {
      breadcrumbs.unshift(folder);
      folder = folder.parent_folder ? folders.find(f => f.id === folder.parent_folder) || null : null;
    }
    
    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  if (!currentFolder) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Pasta não encontrada</h2>
          <button
            onClick={() => navigate('/media')}
            className="text-blue-600 hover:text-blue-800"
          >
            Voltar para biblioteca
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header com breadcrumbs */}
        <div className="mb-8">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-4">
            <button
              onClick={() => navigate('/media')}
              className="flex items-center gap-1 hover:text-gray-900"
            >
              <Home className="w-4 h-4" />
              Biblioteca
            </button>
            
            {breadcrumbs.map((folder, index) => (
              <React.Fragment key={folder.id}>
                <ChevronRight className="w-4 h-4" />
                <button
                  onClick={() => navigate(`/media/folder/${folder.id}`)}
                  className={`hover:text-gray-900 ${
                    index === breadcrumbs.length - 1 ? 'font-medium text-gray-900' : ''
                  }`}
                >
                  {folder.name}
                </button>
              </React.Fragment>
            ))}
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {currentFolder.name}
              </h1>
              {currentFolder.description && (
                <p className="mt-2 text-gray-600">
                  {currentFolder.description}
                </p>
              )}
            </div>
            
            <button
              onClick={() => navigate('/media/upload')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Upload className="w-4 h-4" />
              Upload
            </button>
          </div>
        </div>
        
        {/* Biblioteca de mídia filtrada por pasta */}
        <MediaLibrary 
          initialFilters={{ folder: currentFolder.id }}
          showFolderFilter={false}
        />
      </div>
    </div>
  );
};