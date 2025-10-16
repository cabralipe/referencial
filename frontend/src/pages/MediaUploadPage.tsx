/**
 * Página de upload de arquivos
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, FolderPlus } from 'lucide-react';
import { FileUploadModal } from '../components/media/FileUploadModal';
import { CreateFolderModal } from '../components/media/CreateFolderModal';

export const MediaUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [showUploadModal, setShowUploadModal] = useState(true);
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);

  const handleUploadComplete = () => {
    setShowUploadModal(false);
    navigate('/media');
  };

  const handleUploadCancel = () => {
    setShowUploadModal(false);
    navigate('/media');
  };

  const handleCreateFolderComplete = () => {
    setShowCreateFolderModal(false);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/media')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar para biblioteca
          </button>
          
          <h1 className="text-3xl font-bold text-gray-900">
            Upload de Arquivos
          </h1>
          <p className="mt-2 text-gray-600">
            Faça upload de novos arquivos para sua biblioteca de mídia
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div 
            className="p-6 bg-white rounded-lg shadow-sm border border-gray-200 cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => setShowUploadModal(true)}
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <Upload className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Fazer Upload
                </h3>
                <p className="text-sm text-gray-500">
                  Adicione novos arquivos à biblioteca
                </p>
              </div>
            </div>
          </div>

          <div 
            className="p-6 bg-white rounded-lg shadow-sm border border-gray-200 cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => setShowCreateFolderModal(true)}
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <FolderPlus className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Criar Pasta
                </h3>
                <p className="text-sm text-gray-500">
                  Organize seus arquivos em pastas
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Upload Tips */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Dicas de Upload
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Formatos Suportados</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Imagens: JPG, PNG, GIF, SVG, WebP</li>
                <li>• Vídeos: MP4, WebM, AVI, MOV</li>
                <li>• Documentos: PDF, DOC, DOCX, XLS, XLSX</li>
                <li>• Outros: ZIP, RAR, TXT, CSV</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Limites</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Tamanho máximo por arquivo: 100MB</li>
                <li>• Até 10 arquivos por upload</li>
                <li>• Nomes de arquivo até 255 caracteres</li>
                <li>• Caracteres especiais são permitidos</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      <FileUploadModal
        isOpen={showUploadModal}
        onClose={handleUploadCancel}
        onComplete={handleUploadComplete}
      />

      <CreateFolderModal
        isOpen={showCreateFolderModal}
        onClose={handleCreateFolderComplete}
        onComplete={handleCreateFolderComplete}
      />
    </div>
  );
};