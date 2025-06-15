import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import List, Tuple, Optional, Dict
import cv2
import torch.nn.functional as F

class BezierCurve(nn.Module):
    def __init__(self, control_points: List[Tuple[float, float]]):
        super().__init__()
        points_tensor = torch.tensor(control_points, dtype=torch.float32, requires_grad=True)
        self.control_points = nn.Parameter(points_tensor)
        
    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """Evaluate Bezier curve at parameter t"""
        n = len(self.control_points) - 1
        result = torch.zeros_like(t.unsqueeze(-1).expand(-1, 2))
        
        for i in range(n + 1):
            # Binomial coefficient
            binom_coeff = self._binomial_coefficient(n, i)
            # Bernstein polynomial
            bernstein = binom_coeff * (t ** i) * ((1 - t) ** (n - i))
            result += bernstein.unsqueeze(-1) * self.control_points[i]
        
        return result
    
    def _binomial_coefficient(self, n: int, k: int) -> float:
        """Calculate binomial coefficient n choose k"""
        if k > n - k:
            k = n - k
        
        result = 1
        for i in range(k):
            result = result * (n - i) // (i + 1)
        return float(result)

class VectorPath(nn.Module):
    def __init__(self, initial_paths: List[List[Tuple[float, float]]], 
                 colors: List[Tuple[float, float, float]]):
        super().__init__()
        
        self.curves = nn.ModuleList()
        self.colors = []
        
        for path, color in zip(initial_paths, colors):
            if len(path) >= 4:
                # Create Bezier curve
                self.curves.append(BezierCurve(path))
                self.colors.append(torch.tensor(color, dtype=torch.float32))
            elif len(path) >= 2:
                # Simple line - extend to 4 points for Bezier
                extended_path = self._extend_to_bezier(path)
                self.curves.append(BezierCurve(extended_path))
                self.colors.append(torch.tensor(color, dtype=torch.float32))
    
    def _extend_to_bezier(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Extend simple path to Bezier control points"""
        if len(path) == 2:
            start, end = path
            # Create control points that approximate a straight line
            control1 = (start[0] + (end[0] - start[0]) / 3, start[1] + (end[1] - start[1]) / 3)
            control2 = (start[0] + 2 * (end[0] - start[0]) / 3, start[1] + 2 * (end[1] - start[1]) / 3)
            return [start, control1, control2, end]
        elif len(path) == 3:
            # Add one more control point
            return path + [path[-1]]
        else:
            return path[:4]  # Take first 4 points
    
    def render(self, width: int, height: int, samples_per_curve: int = 100) -> torch.Tensor:
        """Render vector paths to raster image"""
        image = torch.zeros((height, width, 3), dtype=torch.float32)
        
        for curve, color in zip(self.curves, self.colors):
            # Sample points along curve
            t = torch.linspace(0, 1, samples_per_curve)
            points = curve(t)
            
            # Rasterize curve (simplified - just plot points)
            for point in points:
                x, y = int(point[0].item()), int(point[1].item())
                if 0 <= x < width and 0 <= y < height:
                    image[y, x] = color
        
        return image

class DifferentiableOptimizer:
    def __init__(self, learning_rate: float = 0.01, max_iterations: int = 100):
        self.learning_rate = learning_rate
        self.max_iterations = max_iterations
        
    def optimize_paths(self, target_image: np.ndarray, 
                      initial_paths: List[List[Tuple[float, float]]],
                      colors: List[Tuple[float, float, float]]) -> List[List[Tuple[float, float]]]:
        """Optimize vector paths to match target image"""
        
        # Convert target to torch tensor
        target_tensor = torch.tensor(target_image[:, :, :3], dtype=torch.float32)
        height, width = target_tensor.shape[:2]
        
        # Create vector path model
        vector_model = VectorPath(initial_paths, colors)
        
        # Optimizer
        optimizer = optim.Adam(vector_model.parameters(), lr=self.learning_rate)
        
        # Loss function (perceptual loss)
        criterion = self._create_perceptual_loss()
        
        best_loss = float('inf')
        best_paths = initial_paths.copy()
        
        for iteration in range(self.max_iterations):
            optimizer.zero_grad()
            
            # Render current paths
            rendered = vector_model.render(width, height)
            
            # Calculate loss
            loss = criterion(rendered, target_tensor)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            # Track best result
            if loss.item() < best_loss:
                best_loss = loss.item()
                best_paths = self._extract_paths(vector_model)
            
            # Early stopping if converged
            if iteration > 10 and loss.item() > best_loss * 1.1:
                break
                
        return best_paths
    
    def _create_perceptual_loss(self) -> nn.Module:
        """Create advanced perceptual loss function for higher similarity"""
        class AdvancedPerceptualLoss(nn.Module):
            def __init__(self):
                super().__init__()
                self.mse = nn.MSELoss()
                self.l1 = nn.L1Loss()
                
            def forward(self, rendered: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
                # Multi-scale perceptual loss
                total_loss = 0.0
                
                # Original scale
                mse_loss = self.mse(rendered, target)
                l1_loss = self.l1(rendered, target)
                total_loss += 0.7 * mse_loss + 0.3 * l1_loss
                
                # Edge preservation with proper Sobel filtering
                rendered_edges = self._compute_edges_proper(rendered)
                target_edges = self._compute_edges_proper(target)
                edge_loss = self.mse(rendered_edges, target_edges)
                total_loss += 0.8 * edge_loss
                
                # Color distribution loss
                color_loss = self._color_distribution_loss(rendered, target)
                total_loss += 0.4 * color_loss
                
                # Structural similarity component
                structural_loss = self._structural_similarity_loss(rendered, target)
                total_loss += 0.6 * structural_loss
                
                return total_loss
            
            def _compute_edges_proper(self, image: torch.Tensor) -> torch.Tensor:
                """Compute edge map using proper Sobel filters"""
                # Convert to grayscale
                if len(image.shape) == 3 and image.shape[-1] == 3:
                    gray = torch.mean(image, dim=-1, keepdim=True)
                else:
                    gray = image
                
                # Ensure proper dimensions for conv2d: [batch, channel, height, width]
                if len(gray.shape) == 3:
                    gray = gray.permute(2, 0, 1).unsqueeze(0)  # [1, 1, H, W]
                
                # Sobel kernels
                sobel_x = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], 
                                     dtype=torch.float32, device=gray.device).unsqueeze(0).unsqueeze(0)
                sobel_y = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], 
                                     dtype=torch.float32, device=gray.device).unsqueeze(0).unsqueeze(0)
                
                # Apply convolution with padding
                edge_x = F.conv2d(gray, sobel_x, padding=1)
                edge_y = F.conv2d(gray, sobel_y, padding=1)
                
                # Compute edge magnitude
                edges = torch.sqrt(edge_x**2 + edge_y**2)
                
                # Return in original format
                return edges.squeeze(0).permute(1, 2, 0)
            
            def _color_distribution_loss(self, rendered: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
                """Loss based on color distribution similarity"""
                # Compute color histograms (simplified)
                rendered_mean = torch.mean(rendered, dim=(0, 1))
                target_mean = torch.mean(target, dim=(0, 1))
                
                rendered_std = torch.std(rendered, dim=(0, 1))
                target_std = torch.std(target, dim=(0, 1))
                
                mean_loss = self.mse(rendered_mean, target_mean)
                std_loss = self.mse(rendered_std, target_std)
                
                return mean_loss + std_loss
            
            def _structural_similarity_loss(self, rendered: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
                """Simplified structural similarity loss"""
                # Compute local means using average pooling
                kernel_size = 11
                padding = kernel_size // 2
                
                # Ensure proper dimensions
                if len(rendered.shape) == 3:
                    rendered_batch = rendered.permute(2, 0, 1).unsqueeze(0)  # [1, C, H, W]
                    target_batch = target.permute(2, 0, 1).unsqueeze(0)
                else:
                    rendered_batch = rendered.unsqueeze(0).unsqueeze(0)
                    target_batch = target.unsqueeze(0).unsqueeze(0)
                
                # Local means
                mu1 = F.avg_pool2d(rendered_batch, kernel_size, stride=1, padding=padding)
                mu2 = F.avg_pool2d(target_batch, kernel_size, stride=1, padding=padding)
                
                # Local variances and covariance
                mu1_sq = mu1 * mu1
                mu2_sq = mu2 * mu2
                mu1_mu2 = mu1 * mu2
                
                sigma1_sq = F.avg_pool2d(rendered_batch * rendered_batch, kernel_size, stride=1, padding=padding) - mu1_sq
                sigma2_sq = F.avg_pool2d(target_batch * target_batch, kernel_size, stride=1, padding=padding) - mu2_sq
                sigma12 = F.avg_pool2d(rendered_batch * target_batch, kernel_size, stride=1, padding=padding) - mu1_mu2
                
                # SSIM constants
                C1 = 0.01 ** 2
                C2 = 0.03 ** 2
                
                # SSIM formula
                numerator = (2 * mu1_mu2 + C1) * (2 * sigma12 + C2)
                denominator = (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
                
                ssim_map = numerator / (denominator + 1e-8)
                ssim_loss = 1.0 - torch.mean(ssim_map)
                
                return ssim_loss
        
        return AdvancedPerceptualLoss()
    
    def _extract_paths(self, vector_model: VectorPath) -> List[List[Tuple[float, float]]]:
        """Extract current path coordinates from model"""
        paths = []
        for curve in vector_model.curves:
            control_points = curve.control_points.detach().numpy()
            path = [(float(p[0]), float(p[1])) for p in control_points]
            paths.append(path)
        return paths
    
    def refine_single_path(self, path: List[Tuple[float, float]], 
                          target_region: np.ndarray, color: Tuple[float, float, float]) -> List[Tuple[float, float]]:
        """Refine a single path to better match a target region"""
        
        if len(path) < 2:
            return path
            
        # Create simple model for single path
        single_curve = BezierCurve(path)
        optimizer = optim.Adam(single_curve.parameters(), lr=self.learning_rate * 2)
        
        target_tensor = torch.tensor(target_region, dtype=torch.float32)
        height, width = target_tensor.shape[:2]
        
        best_path = path.copy()
        best_loss = float('inf')
        
        for _ in range(min(50, self.max_iterations)):
            optimizer.zero_grad()
            
            # Sample points along curve
            t = torch.linspace(0, 1, 50)
            points = single_curve(t)
            
            # Simple loss: how well curve points match target region
            loss = self._path_region_loss(points, target_tensor)
            
            if loss.item() < best_loss:
                best_loss = loss.item()
                best_path = [(float(p[0]), float(p[1])) for p in single_curve.control_points.detach().numpy()]
            
            loss.backward()
            optimizer.step()
        
        return best_path
    
    def _path_region_loss(self, points: torch.Tensor, target_region: torch.Tensor) -> torch.Tensor:
        """Calculate how well path points align with target region"""
        height, width = target_region.shape[:2]
        loss = 0.0
        valid_points = 0
        
        for point in points:
            x, y = point[0], point[1]
            if 0 <= x < width and 0 <= y < height:
                # Sample target value at point location
                x_int, y_int = int(x), int(y)
                target_val = target_region[y_int, x_int] if len(target_region.shape) == 2 else torch.mean(target_region[y_int, x_int])
                
                # Loss is inverse of target value (higher target value = lower loss)
                loss += (1.0 - target_val)
                valid_points += 1
        
        return loss / max(1, valid_points)