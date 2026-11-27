#!/usr/bin/env python3
"""
Phase 0 Environment Check
Tests GPU, CUDA, PyTorch, Diffusers, model storage, and optional Redis.
"""
import sys
import argparse
import platform
from pathlib import Path

def check_python():
    print("=" * 60)
    print("Python Environment")
    print("=" * 60)
    version = sys.version_info
    print(f"Python: {version.major}.{version.minor}.{version.micro}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Machine: {platform.machine()}")
    
    if version < (3, 10):
        print("⚠️  WARNING: Python 3.10+ recommended")
    else:
        print("✅ Python version OK")
    print()

def check_torch():
    print("=" * 60)
    print("PyTorch & CUDA")
    print("=" * 60)
    try:
        import torch
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"cuDNN version: {torch.backends.cudnn.version()}")
            
            gpu_count = torch.cuda.device_count()
            print(f"GPU count: {gpu_count}")
            
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                vram_gb = props.total_memory / 1e9
                compute = f"sm_{props.major}{props.minor}"
                print(f"  GPU {i}: {props.name}")
                print(f"    VRAM: {vram_gb:.1f} GB")
                print(f"    Compute: {compute}")
                
                if props.major == 12 and props.minor == 0:
                    print("    ✅ RTX 5090 (Blackwell sm_120) detected")
                elif props.major >= 7 and props.minor >= 5:
                    print(f"    ✅ Compute {compute} supported")
                else:
                    print(f"    ⚠️  WARNING: Compute {compute} may not support FP8")
            
            # Test allocation
            try:
                x = torch.randn(1000, 1000, device="cuda")
                allocated = torch.cuda.memory_allocated() / 1e9
                print(f"Test allocation: {allocated:.2f} GB (OK)")
                del x
                torch.cuda.empty_cache()
                print("✅ CUDA operational")
            except Exception as e:
                print(f"❌ CUDA allocation test failed: {e}")
        else:
            print("❌ No CUDA GPU detected")
            print("   Phase 0 requires an NVIDIA GPU with CUDA support")
            return False
    except ImportError:
        print("❌ PyTorch not installed")
        print("   Install: pip install torch --index-url https://download.pytorch.org/whl/cu128")
        return False
    print()
    return True

def check_diffusers():
    print("=" * 60)
    print("Diffusers & Transformers")
    print("=" * 60)
    try:
        import diffusers
        print(f"Diffusers: {diffusers.__version__}")
        
        # Check for required pipelines
        from packaging import version
        v = version.parse(diffusers.__version__)
        required = version.parse("0.43.0")
        
        if v >= required:
            print(f"✅ Diffusers >= 0.43.0 (has Krea2Pipeline, ZImagePipeline, etc.)")
        else:
            print(f"⚠️  WARNING: Diffusers {diffusers.__version__} < 0.43.0")
            print("   Image model pipelines may be missing")
            print("   Upgrade: pip install diffusers>=0.43")
        
        # Check transformers
        import transformers
        print(f"Transformers: {transformers.__version__}")
        
        # Check accelerate
        import accelerate
        print(f"Accelerate: {accelerate.__version__}")
        
        print("✅ Core AI libraries installed")
    except ImportError as e:
        print(f"❌ Missing library: {e}")
        print("   Install: pip install diffusers>=0.43 transformers accelerate")
        return False
    print()
    return True

def check_model_storage(model_root: str):
    print("=" * 60)
    print("Model Storage")
    print("=" * 60)
    path = Path(model_root).expanduser()
    print(f"Model root: {path}")
    
    if path.exists():
        print(f"✅ Directory exists")
        
        # Check disk space
        try:
            import psutil
            usage = psutil.disk_usage(str(path))
            free_gb = usage.free / 1e9
            print(f"Free space: {free_gb:.1f} GB")
            
            if free_gb < 500:
                print("⚠️  WARNING: Less than 500 GB free")
                print("   Some model downloads may fail")
            else:
                print("✅ Sufficient disk space")
        except ImportError:
            print("⚠️  psutil not installed, can't check disk space")
            print("   Install: pip install psutil")
        
        # List subdirectories
        subdirs = [d.name for d in path.iterdir() if d.is_dir()]
        if subdirs:
            print(f"Existing model folders ({len(subdirs)}):")
            for d in sorted(subdirs)[:10]:
                print(f"  - {d}")
            if len(subdirs) > 10:
                print(f"  ... and {len(subdirs) - 10} more")
        else:
            print("No model folders found (will download during tests)")
    else:
        print(f"⚠️  Directory does not exist: {path}")
        print("   Create it or adjust --model-root")
        return False
    print()
    return True

def check_redis():
    print("=" * 60)
    print("Redis (Optional for Phase 0)")
    print("=" * 60)
    try:
        import redis
        print(f"redis-py: {redis.__version__}")
        
        # Try to connect
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print("✅ Redis reachable at localhost:6379")
            info = r.info('server')
            print(f"   Version: {info.get('redis_version', 'unknown')}")
        except redis.ConnectionError:
            print("⚠️  Redis not running (not required for Phase 0 GPU tests)")
            print("   Full app needs Redis for Celery queues")
    except ImportError:
        print("⚠️  redis-py not installed (not required for Phase 0)")
        print("   Install: pip install redis")
    print()

def check_sglang():
    print("=" * 60)
    print("SGLang (Optional)")
    print("=" * 60)
    try:
        import sglang
        print(f"SGLang: {sglang.__version__}")
        print("✅ SGLang available (optional H3 runtime)")
    except ImportError:
        print("⚠️  SGLang not installed (optional)")
        print("   Video tests will use Diffusers pipelines")
        print("   Install: pip install sglang>=0.5.17")
    print()

def main():
    parser = argparse.ArgumentParser(description="Phase 0 Environment Check")
    parser.add_argument("--model-root", default="D:\\AIModels" if platform.system() == "Windows" else "~/AIModels",
                        help="Path to model storage directory")
    args = parser.parse_args()
    
    print("Phase 0 Environment Check — RTX 5090 Test Kit")
    print("=" * 60)
    print()
    
    checks = [
        ("Python", check_python),
        ("PyTorch & CUDA", lambda: check_torch()),
        ("Diffusers & Transformers", lambda: check_diffusers()),
        ("Model Storage", lambda: check_model_storage(args.model_root)),
    ]
    
    results = []
    for name, check_fn in checks:
        try:
            result = check_fn()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed with exception: {e}")
            results.append((name, False))
    
    # Optional checks (don't fail if missing)
    check_redis()
    check_sglang()
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    if all_passed:
        print()
        print("✅ Environment ready for Phase 0 GPU tests!")
        print()
        print("Next steps:")
        print(f"  python vram_fit.py --model-root {args.model_root}")
        print(f"  python converter_check.py --model-root {args.model_root}")
        return 0
    else:
        print()
        print("❌ Some checks failed. Fix issues above before running GPU tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
