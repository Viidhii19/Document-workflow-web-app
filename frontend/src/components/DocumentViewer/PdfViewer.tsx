import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import { useAppStore } from '../../store/useAppStore';
import { getPdfUrl } from '../../services/api';
import type { Citation } from '../../types';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

type TextRef = {
  node: Text;
  offset: number;
  length: number;
};

type TextIndex = {
  text: string;
  refs: TextRef[];
};

type MatchRange = {
  start: number;
  end: number;
};

const MIN_PARTIAL_TOKENS = 6;
const MIN_SCALE = 0.7;
const MAX_SCALE = 2;
const SCALE_STEP = 0.15;

const toolbarButtonStyle: React.CSSProperties = {
  width: 32,
  height: 32,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--bg-secondary)',
  color: 'var(--text-primary)',
  cursor: 'pointer',
};

const disabledButtonStyle: React.CSSProperties = {
  opacity: 0.45,
  cursor: 'not-allowed',
};

const normalizeCharacter = (char: string): string => {
  const withoutMarks = char
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

  let normalized = '';
  for (const part of withoutMarks) {
    if (/[\p{L}\p{N}]/u.test(part)) {
      normalized += part;
    } else if (/\s/u.test(part) || /[\p{P}\p{S}]/u.test(part)) {
      normalized += ' ';
    }
  }

  return normalized;
};

const normalizeTextForMatch = (value: string): string => {
  let normalized = '';
  let previousWasSpace = true;

  for (let offset = 0; offset < value.length;) {
    const codePoint = value.codePointAt(offset);
    if (codePoint === undefined) break;

    const char = String.fromCodePoint(codePoint);
    offset += char.length;

    for (const normalizedChar of normalizeCharacter(char)) {
      if (normalizedChar === ' ') {
        if (!previousWasSpace) {
          normalized += ' ';
          previousWasSpace = true;
        }
      } else {
        normalized += normalizedChar;
        previousWasSpace = false;
      }
    }
  }

  return normalized.trim();
};

const buildTextIndex = (textLayer: HTMLElement): TextIndex => {
  const walker = document.createTreeWalker(textLayer, NodeFilter.SHOW_TEXT);
  const refs: TextRef[] = [];
  let text = '';
  let previousWasSpace = true;

  while (walker.nextNode()) {
    const node = walker.currentNode as Text;
    const value = node.nodeValue ?? '';

    for (let offset = 0; offset < value.length;) {
      const codePoint = value.codePointAt(offset);
      if (codePoint === undefined) break;

      const char = String.fromCodePoint(codePoint);
      const length = char.length;
      const normalized = normalizeCharacter(char);

      for (const normalizedChar of normalized) {
        if (normalizedChar === ' ') {
          if (!previousWasSpace) {
            text += ' ';
            refs.push({ node, offset, length });
            previousWasSpace = true;
          }
        } else {
          text += normalizedChar;
          refs.push({ node, offset, length });
          previousWasSpace = false;
        }
      }

      offset += length;
    }
  }

  while (text.startsWith(' ')) {
    text = text.slice(1);
    refs.shift();
  }

  while (text.endsWith(' ')) {
    text = text.slice(0, -1);
    refs.pop();
  }

  return { text, refs };
};

const tightenRange = (pageText: string, start: number, end: number): MatchRange | null => {
  let rangeStart = start;
  let rangeEnd = end;

  while (rangeStart < rangeEnd && pageText[rangeStart] === ' ') rangeStart += 1;
  while (rangeEnd > rangeStart && pageText[rangeEnd - 1] === ' ') rangeEnd -= 1;

  if (rangeEnd <= rangeStart) return null;
  return { start: rangeStart, end: rangeEnd };
};

const findCitationMatch = (pageText: string, citation: Citation): MatchRange | null => {
  const normalizedQuote = normalizeTextForMatch(citation.normalized_quote || citation.quote);
  if (!normalizedQuote) return null;

  const exactIndex = pageText.indexOf(normalizedQuote);
  if (exactIndex >= 0) {
    return tightenRange(pageText, exactIndex, exactIndex + normalizedQuote.length);
  }

  const tokens = normalizedQuote.split(' ').filter(Boolean);
  if (tokens.length < MIN_PARTIAL_TOKENS + 2) {
    return null;
  }

  const minWindow = Math.max(MIN_PARTIAL_TOKENS, Math.ceil(tokens.length * 0.72));
  const maxWindow = Math.min(tokens.length, 32);

  for (let size = maxWindow; size >= minWindow; size -= 1) {
    for (let start = 0; start <= tokens.length - size; start += 1) {
      const partialQuote = tokens.slice(start, start + size).join(' ');
      const partialIndex = pageText.indexOf(partialQuote);

      if (partialIndex >= 0) {
        return tightenRange(pageText, partialIndex, partialIndex + partialQuote.length);
      }
    }
  }

  return null;
};

const clearHighlightLayer = (highlightLayer: HTMLDivElement | null) => {
  highlightLayer?.replaceChildren();
};

export const PdfViewer: React.FC = () => {
  const { activeDocument, activeCitation, setActiveCitation } = useAppStore();
  const [numPages, setNumPages] = useState<number>();
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.2);
  const pageRef = useRef<HTMLDivElement | null>(null);
  const highlightLayerRef = useRef<HTMLDivElement | null>(null);

  const requestedPage = activeCitation?.page || pageNumber;
  const currentPage = useMemo(() => {
    const upperBound = numPages || requestedPage || 1;
    return Math.min(Math.max(1, requestedPage || 1), upperBound);
  }, [numPages, requestedPage]);

  const onDocumentLoadSuccess = ({ numPages: loadedPages }: { numPages: number }) => {
    setNumPages(loadedPages);
    if (pageNumber > loadedPages) {
      setPageNumber(loadedPages);
    }
  };

  const goToPage = (nextPage: number) => {
    const upperBound = numPages || 1;
    setActiveCitation(null);
    setPageNumber(Math.min(Math.max(1, nextPage), upperBound));
  };

  const applyCitationHighlight = useCallback(() => {
    const pageElement = pageRef.current;
    const highlightLayer = highlightLayerRef.current;
    clearHighlightLayer(highlightLayer);

    if (!pageElement || !highlightLayer || !activeCitation || activeCitation.page !== currentPage) {
      return;
    }

    const textLayer = pageElement.querySelector<HTMLElement>(
      '.react-pdf__Page__textContent, .textLayer',
    );
    if (!textLayer) return;

    const textIndex = buildTextIndex(textLayer);
    const match = findCitationMatch(textIndex.text, activeCitation);
    if (!match) return;

    const startRef = textIndex.refs[match.start];
    const endRef = textIndex.refs[match.end - 1];
    if (!startRef || !endRef) return;

    const range = document.createRange();
    range.setStart(startRef.node, startRef.offset);
    range.setEnd(endRef.node, endRef.offset + endRef.length);

    const pageRect = pageElement.getBoundingClientRect();
    const fragment = document.createDocumentFragment();

    for (const rect of Array.from(range.getClientRects())) {
      if (rect.width < 1 || rect.height < 1) continue;

      const highlight = document.createElement('div');
      highlight.style.position = 'absolute';
      highlight.style.left = `${rect.left - pageRect.left}px`;
      highlight.style.top = `${rect.top - pageRect.top}px`;
      highlight.style.width = `${rect.width}px`;
      highlight.style.height = `${rect.height}px`;
      highlight.style.background = 'rgba(255, 235, 59, 0.42)';
      highlight.style.boxShadow = '0 0 0 1px rgba(255, 214, 10, 0.55)';
      highlight.style.borderRadius = '2px';
      highlight.style.pointerEvents = 'none';
      fragment.appendChild(highlight);
    }

    highlightLayer.appendChild(fragment);
    range.detach();

    const firstHighlight = highlightLayer.firstElementChild;
    if (firstHighlight instanceof HTMLElement) {
      firstHighlight.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
    }
  }, [activeCitation, currentPage]);

  const scheduleHighlight = useCallback(() => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(applyCitationHighlight);
    });
  }, [applyCitationHighlight]);

  useEffect(() => {
    scheduleHighlight();
  }, [activeDocument?.id, currentPage, scale, activeCitation, scheduleHighlight]);

  useEffect(() => {
    const pageElement = pageRef.current;
    if (!pageElement) return;

    const observer = new ResizeObserver(scheduleHighlight);
    observer.observe(pageElement);

    return () => observer.disconnect();
  }, [scheduleHighlight]);

  if (!activeDocument) return null;

  const canGoPrevious = currentPage > 1;
  const canGoNext = currentPage < (numPages || 1);

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#2a2a2a', overflow: 'hidden' }}>
      <div style={{ padding: 'var(--spacing-md)', backgroundColor: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--spacing-md)' }}>
        <h2 style={{ margin: 0, fontSize: '1rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{activeDocument.filename}</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <button
            aria-label="Previous page"
            title="Previous page"
            disabled={!canGoPrevious}
            onClick={() => goToPage(currentPage - 1)}
            style={{ ...toolbarButtonStyle, ...(!canGoPrevious ? disabledButtonStyle : {}) }}
          >
            <ChevronLeft size={16} />
          </button>
          <span style={{ fontSize: '0.875rem', minWidth: 104, textAlign: 'center' }}>
            Page {currentPage} of {numPages || '-'}
          </span>
          <button
            aria-label="Next page"
            title="Next page"
            disabled={!canGoNext}
            onClick={() => goToPage(currentPage + 1)}
            style={{ ...toolbarButtonStyle, ...(!canGoNext ? disabledButtonStyle : {}) }}
          >
            <ChevronRight size={16} />
          </button>
          <button
            aria-label="Zoom out"
            title="Zoom out"
            disabled={scale <= MIN_SCALE}
            onClick={() => setScale((value) => Math.max(MIN_SCALE, Number((value - SCALE_STEP).toFixed(2))))}
            style={{ ...toolbarButtonStyle, ...(scale <= MIN_SCALE ? disabledButtonStyle : {}) }}
          >
            <ZoomOut size={16} />
          </button>
          <button
            aria-label="Zoom in"
            title="Zoom in"
            disabled={scale >= MAX_SCALE}
            onClick={() => setScale((value) => Math.min(MAX_SCALE, Number((value + SCALE_STEP).toFixed(2))))}
            style={{ ...toolbarButtonStyle, ...(scale >= MAX_SCALE ? disabledButtonStyle : {}) }}
          >
            <ZoomIn size={16} />
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', display: 'flex', justifyContent: 'center', padding: 'var(--spacing-lg)' }}>
        <Document
          key={activeDocument.id}
          file={getPdfUrl(activeDocument.id)}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={<div style={{ color: 'white' }}>Loading PDF...</div>}
        >
          <div ref={pageRef} style={{ position: 'relative' }}>
            <Page
              pageNumber={currentPage}
              renderTextLayer
              renderAnnotationLayer={false}
              onRenderTextLayerSuccess={scheduleHighlight}
              scale={scale}
            />
            <div
              ref={highlightLayerRef}
              aria-hidden="true"
              style={{
                position: 'absolute',
                inset: 0,
                pointerEvents: 'none',
                zIndex: 3,
              }}
            />
          </div>
        </Document>
      </div>
    </div>
  );
};
