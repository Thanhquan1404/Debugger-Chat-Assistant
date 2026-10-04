import { X } from 'lucide-react';
import { useEffect, useState } from 'react';

interface ImagePreviewProps {
  file: File;
  onRemove: () => void;
}

export function ImagePreview({ file, onRemove }: ImagePreviewProps) {
  const [previewUrl, setPreviewUrl] = useState('');

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <div className="relative w-fit overflow-hidden rounded-xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      {previewUrl && <img src={previewUrl} alt={file.name} className="h-24 w-32 object-cover" />}
      <button
        type="button"
        onClick={onRemove}
        className="absolute right-1.5 top-1.5 inline-flex size-7 items-center justify-center rounded-full bg-black/65 text-white backdrop-blur-sm transition hover:bg-black/80"
        aria-label="Remove image"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}
