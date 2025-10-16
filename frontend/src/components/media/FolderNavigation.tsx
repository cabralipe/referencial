/**
 * Componente de navegação de pastas
 */

import React, { useState, useMemo } from 'react';
import { 
  Folder, 
  FolderOpen, 
  ChevronRight, 
  ChevronDown, 
  Home,
  Search
} from 'lucide-react';
import { MediaFolder, FolderTreeNode } from '../../types/media';

interface FolderNavigationProps {
  folders: MediaFolder[];
  selectedFolder: string | null;
  onFolderSelect: (folderId: string | null) => void;
  loading?: boolean;
}

export const FolderNavigation: React.FC<FolderNavigationProps> = ({
  folders,
  selectedFolder,
  onFolderSelect,
  loading = false
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  // Construir árvore de pastas
  const folderTree = useMemo(() => {
    const buildTree = (parentId: string | null = null): FolderTreeNode[] => {
      return folders
        .filter(folder => folder.parent === parentId)
        .map(folder => ({
          ...folder,
          children: buildTree(folder.id)
        }))
        .sort((a, b) => a.name.localeCompare(b.name));
    };

    return buildTree();
  }, [folders]);

  // Filtrar pastas por termo de busca
  const filteredTree = useMemo(() => {
    if (!searchTerm) return folderTree;

    const filterTree = (nodes: FolderTreeNode[]): FolderTreeNode[] => {
      return nodes.reduce((acc: FolderTreeNode[], node) => {
        const matchesSearch = node.name.toLowerCase().includes(searchTerm.toLowerCase());
        const filteredChildren = filterTree(node.children);
        
        if (matchesSearch || filteredChildren.length > 0) {
          acc.push({
            ...node,
            children: filteredChildren
          });
        }
        
        return acc;
      }, []);
    };

    return filterTree(folderTree);
  }, [folderTree, searchTerm]);

  const toggleFolder = (folderId: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderId)) {
        newSet.delete(folderId);
      } else {
        newSet.add(folderId);
      }
      return newSet;
    });
  };

  const isExpanded = (folderId: string) => {
    return expandedFolders.has(folderId);
  };

  const handleFolderClick = (folderId: string | null) => {
    onFolderSelect(folderId);
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="animate-pulse space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Pastas</h3>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar pastas..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Folder Tree */}
      <div className="p-2">
        {/* Root folder */}
        <button
          onClick={() => handleFolderClick(null)}
          className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-gray-100 ${
            selectedFolder === null ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
          }`}
        >
          <Home className="w-4 h-4" />
          <span>Todos os arquivos</span>
        </button>

        {/* Folder tree */}
        <div className="mt-2">
          {filteredTree.length > 0 ? (
            <FolderTreeView
              nodes={filteredTree}
              selectedFolder={selectedFolder}
              expandedFolders={expandedFolders}
              onFolderSelect={handleFolderClick}
              onToggleExpand={toggleFolder}
              level={0}
            />
          ) : (
            <div className="text-sm text-gray-500 text-center py-4">
              {searchTerm ? 'Nenhuma pasta encontrada' : 'Nenhuma pasta criada'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Componente recursivo para renderizar a árvore de pastas
interface FolderTreeViewProps {
  nodes: FolderTreeNode[];
  selectedFolder: string | null;
  expandedFolders: Set<string>;
  onFolderSelect: (folderId: string) => void;
  onToggleExpand: (folderId: string) => void;
  level: number;
}

const FolderTreeView: React.FC<FolderTreeViewProps> = ({
  nodes,
  selectedFolder,
  expandedFolders,
  onFolderSelect,
  onToggleExpand,
  level
}) => {
  return (
    <div>
      {nodes.map((node) => (
        <FolderTreeItem
          key={node.id}
          node={node}
          selectedFolder={selectedFolder}
          expandedFolders={expandedFolders}
          onFolderSelect={onFolderSelect}
          onToggleExpand={onToggleExpand}
          level={level}
        />
      ))}
    </div>
  );
};

// Componente individual de item da árvore
interface FolderTreeItemProps {
  node: FolderTreeNode;
  selectedFolder: string | null;
  expandedFolders: Set<string>;
  onFolderSelect: (folderId: string) => void;
  onToggleExpand: (folderId: string) => void;
  level: number;
}

const FolderTreeItem: React.FC<FolderTreeItemProps> = ({
  node,
  selectedFolder,
  expandedFolders,
  onFolderSelect,
  onToggleExpand,
  level
}) => {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedFolders.has(node.id);
  const isSelected = selectedFolder === node.id;

  const handleClick = () => {
    onFolderSelect(node.id);
  };

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (hasChildren) {
      onToggleExpand(node.id);
    }
  };

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1.5 text-sm rounded-md hover:bg-gray-100 cursor-pointer ${
          isSelected ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
        }`}
        style={{ paddingLeft: `${(level + 1) * 12 + 8}px` }}
        onClick={handleClick}
      >
        {/* Expand/Collapse button */}
        <button
          onClick={handleToggle}
          className="flex-shrink-0 w-4 h-4 flex items-center justify-center hover:bg-gray-200 rounded"
        >
          {hasChildren ? (
            isExpanded ? (
              <ChevronDown className="w-3 h-3" />
            ) : (
              <ChevronRight className="w-3 h-3" />
            )
          ) : (
            <div className="w-3 h-3" />
          )}
        </button>

        {/* Folder icon */}
        <div className="flex-shrink-0">
          {isExpanded ? (
            <FolderOpen className="w-4 h-4" />
          ) : (
            <Folder className="w-4 h-4" />
          )}
        </div>

        {/* Folder name */}
        <span className="flex-1 truncate" title={node.name}>
          {node.name}
        </span>

        {/* File count */}
        {node.files_count > 0 && (
          <span className="flex-shrink-0 text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
            {node.files_count}
          </span>
        )}
      </div>

      {/* Children */}
      {hasChildren && isExpanded && (
        <FolderTreeView
          nodes={node.children}
          selectedFolder={selectedFolder}
          expandedFolders={expandedFolders}
          onFolderSelect={onFolderSelect}
          onToggleExpand={onToggleExpand}
          level={level + 1}
        />
      )}
    </div>
  );
};