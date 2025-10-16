/**
 * Utilitários para manipulação de arquivos de mídia
 */

import { 
  FileText, 
  Image, 
  Video, 
  Music, 
  Archive, 
  File,
  FileSpreadsheet,
  FileCode
} from 'lucide-react';

/**
 * Formata o tamanho do arquivo em formato legível
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Formata uma data em formato legível
 */
export function formatDate(date: string | Date): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  return new Intl.DateTimeFormat('pt-BR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(dateObj);
}

/**
 * Retorna o ícone apropriado para o tipo de arquivo
 */
export function getFileIcon(mimeType: string) {
  if (mimeType.startsWith('image/')) {
    return Image;
  }
  
  if (mimeType.startsWith('video/')) {
    return Video;
  }
  
  if (mimeType.startsWith('audio/')) {
    return Music;
  }
  
  if (mimeType === 'application/pdf') {
    return FileText;
  }
  
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) {
    return FileSpreadsheet;
  }
  
  if (mimeType.includes('text/') || mimeType.includes('json') || mimeType.includes('xml')) {
    return FileText;
  }
  
  if (mimeType.includes('javascript') || mimeType.includes('typescript') || 
      mimeType.includes('html') || mimeType.includes('css')) {
    return FileCode;
  }
  
  if (mimeType.includes('zip') || mimeType.includes('rar') || 
      mimeType.includes('tar') || mimeType.includes('gzip')) {
    return Archive;
  }
  
  return File;
}

/**
 * Verifica se o arquivo é uma imagem
 */
export function isImageFile(mimeType: string): boolean {
  return mimeType.startsWith('image/');
}

/**
 * Verifica se o arquivo é um vídeo
 */
export function isVideoFile(mimeType: string): boolean {
  return mimeType.startsWith('video/');
}

/**
 * Verifica se o arquivo é um áudio
 */
export function isAudioFile(mimeType: string): boolean {
  return mimeType.startsWith('audio/');
}

/**
 * Gera uma URL de preview para o arquivo
 */
export function getFilePreviewUrl(file: File): string | null {
  if (isImageFile(file.type) || isVideoFile(file.type)) {
    return URL.createObjectURL(file);
  }
  return null;
}

/**
 * Valida se o arquivo é permitido
 */
export function validateFile(file: File, maxSize: number = 50 * 1024 * 1024): { valid: boolean; error?: string } {
  // Verificar tamanho
  if (file.size > maxSize) {
    return {
      valid: false,
      error: `Arquivo muito grande. Tamanho máximo: ${formatFileSize(maxSize)}`
    };
  }
  
  // Verificar tipo de arquivo (lista básica de tipos permitidos)
  const allowedTypes = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'video/mp4',
    'video/webm',
    'video/quicktime',
    'audio/mpeg',
    'audio/wav',
    'audio/ogg',
    'application/pdf',
    'text/plain',
    'application/json',
    'application/zip',
    'application/x-rar-compressed'
  ];
  
  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: 'Tipo de arquivo não permitido'
    };
  }
  
  return { valid: true };
}

/**
 * Extrai metadados básicos do arquivo
 */
export function extractFileMetadata(file: File) {
  return {
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: new Date(file.lastModified),
    extension: file.name.split('.').pop()?.toLowerCase() || ''
  };
}