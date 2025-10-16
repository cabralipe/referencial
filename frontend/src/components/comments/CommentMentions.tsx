import React, { useState, useRef, useCallback } from 'react';
import { User } from 'lucide-react';
import type { MentionUser, MentionSuggestion } from '@/types/comments';
import './CommentMentions.css';

interface CommentMentionsProps {
  value: string;
  onChange: (value: string, mentions: number[]) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  onFocus?: () => void;
  onBlur?: () => void;
}

interface MentionPosition {
  start: number;
  end: number;
  query: string;
}

// Mock function to fetch users - replace with actual API call
const fetchUsers = async (query: string): Promise<MentionUser[]> => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 200));
  
  // Mock users data
  const mockUsers: MentionUser[] = [
    { id: 1, username: 'joao.silva', name: 'João Silva', avatar: null },
    { id: 2, username: 'maria.santos', name: 'Maria Santos', avatar: null },
    { id: 3, username: 'pedro.oliveira', name: 'Pedro Oliveira', avatar: null },
    { id: 4, username: 'ana.costa', name: 'Ana Costa', avatar: null },
    { id: 5, username: 'carlos.ferreira', name: 'Carlos Ferreira', avatar: null },
  ];
  
  return mockUsers.filter(user => 
    user.username.toLowerCase().includes(query.toLowerCase()) ||
    user.name.toLowerCase().includes(query.toLowerCase())
  );
};

export function CommentMentions({
  value,
  onChange,
  placeholder = 'Digite seu comentário...',
  className = '',
  disabled = false,
  onFocus,
  onBlur,
}: CommentMentionsProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [suggestions, setSuggestions] = useState<MentionSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(0);
  const [mentionPosition, setMentionPosition] = useState<MentionPosition | null>(null);
  const [mentions, setMentions] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Find mention at cursor position
  const findMentionAtCursor = useCallback((text: string, cursorPos: number): MentionPosition | null => {
    const beforeCursor = text.substring(0, cursorPos);
    const lastAtIndex = beforeCursor.lastIndexOf('@');
    
    if (lastAtIndex === -1) return null;
    
    const afterAt = text.substring(lastAtIndex + 1);
    const spaceIndex = afterAt.indexOf(' ');
    const endIndex = spaceIndex === -1 ? text.length : lastAtIndex + 1 + spaceIndex;
    
    // Check if there's a space before @ (or it's at the beginning)
    const beforeAt = lastAtIndex > 0 ? text[lastAtIndex - 1] : ' ';
    if (beforeAt !== ' ' && beforeAt !== '\n' && lastAtIndex !== 0) {
      return null;
    }
    
    const query = text.substring(lastAtIndex + 1, cursorPos);
    
    // Only show suggestions if cursor is right after @ or within the mention
    if (cursorPos >= lastAtIndex + 1 && cursorPos <= endIndex) {
      return {
        start: lastAtIndex,
        end: endIndex,
        query,
      };
    }
    
    return null;
  }, []);

  // Load suggestions
  const loadSuggestions = useCallback(async (query: string) => {
    if (query.length === 0) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setIsLoading(true);
    try {
      const users = await fetchUsers(query);
      const suggestionList: MentionSuggestion[] = users.map(user => ({
        id: user.id,
        username: user.username,
        name: user.name,
        avatar: user.avatar,
        type: 'user',
      }));
      
      setSuggestions(suggestionList);
      setShowSuggestions(suggestionList.length > 0);
      setSelectedSuggestionIndex(0);
    } catch (error) {
      console.error('Error loading user suggestions:', error);
      setSuggestions([]);
      setShowSuggestions(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle text change
  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    const cursorPos = e.target.selectionStart;
    
    // Find mentions in the text
    const mentionRegex = /@(\w+)/g;
    const foundMentions: number[] = [];
    let match;
    
    while ((match = mentionRegex.exec(newValue)) !== null) {
      // This is a simplified approach - in a real app, you'd need to track
      // which usernames correspond to which user IDs
      const username = match[1];
      // For now, we'll just use a mock ID based on username
      foundMentions.push(username.length); // Mock ID
    }
    
    setMentions(foundMentions);
    
    // Check for mention at cursor
    const mention = findMentionAtCursor(newValue, cursorPos);
    setMentionPosition(mention);
    
    if (mention) {
      loadSuggestions(mention.query);
    } else {
      setShowSuggestions(false);
      setSuggestions([]);
    }
    
    onChange(newValue, foundMentions);
  }, [findMentionAtCursor, loadSuggestions, onChange]);

  // Handle key down
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      
      case 'ArrowUp':
        e.preventDefault();
        setSelectedSuggestionIndex(prev => 
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      
      case 'Enter':
      case 'Tab':
        if (mentionPosition && suggestions[selectedSuggestionIndex]) {
          e.preventDefault();
          insertMention(suggestions[selectedSuggestionIndex]);
        }
        break;
      
      case 'Escape':
        setShowSuggestions(false);
        setSuggestions([]);
        break;
    }
  }, [showSuggestions, suggestions, selectedSuggestionIndex, mentionPosition, insertMention]);

  // Insert mention
  const insertMention = useCallback((suggestion: MentionSuggestion) => {
    if (!mentionPosition || !textareaRef.current) return;

    const textarea = textareaRef.current;
    const beforeMention = value.substring(0, mentionPosition.start);
    const afterMention = value.substring(mentionPosition.end);
    const mentionText = `@${suggestion.username} `;
    
    const newValue = beforeMention + mentionText + afterMention;
    const newCursorPos = mentionPosition.start + mentionText.length;
    
    // Update mentions list
    const newMentions = [...mentions, suggestion.id];
    setMentions(newMentions);
    
    onChange(newValue, newMentions);
    
    // Set cursor position after mention
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
    
    setShowSuggestions(false);
    setSuggestions([]);
    setMentionPosition(null);
  }, [mentionPosition, value, mentions, onChange]);

  // Calculate suggestion box position
  const getSuggestionBoxStyle = useCallback(() => {
    if (!textareaRef.current || !mentionPosition) return {};

    const textarea = textareaRef.current;
    const rect = textarea.getBoundingClientRect();
    
    // This is a simplified positioning - in a real app, you'd want more sophisticated positioning
    return {
      position: 'absolute' as const,
      top: rect.bottom + 4,
      left: rect.left,
      zIndex: 1000,
    };
  }, [mentionPosition]);

  return (
    <div className="comment-mentions">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleTextChange}
        onKeyDown={handleKeyDown}
        onFocus={onFocus}
        onBlur={onBlur}
        placeholder={placeholder}
        disabled={disabled}
        className={`comment-mentions__textarea ${className}`}
        rows={3}
      />
      
      {showSuggestions && suggestions.length > 0 && (
        <div 
          className="comment-mentions__suggestions"
          style={getSuggestionBoxStyle()}
        >
          {isLoading && (
            <div className="comment-mentions__loading">
              Carregando usuários...
            </div>
          )}
          
          {suggestions.map((suggestion, index) => (
            <button
              key={suggestion.id}
              type="button"
              className={`comment-mentions__suggestion ${
                index === selectedSuggestionIndex ? 'comment-mentions__suggestion--selected' : ''
              }`}
              onClick={() => insertMention(suggestion)}
              onMouseEnter={() => setSelectedSuggestionIndex(index)}
            >
              <div className="comment-mentions__suggestion-avatar">
                {suggestion.avatar ? (
                  <img src={suggestion.avatar} alt={suggestion.name} />
                ) : (
                  <User size={20} />
                )}
              </div>
              <div className="comment-mentions__suggestion-info">
                <div className="comment-mentions__suggestion-name">
                  {suggestion.name}
                </div>
                <div className="comment-mentions__suggestion-username">
                  @{suggestion.username}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Hook for using mentions in other components
export function useMentions() {
  const [mentions, setMentions] = useState<number[]>([]);
  const [mentionText, setMentionText] = useState('');

  const handleMentionChange = useCallback((text: string, mentionIds: number[]) => {
    setMentionText(text);
    setMentions(mentionIds);
  }, []);

  const clearMentions = useCallback(() => {
    setMentions([]);
    setMentionText('');
  }, []);

  return {
    mentions,
    mentionText,
    handleMentionChange,
    clearMentions,
  };
}