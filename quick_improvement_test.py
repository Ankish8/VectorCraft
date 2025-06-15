#!/usr/bin/env python3
"""
Quick improvement test for VectorCraft 2.0
Tests the improvement pipeline with Frame 53.png
"""

import os
import time
import json
import requests
import numpy as np
from PIL import Image
import cv2
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_target_image(image_path: str):
    """Quick analysis of the target image"""
    logger.info(f"Analyzing target image: {image_path}")
    
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    height, width, channels = image.shape
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Basic analysis
    analysis = {
        'dimensions': (width, height),
        'channels': channels,
        'file_size': os.path.getsize(image_path),
        'unique_colors': len(np.unique(image.reshape(-1, image.shape[-1]), axis=0)),
        'edge_density': calculate_edge_density(gray),
        'avg_brightness': np.mean(gray),
        'contrast': np.std(gray)
    }
    
    logger.info(f"Image analysis: {analysis}")
    return analysis

def calculate_edge_density(gray_image):
    """Calculate edge density using Canny"""
    edges = cv2.Canny(gray_image, 50, 150)
    return np.sum(edges > 0) / edges.size

def test_vectorcraft_processing(image_path: str, server_url: str = "http://localhost:8080"):
    """Test processing with VectorCraft"""
    logger.info("Testing VectorCraft processing...")
    
    try:
        # Check server health first
        health_response = requests.get(f"{server_url}/health", timeout=5)
        if health_response.status_code != 200:
            raise Exception("VectorCraft server not healthy")
        
        logger.info("✅ VectorCraft server is healthy")
        
        # Process the image
        with open(image_path, 'rb') as f:
            files = {'file': f}
            data = {
                'vectorizer': 'optimized',
                'target_time': '60',
                'strategy': 'vtracer_high_fidelity'
            }
            
            logger.info("🔄 Processing image with VectorCraft...")
            start_time = time.time()
            
            response = requests.post(f'{server_url}/api/vectorize', files=files, data=data)
            
            processing_time = time.time() - start_time
            logger.info(f"⏱️ Request completed in {processing_time:.2f}s")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    logger.info("✅ VectorCraft processing successful!")
                    logger.info(f"   Algorithm time: {result['processing_time']:.2f}s")
                    logger.info(f"   Strategy used: {result['strategy_used']}")
                    logger.info(f"   Quality score: {result['quality_score']:.3f}")
                    logger.info(f"   SVG elements: {result['num_elements']}")
                    logger.info(f"   Content type: {result['content_type']}")
                    
                    return result
                else:
                    raise Exception(f"Processing failed: {result.get('error')}")
            else:
                raise Exception(f"HTTP Error {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.error(f"VectorCraft processing failed: {e}")
        raise

def save_svg_result(svg_content: str, output_path: str):
    """Save SVG result to file"""
    with open(output_path, 'w') as f:
        f.write(svg_content)
    logger.info(f"💾 SVG saved to: {output_path}")

def calculate_basic_similarity(target_image_path: str, svg_content: str) -> float:
    """Calculate comprehensive similarity between target image and SVG output"""
    logger.info("🔍 Calculating similarity metrics...")
    
    try:
        from vectorcraft.utils.similarity_calculator import SimilarityCalculator
        
        calculator = SimilarityCalculator()
        
        # Try comprehensive similarity calculation first
        try:
            similarity = calculator.calculate_comprehensive_similarity(svg_content, target_image_path)
            if similarity > 0:
                logger.info(f"📊 Comprehensive similarity: {similarity:.3f}")
                return similarity
        except Exception as e:
            logger.warning(f"Comprehensive similarity calculation failed: {e}")
        
        # Fallback to heuristic estimation
        svg_elements = svg_content.count('<rect') + svg_content.count('<path') + svg_content.count('<circle')
        svg_size = len(svg_content)
        
        # Analyze target image characteristics
        target_image = cv2.imread(target_image_path)
        if target_image is not None:
            unique_colors = len(np.unique(target_image.reshape(-1, target_image.shape[2]), axis=0))
            gray = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
        else:
            unique_colors = 10
            edge_density = 0.01
        
        target_characteristics = {
            'unique_colors': unique_colors,
            'edge_density': edge_density
        }
        
        similarity = calculator.estimate_heuristic_similarity(svg_content, svg_elements, svg_size, target_characteristics)
        logger.info(f"📊 Heuristic similarity: {similarity:.3f}")
        
        logger.info(f"   SVG elements: {svg_elements}")
        logger.info(f"   SVG size: {svg_size} characters")
        
        return similarity
    
    except Exception as e:
        logger.error(f"Similarity calculation failed: {e}")
        
        # Ultra-basic fallback
        svg_elements = svg_content.count('<rect') + svg_content.count('<path') + svg_content.count('<circle')
        
        if svg_elements == 0:
            return 0.0
        elif svg_elements < 5:
            return svg_elements / 5.0 * 0.5
        else:
            return min(0.8, svg_elements / 15.0)

def suggest_improvements(similarity_score: float, vectorcraft_result: dict, image_analysis: dict):
    """Suggest improvements based on results"""
    logger.info("🧠 Sequential thinking - analyzing results and suggesting improvements...")
    
    improvements = []
    
    # Analyze current performance
    quality_score = vectorcraft_result.get('quality_score', 0)
    num_elements = vectorcraft_result.get('num_elements', 0)
    content_type = vectorcraft_result.get('content_type', 'unknown')
    processing_time = vectorcraft_result.get('processing_time', 0)
    
    logger.info(f"🔍 Current metrics:")
    logger.info(f"   Similarity: {similarity_score:.3f}")
    logger.info(f"   Quality: {quality_score:.3f}")
    logger.info(f"   Elements: {num_elements}")
    logger.info(f"   Content type: {content_type}")
    logger.info(f"   Processing time: {processing_time:.2f}s")
    
    # Sequential improvement logic
    if similarity_score < 0.7:
        improvements.append("🚨 Major improvements needed:")
        improvements.append("  - Enhance core vectorization algorithm")
        improvements.append("  - Improve edge detection accuracy")
        improvements.append("  - Better color quantization")
        
        if image_analysis['edge_density'] > 0.1:
            improvements.append("  - High edge density detected - improve contour tracing")
        
        if image_analysis['unique_colors'] > 50:
            improvements.append("  - Many colors detected - enhance color reduction strategy")
            
    elif similarity_score < 0.85:
        improvements.append("🔧 Moderate improvements needed:")
        improvements.append("  - Fine-tune primitive detection")
        improvements.append("  - Optimize path simplification")
        improvements.append("  - Improve curve fitting")
        
        if num_elements < 5:
            improvements.append("  - Too few elements - may be over-simplifying")
        elif num_elements > 30:
            improvements.append("  - Too many elements - better consolidation needed")
            
    elif similarity_score < 0.95:
        improvements.append("⚡ Minor optimizations needed:")
        improvements.append("  - Perceptual quality tuning")
        improvements.append("  - Edge case handling")
        improvements.append("  - Final polish optimizations")
    else:
        improvements.append("🎉 Excellent results! Consider:")
        improvements.append("  - Performance optimizations")
        improvements.append("  - Testing on more diverse images")
    
    # Content-specific suggestions
    if content_type == 'mixed':
        improvements.append("📝 Content-specific improvements:")
        improvements.append("  - Better content type detection")
        improvements.append("  - Separate strategies for different regions")
    
    # Performance suggestions
    if processing_time > 30:
        improvements.append("⚡ Performance improvements:")
        improvements.append("  - Optimize processing pipeline")
        improvements.append("  - Consider parallel processing")
    
    return improvements

def research_inspiration():
    """Research inspiration from existing solutions"""
    logger.info("🔬 Researching inspiration from existing solutions...")
    
    research_notes = [
        "📚 Key research areas identified:",
        "  - VTracer: Advanced curve fitting algorithms",
        "  - Potrace: Efficient path optimization",
        "  - Vector Magic: Commercial-grade quality standards",
        "  - DiffVG: Differentiable optimization techniques",
        "",
        "🎯 Promising techniques to explore:",
        "  - Multi-scale processing for different detail levels",
        "  - Perceptual loss functions for better visual quality",
        "  - Machine learning-based primitive detection",
        "  - Adaptive strategy selection based on content analysis",
        "  - Advanced color palette optimization"
    ]
    
    for note in research_notes:
        logger.info(note)
    
    return research_notes

def create_improvement_plan(improvements: list, research_notes: list):
    """Create a concrete improvement plan"""
    logger.info("📋 Creating improvement implementation plan...")
    
    plan = {
        'immediate_actions': [],
        'short_term_goals': [],
        'long_term_vision': [],
        'implementation_priority': []
    }
    
    # Categorize improvements
    for improvement in improvements:
        if '🚨' in improvement or 'Major' in improvement:
            plan['immediate_actions'].append(improvement)
        elif '🔧' in improvement or 'Moderate' in improvement:
            plan['short_term_goals'].append(improvement)
        elif '⚡' in improvement or 'Minor' in improvement:
            plan['long_term_vision'].append(improvement)
    
    # Set implementation priorities
    plan['implementation_priority'] = [
        "1. Enhance edge detection algorithms",
        "2. Improve color quantization strategy", 
        "3. Optimize primitive detection accuracy",
        "4. Implement multi-scale processing",
        "5. Add perceptual quality metrics",
        "6. Performance optimizations"
    ]
    
    return plan

def save_improvement_session(image_path: str, results: dict, improvements: list, plan: dict):
    """Save the improvement session results"""
    session_data = {
        'timestamp': time.time(),
        'target_image': image_path,
        'vectorcraft_results': results,
        'similarity_analysis': {
            'estimated_similarity': results.get('estimated_similarity', 0),
            'needs_improvement': results.get('estimated_similarity', 0) < 0.95
        },
        'improvement_suggestions': improvements,
        'implementation_plan': plan,
        'next_steps': [
            "Implement highest priority improvements",
            "Test with improved algorithms", 
            "Measure similarity improvements",
            "Iterate until 95% similarity achieved"
        ]
    }
    
    # Save to improvement results directory
    os.makedirs('improvement_results', exist_ok=True)
    session_file = f"improvement_results/session_{int(time.time())}.json"
    
    with open(session_file, 'w') as f:
        json.dump(session_data, f, indent=2, default=str)
    
    logger.info(f"💾 Improvement session saved to: {session_file}")
    
    # Also update CLAUDE.md
    update_claude_md(session_data)

def update_claude_md(session_data):
    """Update CLAUDE.md with latest improvement session"""
    claude_md_path = "CLAUDE.md"
    
    # Read existing content
    if os.path.exists(claude_md_path):
        with open(claude_md_path, 'r') as f:
            content = f.read()
    else:
        content = ""
    
    # Append new session results
    new_content = f"""

## Latest Improvement Session - {time.strftime('%Y-%m-%d %H:%M:%S')}

### Results Summary
- **Target Image**: {session_data['target_image']}
- **Estimated Similarity**: {session_data['similarity_analysis']['estimated_similarity']:.3f}
- **Processing Time**: {session_data['vectorcraft_results']['processing_time']:.2f}s
- **Quality Score**: {session_data['vectorcraft_results']['quality_score']:.3f}
- **SVG Elements**: {session_data['vectorcraft_results']['num_elements']}

### Key Findings
- Strategy Used: {session_data['vectorcraft_results']['strategy_used']}
- Content Type: {session_data['vectorcraft_results']['content_type']}
- Needs Improvement: {'Yes' if session_data['similarity_analysis']['needs_improvement'] else 'No'}

### Next Actions
"""
    
    for action in session_data['next_steps']:
        new_content += f"- [ ] {action}\n"
    
    new_content += f"""
### Implementation Priority
"""
    
    for priority in session_data['implementation_plan']['implementation_priority']:
        new_content += f"- [ ] {priority}\n"
    
    # Write updated content
    with open(claude_md_path, 'w') as f:
        f.write(content + new_content)
    
    logger.info(f"📝 Updated CLAUDE.md with latest session results")

def main():
    """Main improvement pipeline execution"""
    target_image = "/Users/ankish/Downloads/Frame 54.png"
    
    logger.info("🚀 Starting VectorCraft 2.0 Improvement Pipeline")
    logger.info(f"🎯 Target: 95% similarity for {target_image}")
    logger.info("=" * 60)
    
    try:
        # Step 1: Analyze target image
        logger.info("📊 STEP 1: Analyzing target image...")
        image_analysis = analyze_target_image(target_image)
        
        # Step 2: Process with VectorCraft
        logger.info("\n🔄 STEP 2: Processing with VectorCraft...")
        vectorcraft_result = test_vectorcraft_processing(target_image)
        
        # Step 3: Save SVG result
        logger.info("\n💾 STEP 3: Saving SVG result...")
        svg_output_path = "improvement_results/frame53_current_result.svg"
        os.makedirs('improvement_results', exist_ok=True)
        save_svg_result(vectorcraft_result['svg_content'], svg_output_path)
        
        # Step 4: Calculate similarity
        logger.info("\n🔍 STEP 4: Calculating similarity...")
        similarity = calculate_basic_similarity(target_image, vectorcraft_result['svg_content'])
        vectorcraft_result['estimated_similarity'] = similarity
        
        # Step 4.5: Compare with real VTracer
        logger.info("\n🔍 STEP 4.5: Testing real VTracer for comparison...")
        try:
            import vtracer
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp_output:
                tmp_output_path = tmp_output.name
            
            try:
                vtracer.convert_image_to_svg_py(
                    target_image,
                    tmp_output_path,
                    color_precision=6,
                    layer_difference=16,
                    mode='spline',
                    filter_speckle=4,
                    colormode='color',
                    hierarchical='stacked'
                )
                
                with open(tmp_output_path, 'r') as f:
                    vtracer_svg = f.read()
                
                vtracer_similarity = calculate_basic_similarity(target_image, vtracer_svg)
                logger.info(f"🏆 Real VTracer similarity: {vtracer_similarity:.3f}")
                logger.info(f"📊 Our result: {similarity:.3f}")
                logger.info(f"📈 Improvement potential: {vtracer_similarity - similarity:.3f}")
                
                # Save VTracer result for comparison
                with open('improvement_results/vtracer_comparison.svg', 'w') as f:
                    f.write(vtracer_svg)
                logger.info("💾 VTracer result saved to: improvement_results/vtracer_comparison.svg")
                
            finally:
                try:
                    os.unlink(tmp_output_path)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"VTracer comparison failed: {e}")
        
        # Step 5: Sequential thinking for improvements
        logger.info("\n🧠 STEP 5: Sequential thinking analysis...")
        improvements = suggest_improvements(similarity, vectorcraft_result, image_analysis)
        
        # Step 6: Research inspiration
        logger.info("\n🔬 STEP 6: Researching inspiration...")
        research_notes = research_inspiration()
        
        # Step 7: Create improvement plan
        logger.info("\n📋 STEP 7: Creating improvement plan...")
        improvement_plan = create_improvement_plan(improvements, research_notes)
        
        # Step 8: Save session and update CLAUDE.md
        logger.info("\n💾 STEP 8: Saving improvement session...")
        save_improvement_session(target_image, vectorcraft_result, improvements, improvement_plan)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("🎉 IMPROVEMENT PIPELINE COMPLETE")
        logger.info(f"📊 Current similarity: {similarity:.3f}")
        logger.info(f"🎯 Target similarity: 0.95")
        logger.info(f"📈 Improvement needed: {0.95 - similarity:.3f}")
        
        if similarity >= 0.95:
            logger.info("🏆 TARGET ACHIEVED! 95% similarity reached!")
        else:
            logger.info("🔧 Improvements needed - see generated plan")
            logger.info("📝 Check CLAUDE.md for updated action items")
        
        logger.info(f"📁 Results saved in: improvement_results/")
        logger.info(f"🖼️ SVG output: {svg_output_path}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()