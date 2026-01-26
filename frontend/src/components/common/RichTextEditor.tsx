import { CKEditor } from '@ckeditor/ckeditor5-react';
import ClassicEditor from '@ckeditor/ckeditor5-build-classic';
import type { EditorConfig } from '@ckeditor/ckeditor5-core';


interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  config?: EditorConfig;
}

const BASE_CONFIG: EditorConfig = {
  toolbar: [
    'heading',
    '|',
    'bold',
    'italic',
    'link',
    'bulletedList',
    'numberedList',
    '|',
    'blockQuote',
    'insertTable',
    '|',
    'undo',
    'redo',
  ],
  table: {
    contentToolbar: ['tableColumn', 'tableRow', 'mergeTableCells'],
  },
};

export function RichTextEditor({ value, onChange, placeholder, disabled, className, config }: RichTextEditorProps) {
  const editorConfig: EditorConfig = {
    ...BASE_CONFIG,
    placeholder,
    ...(config ?? {}),
  };

  return (
    <div className={className}>
      <CKEditor
        editor={ClassicEditor}
        data={value}
        config={editorConfig}
        disabled={disabled}
        onChange={(_, editor) => {
          const data = editor.getData();
          onChange(data);
        }}
      />
    </div>
  );
}
