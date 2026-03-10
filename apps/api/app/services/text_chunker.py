from dataclasses import dataclass
from typing import List


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    content: str
    index: int
    start_char: int
    end_char: int


class TextChunker:
    """Split text into overlapping chunks for embedding."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[TextChunk]:
        """Split text into overlapping chunks."""
        if not text or not text.strip():
            return []

        text = text.strip()

        chunks: List[TextChunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                # Try to break at a sentence boundary
                for sep in [". ", ".\n", "? ", "!\n", "\n\n"]:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break
                else:
                    # Fallback to word boundary
                    last_space = text.rfind(" ", start, end)
                    if last_space > start:
                        end = last_space + 1
            else:
                end = len(text)

            chunk_content = text[start:end].strip()

            if chunk_content:
                chunks.append(
                    TextChunk(
                        content=chunk_content,
                        index=index,
                        start_char=start,
                        end_char=end,
                    )
                )
                index += 1

            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
            # Ensure progress
            if chunks and start <= chunks[-1].start_char:
                start = end

        return chunks


text_chunker = TextChunker()

