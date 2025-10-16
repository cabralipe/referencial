/**
 * Página principal da biblioteca de mídia
 */

import React from 'react';
import { MediaLibrary } from '../components/media/MediaLibrary';

export const MediaLibraryPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            Biblioteca de Mídia
          </h1>
          <p className="mt-2 text-gray-600">
            Gerencie seus arquivos, organize em pastas e compartilhe com sua equipe
          </p>
        </div>
        
        <MediaLibrary />
      </div>
    </div>
  );
};