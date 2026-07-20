"""
Enhanced Feature Extractor for ABYSS
=====================================
Adds additional features on top of EMBER's 2381:
- Byte n-grams (hashed to 256 dims)
- Import hash (imphash) 
- Section entropy statistics
- Rich header hash
- TLS callback count
- Certificate table info
- Overlay size/entropy
"""

import hashlib
import numpy as np
from pathlib import Path
from collections import Counter
import struct

try:
    import lief
    HAS_LIEF = True
except ImportError:
    HAS_LIEF = False

try:
    import pefile
    HAS_PEFILE = True
except ImportError:
    HAS_PEFILE = False


def compute_entropy(data: bytes) -> float:
    """Compute Shannon entropy of byte sequence."""
    if not data:
        return 0.0
    freq = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    prob = freq / len(data)
    prob = prob[prob > 0]
    return float(-np.sum(prob * np.log2(prob)))


def extract_byte_ngrams(data: bytes, n: int = 2, dim: int = 256) -> np.ndarray:
    """
    Extract byte n-grams using feature hashing.
    Uses xxhash for fast hashing.
    """
    if len(data) < n:
        return np.zeros(dim, dtype=np.float32)
    
    # Use a simple rolling hash for speed
    hashes = []
    for i in range(len(data) - n + 1):
        chunk = data[i:i+n]
        h = hash(chunk) % dim
        hashes.append(h)
    
    # Count frequencies
    counts = np.bincount(hashes, minlength=dim).astype(np.float32)
    total = counts.sum()
    if total > 0:
        counts = counts / total
    return counts


def extract_imphash(file_path: Path) -> str:
    """Compute import hash (imphash) - hash of sorted imported function names."""
    if not HAS_PEFILE:
        return ""
    try:
        pe = pefile.PE(str(file_path))
        imports = []
        if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
            for entry in pe.DIRECTORY_ENTRY_IMPORT:
                dll_name = entry.dll.decode("utf-8", errors="replace").lower()
                for imp in entry.imports:
                    if imp.name:
                        func_name = imp.name.decode("utf-8", errors="replace")
                        imports.append(f"{dll_name}:{func_name}")
        pe.close()
        
        if imports:
            imports.sort()
            imphash_str = ",".join(imports)
            return hashlib.md5(imphash_str.encode()).hexdigest()
    except Exception:
        pass
    return ""


def extract_section_features(file_path: Path) -> dict:
    """Extract detailed section statistics."""
    if not HAS_PEFILE:
        return {}
    
    try:
        pe = pefile.PE(str(file_path))
        entropies = []
        sizes = []
        names = []
        
        for section in pe.sections:
            name = section.Name.decode("utf-8", errors="replace").strip("\x00")
            names.append(name)
            data = section.get_data()
            sizes.append(len(data))
            entropies.append(compute_entropy(data))
        
        pe.close()
        
        if entropies:
            return {
                "section_count": len(entropies),
                "section_names": names,
                "section_sizes": sizes,
                "section_entropies": entropies,
                "entropy_min": float(np.min(entropies)),
                "entropy_max": float(np.max(entropies)),
                "entropy_mean": float(np.mean(entropies)),
                "entropy_std": float(np.std(entropies)),
                "size_min": int(np.min(sizes)),
                "size_max": int(np.max(sizes)),
                "size_mean": float(np.mean(sizes)),
            }
    except Exception:
        pass
    return {}


def extract_rich_header(file_path: Path) -> str:
    """Extract and hash the Rich header (compiler/linker info)."""
    if not HAS_PEFILE:
        return ""
    try:
        pe = pefile.PE(str(file_path))
        rich_data = pe.parse_rich_header()
        pe.close()
        if rich_data:
            return hashlib.md5(str(rich_data).encode()).hexdigest()
    except Exception:
        pass
    return ""


def extract_overlay_features(file_path: Path) -> dict:
    """Extract overlay (appended data) features."""
    result = {
        "overlay_size": 0,
        "overlay_entropy": 0.0,
        "has_overlay": False,
    }
    
    if not HAS_LIEF:
        return result
    
    try:
        binary = lief.parse(str(file_path))
        if binary and hasattr(binary, "overlay"):
            overlay = bytes(binary.overlay)
            result["overlay_size"] = len(overlay)
            result["has_overlay"] = len(overlay) > 0
            if overlay:
                result["overlay_entropy"] = compute_entropy(overlay)
    except Exception:
        pass
    return result


def extract_tls_features(file_path: Path) -> dict:
    """Extract TLS callback features."""
    result = {
        "tls_callback_count": 0,
        "tls_callbacks": [],
    }
    
    if not HAS_LIEF:
        return result
    
    try:
        binary = lief.parse(str(file_path))
        if binary and binary.has_tls:
            cbs = list(binary.tls.callbacks)
            result["tls_callback_count"] = len(cbs)
            result["tls_callbacks"] = [hex(cb) for cb in cbs]
    except Exception:
        pass
    return result


def extract_certificate_features(file_path: Path) -> dict:
    """Extract certificate table features."""
    result = {
        "has_certificate": False,
        "cert_count": 0,
        "cert_sizes": [],
    }
    
    if not HAS_LIEF:
        return result
    
    try:
        binary = lief.parse(str(file_path))
        if binary and hasattr(binary, "signatures"):
            sigs = list(binary.signatures)
            result["has_certificate"] = len(sigs) > 0
            result["cert_count"] = len(sigs)
            for sig in sigs:
                # Get certificate size if available
                try:
                    result["cert_sizes"].append(len(sig.content))
                except Exception:
                    pass
    except Exception:
        pass
    return result


def extract_all_enhanced_features(file_path: Path) -> np.ndarray:
    """
    Extract all enhanced features and return as concatenated vector.
    Expected output dimensions:
    - byte_2grams: 256
    - byte_3grams: 256
    - section_entropy_stats: 8 (count, min, max, mean, std, size_min, size_max, size_mean)
    - overlay: 3 (size, entropy, has_overlay)
    - tls: 1 (callback_count)
    - cert: 2 (has_cert, cert_count)
    - imphash: 1 (hashed to single float via md5)
    - rich_header: 1 (hashed to single float via md5)
    Total: ~536 features
    """
    with open(file_path, "rb") as f:
        data = f.read()
    
    # Byte n-grams
    bigrams = extract_byte_ngrams(data, n=2, dim=256)
    trigrams = extract_byte_ngrams(data, n=3, dim=256)
    
    # Section features
    section_feat = extract_section_features(file_path)
    section_vec = np.zeros(8, dtype=np.float32)
    if section_feat:
        section_vec[0] = section_feat.get("section_count", 0) / 20.0  # normalize
        section_vec[1] = section_feat.get("entropy_min", 0) / 8.0
        section_vec[2] = section_feat.get("entropy_max", 0) / 8.0
        section_vec[3] = section_feat.get("entropy_mean", 0) / 8.0
        section_vec[4] = section_feat.get("entropy_std", 0) / 8.0
        section_vec[5] = section_feat.get("size_min", 0) / 1e6
        section_vec[6] = section_feat.get("size_max", 0) / 1e6
        section_vec[7] = section_feat.get("size_mean", 0) / 1e6
    
    # Overlay features
    overlay_feat = extract_overlay_features(file_path)
    overlay_vec = np.array([
        min(overlay_feat.get("overlay_size", 0) / 1e6, 1.0),
        overlay_feat.get("overlay_entropy", 0) / 8.0,
        float(overlay_feat.get("has_overlay", False)),
    ], dtype=np.float32)
    
    # TLS features
    tls_feat = extract_tls_features(file_path)
    tls_vec = np.array([
        min(tls_feat.get("tls_callback_count", 0) / 10.0, 1.0),
    ], dtype=np.float32)
    
    # Certificate features
    cert_feat = extract_certificate_features(file_path)
    cert_vec = np.array([
        float(cert_feat.get("has_certificate", False)),
        min(cert_feat.get("cert_count", 0) / 5.0, 1.0),
    ], dtype=np.float32)
    
    # Imphash (hash to single float)
    imphash = extract_imphash(file_path)
    imphash_vec = np.array([
        float(int(imphash[:8], 16) % 1000000) / 1000000.0 if imphash else 0.0
    ], dtype=np.float32)
    
    # Rich header
    rich_hash = extract_rich_header(file_path)
    rich_vec = np.array([
        float(int(rich_hash[:8], 16) % 1000000) / 1000000.0 if rich_hash else 0.0
    ], dtype=np.float32)
    
    # Concatenate all
    features = np.concatenate([
        bigrams,           # 256
        trigrams,          # 256
        section_vec,       # 8
        overlay_vec,       # 3
        tls_vec,           # 1
        cert_vec,          # 2
        imphash_vec,       # 1
        rich_vec,          # 1
    ])
    
    return features.astype(np.float32)


def get_enhanced_feature_names() -> list:
    """Return names for the enhanced features."""
    names = []
    names += [f"byte_bigram_{i}" for i in range(256)]
    names += [f"byte_trigram_{i}" for i in range(256)]
    names += [
        "section_count_norm", "section_entropy_min", "section_entropy_max",
        "section_entropy_mean", "section_entropy_std", "section_size_min",
        "section_size_max", "section_size_mean"
    ]
    names += ["overlay_size_norm", "overlay_entropy", "has_overlay"]
    names += ["tls_callback_count_norm"]
    names += ["has_certificate", "cert_count_norm"]
    names += ["imphash_hash"]
    names += ["rich_header_hash"]
    return names


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        f = Path(sys.argv[1])
        if f.exists():
            feat = extract_all_enhanced_features(f)
            print(f"Feature vector shape: {feat.shape}")
            print(f"Feature names count: {len(get_enhanced_feature_names())}")
            print(f"Sample values: {feat[:10]}")
            names = get_enhanced_feature_names()
            for i, (n, v) in enumerate(zip(names, feat)):
                if v != 0:
                    print(f"  {n}: {v:.4f}")
        else:
            print(f"File not found: {f}")