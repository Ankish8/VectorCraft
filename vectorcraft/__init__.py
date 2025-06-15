"""
VectorCraft 2.0 - Next-Generation Vector Conversion
"""

from .core.hybrid_vectorizer import HybridVectorizer
from .core.optimized_vectorizer import OptimizedVectorizer
from .core.svg_builder import SVGBuilder
from .utils.image_processor import ImageProcessor

__version__ = "2.0.0"
__all__ = ["HybridVectorizer", "OptimizedVectorizer", "SVGBuilder", "ImageProcessor"]