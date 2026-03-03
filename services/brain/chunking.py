from __future__ import annotations
import html
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def _encode(txt: str) -> List[int]:
        return _ENC.encode(txt)

    def _decode(tokens: List[int]) -> str:
        return _ENC.decode(tokens)

except Exception:
    _WORD_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

    def _encode(txt: str) -> List[int]:
        return [abs(hash(t)) % (2**20) for t in _WORD_RE.findall(txt)]

    def _decode(tokens: List[int]) -> str:
        raise RuntimeError("Fallback tokenizer cannot decode tokens back to text")


_CODE_BLOCK_RE = re.compile(r"```.*?```", flags=re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
MULTI_NL_RE = re.compile(r"\n{3,}")
NBSP_RE = re.compile(r"\xa0")


def _strip_html(text: str) -> str:
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    return text


def _normalize_ws(text: str) -> str:
    text = NBSP_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MULTI_NL_RE.sub("\n\n", text)
    return text.strip()


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_MD_LIST_RE = re.compile(r"^(\s*[-*+]\s+|\s*\d+\.\s+)", re.MULTILINE)


def _split_markdown_sections(
    text: str,
) -> List[Tuple[str, Tuple[int, int], Dict[str, str]]]:
    placeholders: List[Tuple[Tuple[int, int], str]] = []

    def _placehold(m: re.Match[str]) -> str:
        start, end = m.span()
        placeholders.append(((start, end), m.group(0)))
        return "\ue000" * (end - start)

    masked = _CODE_BLOCK_RE.sub(_placehold, text)
    heads = list(_MD_HEADING_RE.finditer(masked))
    if not heads:
        return [(text, (0, len(text)), {"heading": "", "level": "0"})]

    sections: List[Tuple[int, int, str, str]] = []
    for i, h in enumerate(heads):
        start = h.start()
        level = str(len(h.group(1)))
        heading = h.group(2).strip()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(masked)
        sections.append((start, end, heading, level))

    result: List[Tuple[str, Tuple[int, int], Dict[str, str]]] = []
    for start, end, heading, level in sections:
        seg = text[start:end]
        result.append((seg, (start, end), {"heading": heading, "level": level}))
    return result


_SENT_END_RE = re.compile(r"(?<!\b[A-ZА-ЯЁ]\.)(?<=[\.\!\?])\s+(?=[A-ZА-ЯЁ])")


def _split_paragraphs(text: str) -> List[Tuple[str, Tuple[int, int]]]:
    parts: List[Tuple[str, Tuple[int, int]]] = []
    start = 0
    for block in text.split("\n\n"):
        s = start
        e = s + len(block)
        parts.append((block, (s, e)))
        start = e + 2
    return [p for p in parts if p[0].strip()]


def _split_sentences(block: str) -> List[str]:
    block = block.strip()
    if not block:
        return []
    if not re.search(r"[A-ZА-ЯЁ]", block):
        return re.split(r"(?<=[\.\!\?\;])\s+", block)
    parts = _SENT_END_RE.split(block)
    merged: List[str] = []
    buf = ""
    for p in parts:
        if not p:
            continue
        if len(p) < 40:
            buf = (buf + " " + p).strip() if buf else p
        else:
            if buf:
                merged.append(buf.strip())
                buf = ""
            merged.append(p.strip())
    if buf:
        merged.append(buf.strip())
    return merged


def _pack_by_tokens(frags: List[str], chunk_size: int, overlap: int) -> List[str]:
    chunks: List[str] = []
    cur_tokens: List[int] = []
    cur_texts: List[str] = []

    def flush() -> None:
        if not cur_texts:
            return
        text = " ".join(cur_texts).strip()
        if text:
            chunks.append(text)

    for frag in frags:
        toks = _encode(frag)
        if len(cur_tokens) + len(toks) <= chunk_size:
            cur_tokens.extend(toks)
            cur_texts.append(frag)
        else:
            flush()
            if overlap > 0 and cur_texts:
                last = cur_texts[-1]
                cur_tokens = _encode(last)
                cur_texts = [last]
            else:
                cur_tokens = []
                cur_texts = []
            cur_tokens.extend(toks)
            cur_texts.append(frag)

    flush()
    return chunks


def split_with_metadata(
    text: str,
    filename: Optional[str] = None,
    document_id: Optional[int] = None,
    chunk_size: int = 800,
    overlap: int = 120,
    strip_html: bool = True,
    markdown_aware: bool = True,
) -> List[Dict[str, Any]]:
    if not text or not isinstance(text, str):
        return []

    if strip_html:
        text = _strip_html(text)
    text = _normalize_ws(text)

    sections: List[Tuple[str, Tuple[int, int], Dict[str, str]]]
    sections = (
        _split_markdown_sections(text)
        if markdown_aware
        else [(text, (0, len(text)), {"heading": "", "level": "0"})]
    )

    all_chunks: List[Dict[str, Any]] = []
    for section_text, (s_start, s_end), meta in sections:
        paras = _split_paragraphs(section_text)
        sentences: List[str] = []
        for para, _ in paras:
            p = para.strip()
            if not p:
                continue
            if _MD_LIST_RE.search(p):
                for line in p.splitlines():
                    line = line.strip()
                    if line:
                        sentences.append(line)
            else:
                sentences.extend(_split_sentences(p))

        packed = _pack_by_tokens(sentences, chunk_size=chunk_size, overlap=overlap)
        for ch in packed:
            all_chunks.append(
                {
                    "text": ch,
                    "heading": meta.get("heading", ""),
                    "level": meta.get("level", "0"),
                    "span": [s_start, s_end],
                    "filename": filename or "",
                    "document_id": (int(document_id) if document_id is not None else None),
                }
            )

    cleaned = []
    for c in all_chunks:
        t = c["text"].strip()
        if not t:
            continue
        if len(t) < 50:
            continue
        c["text"] = t
        cleaned.append(c)

    return cleaned


def split_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
    strip_html: bool = True,
    markdown_aware: bool = True,
) -> List[str]:
    out = split_with_metadata(
        text=text,
        filename=None,
        document_id=None,
        chunk_size=chunk_size,
        overlap=overlap,
        strip_html=strip_html,
        markdown_aware=markdown_aware,
    )
    return [c["text"] for c in out]
