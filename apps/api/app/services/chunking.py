import re
import uuid

from loguru import logger
from sqlalchemy.orm import Session

from app.models.chunk import DocumentChunk

# Chunking parameters
CHUNK_SIZE = 1000  # ~250 tokens for English text
CHUNK_OVERLAP = 200

# Page marker regex matching PyMuPDF output from TextExtractionService
PAGE_MARKER_RE = re.compile(r"^--- Page (\d+) ---$", re.MULTILINE)


class ChunkingService:
    def chunk_document(
        self,
        document_id: uuid.UUID,
        investigation_id: uuid.UUID,
        extracted_text: str,
        session: Session,
    ) -> list[DocumentChunk]:
        """Split extracted text into overlapping chunks with page provenance.

        Returns the list of created DocumentChunk objects.
        """
        if not extracted_text or not extracted_text.strip():
            logger.info("Empty text, no chunks to create", document_id=str(document_id))
            return []

        pages = self._parse_pages(extracted_text)
        raw_chunks = self._split_into_chunks(pages, extracted_text)

        chunks: list[DocumentChunk] = []
        for seq, (text, page_start, page_end, offset_start, offset_end) in enumerate(
            raw_chunks
        ):
            chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                investigation_id=investigation_id,
                sequence_number=seq,
                text=text,
                page_start=page_start,
                page_end=page_end,
                char_offset_start=offset_start,
                char_offset_end=offset_end,
            )
            chunks.append(chunk)

        session.add_all(chunks)
        session.flush()

        logger.info(
            "Document chunked",
            document_id=str(document_id),
            chunk_count=len(chunks),
        )
        return chunks

    def _parse_pages(
        self, text: str
    ) -> list[tuple[int, str, int]]:
        """Parse page markers and return list of (page_number, page_text, char_offset).

        If no page markers found, treats entire text as page 1.
        """
        markers = list(PAGE_MARKER_RE.finditer(text))

        if not markers:
            return [(1, text, 0)]

        pages: list[tuple[int, str, int]] = []
        for i, match in enumerate(markers):
            page_num = int(match.group(1))
            content_start = match.end()
            # Strip leading newline after marker
            if content_start < len(text) and text[content_start] == "\n":
                content_start += 1

            if i + 1 < len(markers):
                content_end = markers[i + 1].start()
            else:
                content_end = len(text)

            page_text = text[content_start:content_end].rstrip()
            pages.append((page_num, page_text, content_start))

        return pages

    def _split_into_chunks(
        self,
        pages: list[tuple[int, str, int]],
        full_text: str,
    ) -> list[tuple[str, int, int, int, int]]:
        """Split pages into overlapping chunks.

        Returns list of (chunk_text, page_start, page_end, char_offset_start, char_offset_end).
        """
        # Build a flat content string with page tracking
        # Each position maps to a page number
        content_segments: list[tuple[str, int, int]] = []  # (text, page_num, global_offset)
        for page_num, page_text, content_offset in pages:
            if not page_text:
                continue
            # Locate page_text in full_text starting from the known content offset
            idx = full_text.find(page_text, content_offset)
            if idx == -1:
                # Fallback: use content_offset directly (content start, not marker start)
                idx = content_offset
            content_segments.append((page_text, page_num, idx))

        if not content_segments:
            return []

        # Concatenate all page texts with a space separator, tracking page boundaries
        combined_text = ""
        page_boundaries: list[tuple[int, int, int]] = (
            []
        )  # (start_in_combined, page_num, global_offset)

        for page_text, page_num, global_offset in content_segments:
            start_in_combined = len(combined_text)
            if combined_text:
                combined_text += " "
                start_in_combined = len(combined_text)
            combined_text += page_text
            page_boundaries.append((start_in_combined, page_num, global_offset))

        if not combined_text.strip():
            return []

        # Split combined text into chunks
        chunks: list[tuple[str, int, int, int, int]] = []
        pos = 0
        text_len = len(combined_text)

        while pos < text_len:
            end = min(pos + CHUNK_SIZE, text_len)

            # Try to split at a sentence boundary near the end
            if end < text_len:
                boundary = self._find_sentence_boundary(combined_text, pos, end)
                if boundary > pos:
                    end = boundary

            chunk_text = combined_text[pos:end]

            # Determine page range for this chunk
            page_start = self._page_at_position(pos, page_boundaries)
            page_end = self._page_at_position(end - 1, page_boundaries)

            # Map combined-text positions back to global offsets
            global_start = self._global_offset_at(pos, page_boundaries, content_segments)
            global_end = self._global_offset_at(
                end - 1, page_boundaries, content_segments
            ) + 1

            chunks.append((chunk_text, page_start, page_end, global_start, global_end))

            # Advance with overlap; guard against stall if overlap >= chunk size
            next_pos = end - CHUNK_OVERLAP
            if next_pos <= pos:
                next_pos = end
            pos = next_pos
            if end >= text_len:
                break

        return chunks

    def _find_sentence_boundary(self, text: str, start: int, end: int) -> int:
        """Find the best sentence boundary near `end`, searching backward.

        Returns position after the sentence-ending punctuation, or `end` if none found.
        """
        # Search backward from end for ". " or ".\n"
        search_start = max(start + (CHUNK_SIZE // 2), start)  # Don't go too far back
        search_region = text[search_start:end]

        # Find last sentence-ending punctuation followed by space/newline
        last_boundary = -1
        for match in re.finditer(r"[.!?]\s", search_region):
            last_boundary = search_start + match.end()

        if last_boundary > start:
            return last_boundary

        return end

    def _page_at_position(
        self, pos: int, page_boundaries: list[tuple[int, int, int]]
    ) -> int:
        """Determine which page a position in combined text belongs to."""
        page_num = page_boundaries[0][1]
        for boundary_start, pnum, _ in page_boundaries:
            if pos >= boundary_start:
                page_num = pnum
            else:
                break
        return page_num

    def _global_offset_at(
        self,
        pos: int,
        page_boundaries: list[tuple[int, int, int]],
        content_segments: list[tuple[str, int, int]],
    ) -> int:
        """Map a position in combined text back to global offset in original text."""
        # Find which page segment this position belongs to
        seg_idx = 0
        for i, (boundary_start, _, _) in enumerate(page_boundaries):
            if pos >= boundary_start:
                seg_idx = i
            else:
                break

        boundary_start = page_boundaries[seg_idx][0]
        global_offset = content_segments[seg_idx][2]
        offset_within_segment = pos - boundary_start

        return global_offset + offset_within_segment
