import React, { useMemo, useRef } from 'react';
import { clearSubtitleSelection, CJK_LANGUAGES, getSubtitleSelection, segmentSubtitleText } from '@/lib/subtitle-segmentation';
import { cn } from '@/lib/utils';

interface InteractiveSubtitleTextProps {
  text: string;
  language?: string;
  className?: string;
  wordClassName?: string;
  onWordClick?: (word: string, x: number, y: number) => void;
  onWordDoubleClick?: (phrase: string, x: number, y: number) => void;
  onPhraseSelect?: (text: string, x: number, y: number) => void;
}

const Word = React.memo(({
  word,
  isCjk,
  onClick,
  onDoubleClick,
  className,
  dataIndex,
}: {
  word: string;
  isCjk: boolean;
  className?: string;
  onClick?: (word: string, event: React.MouseEvent<HTMLSpanElement>) => void;
  onDoubleClick?: (event: React.MouseEvent<HTMLSpanElement>) => void;
  dataIndex: number;
}) => {
  const handleClick = (event: React.MouseEvent<HTMLSpanElement>) => {
    event.stopPropagation();
    const selection = window.getSelection?.();
    if (selection && selection.toString().trim().length > 0) return;
    onClick?.(word, event);
  };

  return (
    <span
      data-word={word}
      data-index={dataIndex}
      className={cn(
        'cursor-help rounded-md transition-colors hover:text-primary',
        isCjk && 'hover:bg-primary/20 px-0.5',
        className,
      )}
      onClick={handleClick}
      onDoubleClick={(event) => {
        event.stopPropagation();
        event.preventDefault();
        onDoubleClick?.(event);
      }}
    >
      {word}
      {isCjk ? '' : ' '}
    </span>
  );
});

Word.displayName = 'InteractiveSubtitleWord';

export const InteractiveSubtitleText = ({
  text,
  language,
  className,
  wordClassName,
  onWordClick,
  onWordDoubleClick,
  onPhraseSelect,
}: InteractiveSubtitleTextProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const isCjk = CJK_LANGUAGES.has(language || '');

  const words = useMemo(() => segmentSubtitleText(text, language), [text, language]);

  return (
    <div
      ref={containerRef}
      className={cn('select-text', className)}
      onMouseUp={() => {
        if (!onPhraseSelect) return;

        requestAnimationFrame(() => {
          const selection = getSubtitleSelection(containerRef);
          if (!selection || selection.text.length < 2) return;
          onPhraseSelect(selection.text, selection.position.x, selection.position.y);
        });
      }}
      onTouchEnd={(e) => {
        if (!onPhraseSelect) return;
        e.preventDefault();

        requestAnimationFrame(() => {
          const selection = getSubtitleSelection(containerRef);
          if (!selection || selection.text.length < 2) return;
          onPhraseSelect(selection.text, selection.position.x, selection.position.y);
        });
      }}
    >
      {words.map((word, index) => (
        <Word
          key={`${word}-${index}`}
          word={word}
          isCjk={isCjk}
          className={wordClassName}
          dataIndex={index}
          onClick={onWordClick ? (word, event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            clearSubtitleSelection();
            onWordClick(word, rect.left + rect.width / 2, rect.top);
          } : undefined}
          onDoubleClick={onWordDoubleClick ? (event) => {
            const current = words[index];
            const next = words[index + 1];
            if (!current || !next) return;
            const phrase = isCjk ? `${current}${next}` : `${current} ${next}`;
            const rect = event.currentTarget.getBoundingClientRect();
            clearSubtitleSelection();
            onWordDoubleClick(phrase, rect.left + rect.width / 2, rect.top);
          } : undefined}
        />
      ))}
    </div>
  );
};
