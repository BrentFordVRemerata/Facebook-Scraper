"""
Post Parser and Text Processing Module
======================================
Provides clean, deterministic extraction and hashing of post text blocks
extracted from Facebook page DOMs.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set


DEFAULT_SKIP_WORDS = [
    'Like', 'Comment', 'Share', 'Follow', 'Following', 'Message',
    'See more', 'View more', 'Write a comment', 'Log In', 'Sign Up',
    'Privacy', 'Terms', 'Advertising', 'Ad Choices', 'Cookies',
    'More', 'Meta ©', 'About', 'Photos', 'Videos', 'Events',
    'Posts', 'Community', 'Reviews', 'Number of unread notifications'
]


def normalize_whitespace(text: str) -> str:
    """Normalize irregular whitespace, carriage returns, and blank lines."""
    if not text:
        return ""
    # Standardize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Collapse multiple blank lines to at most two
    lines = [line.strip() for line in text.split('\n')]
    return '\n'.join(lines)


def extract_text_blocks(raw_text: str, min_line_len: int = 10, min_block_len: int = 80) -> List[str]:
    """
    Extract meaningful text blocks from raw body text.
    
    Accumulates lines longer than `min_line_len` into contiguous blocks.
    When a short line or empty line is encountered, the accumulated block
    is finalized if its total length meets `min_block_len`.
    
    Trailing blocks at the end of the text stream are properly preserved.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []
    
    normalized = normalize_whitespace(raw_text)
    lines = normalized.split('\n')
    
    blocks: List[str] = []
    current_block: List[str] = []
    
    for line in lines:
        line_clean = line.strip()
        if len(line_clean) >= min_line_len:
            current_block.append(line_clean)
        else:
            if current_block:
                block_text = '\n'.join(current_block)
                if len(block_text) >= min_block_len:
                    blocks.append(block_text)
                current_block = []
                
    # Flush any remaining block at the end of the stream
    if current_block:
        block_text = '\n'.join(current_block)
        if len(block_text) >= min_block_len:
            blocks.append(block_text)
            
    return blocks


def is_ignorable_block(block: str, skip_words: Optional[List[str]] = None) -> bool:
    """
    Check if a text block contains Facebook UI chrome or boilerplate.
    """
    if not block:
        return True
    
    words = skip_words if skip_words is not None else DEFAULT_SKIP_WORDS
    first_line = block.split('\n')[0].strip()
    
    # Check if the block starts with or strictly matches any skip word
    for word in words:
        if first_line.startswith(word) or first_line == word:
            return True
            
    return False


def generate_content_hash(text: str) -> str:
    """
    Generate SHA-256 hex digest of the normalized text content.
    
    Using SHA-256 over the entire text prevents hash collisions that occurred
    when hashing only the first 100 characters of posts sharing identical headers.
    """
    normalized = re.sub(r'\s+', ' ', text.strip()).encode('utf-8')
    return hashlib.sha256(normalized).hexdigest()


def generate_post_id(source_id: str, content_hash: str) -> str:
    """Generate a clean deterministic post ID from source and content hash."""
    clean_source = re.sub(r'[^a-zA-Z0-9_-]', '_', source_id)
    return f"{clean_source}_{content_hash[:12]}"


def extract_title_from_block(block: str, max_length: int = 80) -> str:
    """
    Derive a concise title from the first non-empty line of the text block.
    """
    lines = [l.strip() for l in block.split('\n') if l.strip()]
    if not lines:
        return "Untitled Announcement"
    first_line = lines[0]
    if len(first_line) <= max_length:
        return first_line
    return first_line[:max_length].rstrip() + "..."


def generate_legacy_post_id(source_id: str, block: str) -> str:
    """
    Generate historical 8-character MD5 post ID (used in original Feb 2026 prototype).
    Maintained for database migration checks and backwards compatibility.
    """
    clean_source = re.sub(r'[^a-zA-Z0-9_-]', '_', source_id)
    legacy_hash = hashlib.md5(block[:100].encode('utf-8')).hexdigest()[:8]
    return f"{clean_source}_{legacy_hash}"


def build_post_record(
    source_id: str,
    source_name: str,
    block: str,
    scraped_at: Optional[str] = None
) -> Dict:
    """
    Construct a standardized post dictionary.
    """
    content_hash = generate_content_hash(block)
    post_id = generate_post_id(source_id, content_hash)
    legacy_post_id = generate_legacy_post_id(source_id, block)
    title = extract_title_from_block(block)
    timestamp = scraped_at or datetime.now(timezone.utc).isoformat()
    
    return {
        "post_id": post_id,
        "legacy_post_id": legacy_post_id,
        "source_id": source_id,
        "source_name": source_name or source_id,
        "title": title,
        "text": block[:4000],
        "body": block[:4000],  # Schema alias for backwards compatibility
        "scraped_at": timestamp,
        "content_hash": content_hash,
    }


def parse_posts_from_text(
    raw_text: str,
    source_id: str,
    source_name: str = "",
    max_posts: int = 10,
    min_line_len: int = 10,
    min_block_len: int = 80,
    skip_words: Optional[List[str]] = None
) -> List[Dict]:
    """
    Parse posts from raw text stream with deduplication and limit constraints.
    """
    display_name = source_name or source_id
    blocks = extract_text_blocks(raw_text, min_line_len=min_line_len, min_block_len=min_block_len)
    
    posts: List[Dict] = []
    seen_hashes: Set[str] = set()
    
    for block in blocks:
        if len(posts) >= max_posts:
            break
        
        if is_ignorable_block(block, skip_words=skip_words):
            continue
            
        content_hash = generate_content_hash(block)
        if content_hash in seen_hashes:
            continue
            
        seen_hashes.add(content_hash)
        post = build_post_record(
            source_id=source_id,
            source_name=display_name,
            block=block
        )
        posts.append(post)
        
    return posts
