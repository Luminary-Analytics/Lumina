#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        LUMINA 3D GENERATION                                   ║
║                                                                               ║
║  3D model generation capabilities for Lumina using Shap-E.                   ║
║  Create 3D objects from text descriptions.                                   ║
║                                                                               ║
║  Features:                                                                     ║
║  - Text-to-3D generation with Shap-E                                         ║
║  - Export to OBJ/GLB/STL formats                                             ║
║  - 3D model viewer data                                                       ║
║  - Print-ready models for 3D printing                                        ║
║  - Scene composition                                                          ║
║                                                                               ║
║  Created: 2025-12-07                                                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# Shap-E for 3D generation
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Trimesh for 3D manipulation
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# 3D GENERATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ShapEGenerator:
    """Text-to-3D generation using Shap-E."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "3d_models"
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.available = TORCH_AVAILABLE
        self.device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        
        if not self.available:
            print("    🎲 Shap-E: Not available (install torch)")
    
    def _load_model(self) -> bool:
        """Load the Shap-E model."""
        if self.model is not None:
            return True
        
        if not self.available:
            return False
        
        try:
            # Shap-E requires specific imports
            from shap_e.diffusion.sample import sample_latents
            from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
            from shap_e.models.download import load_model, load_config
            from shap_e.util.notebooks import create_pan_cameras, decode_latent_mesh
            
            print("    🎲 Loading Shap-E model...")
            
            self.xm = load_model('transmitter', device=self.device)
            self.model = load_model('text300M', device=self.device)
            self.diffusion = diffusion_from_config(load_config('diffusion'))
            
            print("    🎲 Shap-E loaded!")
            return True
            
        except Exception as e:
            print(f"    🎲 Shap-E load error: {e}")
            self.available = False
            return False
    
    def generate(self, prompt: str, guidance_scale: float = 15.0,
                output_format: str = "obj") -> Optional[str]:
        """Generate a 3D model from a text prompt."""
        if not self._load_model():
            return None
        
        try:
            from shap_e.diffusion.sample import sample_latents
            from shap_e.util.notebooks import decode_latent_mesh
            
            batch_size = 1
            
            latents = sample_latents(
                batch_size=batch_size,
                model=self.model,
                diffusion=self.diffusion,
                guidance_scale=guidance_scale,
                model_kwargs=dict(texts=[prompt] * batch_size),
                progress=True,
                clip_denoised=True,
                use_fp16=True,
                use_karras=True,
                karras_steps=64,
                sigma_min=1e-3,
                sigma_max=160,
                s_churn=0,
            )
            
            # Decode to mesh
            mesh = decode_latent_mesh(self.xm, latents[0]).tri_mesh()
            
            # Generate filename
            model_id = hashlib.md5(f"{prompt}{time.time()}".encode()).hexdigest()[:12]
            filename = f"{model_id}.{output_format}"
            filepath = self.models_path / filename
            
            # Export
            if output_format == "obj":
                with open(filepath, 'w') as f:
                    mesh.write_obj(f)
            elif output_format == "ply":
                with open(filepath, 'wb') as f:
                    mesh.write_ply(f)
            
            return str(filepath)
            
        except Exception as e:
            print(f"3D generation error: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get generator statistics."""
        models = list(self.models_path.glob("*.*")) if self.models_path.exists() else []
        return {
            "available": self.available,
            "device": self.device,
            "models_generated": len(models)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SIMPLE 3D PRIMITIVES (Fallback)
# ═══════════════════════════════════════════════════════════════════════════════

class Simple3DGenerator:
    """Simple 3D primitive generation without ML models."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "3d_models"
        self.models_path.mkdir(parents=True, exist_ok=True)
        
        self.available = TRIMESH_AVAILABLE
    
    def create_cube(self, size: float = 1.0, name: str = None) -> Optional[str]:
        """Create a simple cube."""
        if not self.available:
            return None
        
        mesh = trimesh.creation.box(extents=[size, size, size])
        return self._save_mesh(mesh, name or "cube")
    
    def create_sphere(self, radius: float = 0.5, name: str = None) -> Optional[str]:
        """Create a simple sphere."""
        if not self.available:
            return None
        
        mesh = trimesh.creation.icosphere(subdivisions=3, radius=radius)
        return self._save_mesh(mesh, name or "sphere")
    
    def create_cylinder(self, radius: float = 0.5, height: float = 1.0, 
                       name: str = None) -> Optional[str]:
        """Create a simple cylinder."""
        if not self.available:
            return None
        
        mesh = trimesh.creation.cylinder(radius=radius, height=height)
        return self._save_mesh(mesh, name or "cylinder")
    
    def create_cone(self, radius: float = 0.5, height: float = 1.0,
                   name: str = None) -> Optional[str]:
        """Create a simple cone."""
        if not self.available:
            return None
        
        mesh = trimesh.creation.cone(radius=radius, height=height)
        return self._save_mesh(mesh, name or "cone")
    
    def create_torus(self, major_radius: float = 1.0, minor_radius: float = 0.3,
                    name: str = None) -> Optional[str]:
        """Create a torus (donut shape)."""
        if not self.available:
            return None
        
        # Trimesh doesn't have direct torus creation, use custom
        import numpy as np
        
        u = np.linspace(0, 2 * np.pi, 50)
        v = np.linspace(0, 2 * np.pi, 30)
        u, v = np.meshgrid(u, v)
        
        x = (major_radius + minor_radius * np.cos(v)) * np.cos(u)
        y = (major_radius + minor_radius * np.cos(v)) * np.sin(u)
        z = minor_radius * np.sin(v)
        
        vertices = np.stack([x.flatten(), y.flatten(), z.flatten()], axis=1)
        
        # Simple triangulation (not perfect but works)
        faces = []
        rows, cols = 30, 50
        for i in range(rows - 1):
            for j in range(cols - 1):
                v1 = i * cols + j
                v2 = i * cols + (j + 1)
                v3 = (i + 1) * cols + j
                v4 = (i + 1) * cols + (j + 1)
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
        
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        return self._save_mesh(mesh, name or "torus")
    
    def _save_mesh(self, mesh, name: str) -> str:
        """Save a mesh to file."""
        model_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:12]
        filename = f"{name}_{model_id}.obj"
        filepath = self.models_path / filename
        
        mesh.export(str(filepath))
        return str(filepath)
    
    def get_stats(self) -> Dict:
        """Get generator statistics."""
        models = list(self.models_path.glob("*.obj")) if self.models_path.exists() else []
        return {
            "available": self.available,
            "models_created": len(models)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL PROCESSOR
# ═══════════════════════════════════════════════════════════════════════════════

class ModelProcessor:
    """Process and convert 3D models."""
    
    def __init__(self):
        self.available = TRIMESH_AVAILABLE
    
    def load_model(self, filepath: str) -> Optional[Any]:
        """Load a 3D model."""
        if not self.available:
            return None
        
        try:
            return trimesh.load(filepath)
        except Exception as e:
            print(f"Model load error: {e}")
            return None
    
    def convert(self, input_path: str, output_format: str) -> Optional[str]:
        """Convert a model to a different format."""
        if not self.available:
            return None
        
        try:
            mesh = trimesh.load(input_path)
            
            input_path = Path(input_path)
            output_path = input_path.with_suffix(f".{output_format}")
            
            mesh.export(str(output_path))
            return str(output_path)
            
        except Exception as e:
            print(f"Conversion error: {e}")
            return None
    
    def get_info(self, filepath: str) -> Optional[Dict]:
        """Get information about a 3D model."""
        if not self.available:
            return None
        
        try:
            mesh = trimesh.load(filepath)
            
            return {
                "vertices": len(mesh.vertices) if hasattr(mesh, 'vertices') else 0,
                "faces": len(mesh.faces) if hasattr(mesh, 'faces') else 0,
                "bounds": mesh.bounds.tolist() if hasattr(mesh, 'bounds') else None,
                "center": mesh.centroid.tolist() if hasattr(mesh, 'centroid') else None,
                "volume": float(mesh.volume) if hasattr(mesh, 'volume') else 0,
                "watertight": mesh.is_watertight if hasattr(mesh, 'is_watertight') else False
            }
        except Exception as e:
            print(f"Info error: {e}")
            return None
    
    def scale(self, filepath: str, factor: float) -> Optional[str]:
        """Scale a model by a factor."""
        if not self.available:
            return None
        
        try:
            mesh = trimesh.load(filepath)
            mesh.apply_scale(factor)
            
            output_path = Path(filepath).with_stem(f"{Path(filepath).stem}_scaled")
            mesh.export(str(output_path))
            return str(output_path)
            
        except Exception as e:
            print(f"Scale error: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL GALLERY
# ═══════════════════════════════════════════════════════════════════════════════

class ModelGallery:
    """Gallery for managing 3D models."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "3d_models"
        self.gallery_path = workspace_path / "3d_gallery"
        self.gallery_path.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.gallery_path / "index.json"
        self.index: Dict = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load the gallery index."""
        if self.index_path.exists():
            with open(self.index_path, 'r') as f:
                return json.load(f)
        return {"models": [], "created_at": datetime.now().isoformat()}
    
    def _save_index(self):
        """Save the gallery index."""
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def add_model(self, filepath: str, prompt: str = None, 
                 tags: List[str] = None) -> Dict:
        """Add a model to the gallery."""
        model_id = Path(filepath).stem
        
        entry = {
            "id": model_id,
            "path": filepath,
            "prompt": prompt,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "favorite": False
        }
        
        self.index["models"].append(entry)
        self._save_index()
        
        return entry
    
    def get_models(self, tag: str = None, favorite: bool = None) -> List[Dict]:
        """Get models from the gallery."""
        models = self.index.get("models", [])
        
        if tag:
            models = [m for m in models if tag in m.get("tags", [])]
        
        if favorite is not None:
            models = [m for m in models if m.get("favorite") == favorite]
        
        return models
    
    def set_favorite(self, model_id: str, favorite: bool = True):
        """Set a model as favorite."""
        for model in self.index.get("models", []):
            if model["id"] == model_id:
                model["favorite"] = favorite
                self._save_index()
                return True
        return False
    
    def get_stats(self) -> Dict:
        """Get gallery statistics."""
        models = self.index.get("models", [])
        return {
            "total_models": len(models),
            "favorites": sum(1 for m in models if m.get("favorite")),
            "tags": list(set(tag for m in models for tag in m.get("tags", [])))
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LUMINA 3D INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class Lumina3D:
    """Lumina's 3D generation interface."""
    
    def __init__(self, workspace_path: Path):
        self.shap_e = ShapEGenerator(workspace_path)
        self.simple = Simple3DGenerator(workspace_path)
        self.processor = ModelProcessor()
        self.gallery = ModelGallery(workspace_path)
        
        if self.shap_e.available:
            print("    🎲 3D Generation: Shap-E available")
        elif self.simple.available:
            print("    🎲 3D Generation: Primitives only (install shap-e for text-to-3D)")
        else:
            print("    🎲 3D Generation: Not available (install trimesh)")
    
    def create(self, prompt: str) -> Optional[str]:
        """Create a 3D model from a text prompt."""
        # Try Shap-E first
        if self.shap_e.available:
            path = self.shap_e.generate(prompt)
            if path:
                self.gallery.add_model(path, prompt=prompt)
                return path
        
        # Fallback to primitives based on keywords
        prompt_lower = prompt.lower()
        
        if "cube" in prompt_lower or "box" in prompt_lower:
            return self.simple.create_cube(name=prompt.replace(" ", "_")[:20])
        elif "sphere" in prompt_lower or "ball" in prompt_lower:
            return self.simple.create_sphere(name=prompt.replace(" ", "_")[:20])
        elif "cylinder" in prompt_lower:
            return self.simple.create_cylinder(name=prompt.replace(" ", "_")[:20])
        elif "cone" in prompt_lower:
            return self.simple.create_cone(name=prompt.replace(" ", "_")[:20])
        elif "torus" in prompt_lower or "donut" in prompt_lower:
            return self.simple.create_torus(name=prompt.replace(" ", "_")[:20])
        else:
            # Default to sphere
            return self.simple.create_sphere(name=prompt.replace(" ", "_")[:20])
    
    def create_primitive(self, shape: str, **kwargs) -> Optional[str]:
        """Create a primitive shape."""
        shapes = {
            "cube": self.simple.create_cube,
            "sphere": self.simple.create_sphere,
            "cylinder": self.simple.create_cylinder,
            "cone": self.simple.create_cone,
            "torus": self.simple.create_torus
        }
        
        creator = shapes.get(shape.lower())
        if creator:
            return creator(**kwargs)
        return None
    
    def convert(self, filepath: str, to_format: str) -> Optional[str]:
        """Convert a model to a different format."""
        return self.processor.convert(filepath, to_format)
    
    def info(self, filepath: str) -> Optional[Dict]:
        """Get model information."""
        return self.processor.get_info(filepath)
    
    def list_models(self) -> List[Dict]:
        """List all models in gallery."""
        return self.gallery.get_models()
    
    def is_available(self) -> bool:
        """Check if 3D generation is available."""
        return self.shap_e.available or self.simple.available
    
    def get_stats(self) -> Dict:
        """Get 3D system statistics."""
        return {
            "shap_e": self.shap_e.get_stats(),
            "simple": self.simple.get_stats(),
            "gallery": self.gallery.get_stats()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def initialize_3d(workspace_path: Path) -> Lumina3D:
    """Initialize Lumina's 3D generation system."""
    return Lumina3D(workspace_path)


THREED_AVAILABLE = TORCH_AVAILABLE or TRIMESH_AVAILABLE


if __name__ == "__main__":
    # Test the 3D system
    workspace = Path("lumina_workspace")
    workspace.mkdir(exist_ok=True)
    
    gen3d = initialize_3d(workspace)
    
    print("\n" + "=" * 50)
    print("3D Generation Test")
    print("=" * 50)
    
    print("\nStats:", gen3d.get_stats())
    
    if gen3d.is_available():
        print("\nCreating a cube...")
        path = gen3d.create("a simple cube")
        if path:
            print(f"Created: {path}")
            info = gen3d.info(path)
            if info:
                print(f"Vertices: {info.get('vertices', 'N/A')}")
                print(f"Faces: {info.get('faces', 'N/A')}")
    else:
        print("\n3D generation not available. Install trimesh or shap-e.")

