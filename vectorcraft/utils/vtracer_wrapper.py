"""
VTracer wrapper that provides fallback mechanisms for vtracer access.
This ensures vtracer functionality even if the Python package isn't installed.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

class VTracerWrapper:
    """Wrapper for VTracer that can use either Python package or local binary"""
    
    def __init__(self):
        self.python_vtracer = None
        self.binary_path = None
        self._init_vtracer()
    
    def _init_vtracer(self):
        """Initialize vtracer - try Python package first, then local binary"""
        # Try Python package first
        try:
            import vtracer
            self.python_vtracer = vtracer
            print("✅ Using Python vtracer package")
            return
        except ImportError:
            pass
        
        # Try local binary as fallback
        current_dir = Path(__file__).parent.parent.parent
        binary_path = current_dir / "vtracer_binary"
        
        if binary_path.exists() and os.access(binary_path, os.X_OK):
            self.binary_path = str(binary_path)
            print(f"✅ Using local vtracer binary: {self.binary_path}")
            return
        
        # Try system vtracer
        try:
            result = subprocess.run(['vtracer', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.binary_path = 'vtracer'
                print("✅ Using system vtracer binary")
                return
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        print("⚠️  VTracer not available - some features may be limited")
    
    def is_available(self) -> bool:
        """Check if vtracer is available"""
        return self.python_vtracer is not None or self.binary_path is not None
    
    def convert_image_to_svg_py(self, image_path: str, **kwargs) -> Optional[str]:
        """Convert image to SVG using Python package"""
        if self.python_vtracer:
            try:
                return self.python_vtracer.convert_image_to_svg_py(image_path, **kwargs)
            except Exception as e:
                print(f"Python vtracer conversion failed: {e}")
                return None
        return None
    
    def convert_image_to_svg_binary(self, image_path: str, output_path: Optional[str] = None, **kwargs) -> Optional[str]:
        """Convert image to SVG using binary"""
        if not self.binary_path:
            return None
        
        try:
            # Create temporary output file if not specified
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(suffix='.svg', delete=False)
                output_path = temp_file.name
                temp_file.close()
            
            # Build command
            cmd = [self.binary_path, '--input', image_path, '--output', output_path]
            
            # Add parameters
            if 'color_precision' in kwargs:
                cmd.extend(['--color_precision', str(kwargs['color_precision'])])
            if 'filter_speckle' in kwargs:
                cmd.extend(['--filter_speckle', str(kwargs['filter_speckle'])])
            if 'corner_threshold' in kwargs:
                cmd.extend(['--corner_threshold', str(kwargs['corner_threshold'])])
            if 'segment_length' in kwargs:
                cmd.extend(['--segment_length', str(kwargs['segment_length'])])
            if 'mode' in kwargs:
                cmd.extend(['--mode', kwargs['mode']])
            
            # Run conversion
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Read the SVG content
                with open(output_path, 'r') as f:
                    svg_content = f.read()
                
                # Clean up temp file
                if output_path.startswith(tempfile.gettempdir()):
                    os.unlink(output_path)
                
                return svg_content
            else:
                print(f"Binary vtracer conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Binary vtracer conversion error: {e}")
            return None
    
    def convert(self, image_path: str, **kwargs) -> Optional[str]:
        """Convert image to SVG using best available method"""
        # Try Python package first
        result = self.convert_image_to_svg_py(image_path, **kwargs)
        if result:
            return result
        
        # Fallback to binary
        return self.convert_image_to_svg_binary(image_path, **kwargs)

# Global instance
vtracer_wrapper = VTracerWrapper()