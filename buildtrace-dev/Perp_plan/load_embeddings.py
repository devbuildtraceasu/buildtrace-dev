#!/usr/bin/env python3
"""Load embeddings from disk and perform retrieval"""

import json
from pathlib import Path
from typing import List, Dict, Any

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(y * y for y in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a * mag_b else 0.0

def load_embeddings(embeddings_path: Path) -> List[Dict[str, Any]]:
    """Load full embeddings from JSON file"""
    if not embeddings_path.exists():
        raise FileNotFoundError(f"Embeddings file not found: {embeddings_path}")
    with open(embeddings_path, 'r') as f:
        return json.load(f)

def query_embeddings(query_embedding: List[float], embeddings: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """Query embeddings and return top K most similar"""
    similarities = []
    for emb in embeddings:
        sim = cosine_similarity(query_embedding, emb["embedding"])
        similarities.append((sim, emb))
    similarities.sort(reverse=True, key=lambda x: x[0])
    return [{"similarity": float(sim), **emb} for sim, emb in similarities[:top_k]]

if __name__ == "__main__":
    import sys
    embeddings_path = Path("Perp_plan/output/embeddings_full.json")
    if len(sys.argv) > 1:
        embeddings_path = Path(sys.argv[1])
    
    print(f"Loading embeddings from {embeddings_path}...")
    embeddings = load_embeddings(embeddings_path)
    print(f"✓ Loaded {len(embeddings)} embeddings")
    
    for i, emb in enumerate(embeddings[:3], 1):
        print(f"\n{i}. {emb['object_type']}: {emb['description'][:80]}...")
        print(f"   Vector dim: {len(emb['embedding'])}")
        print(f"   Metadata: {emb['metadata']}")
