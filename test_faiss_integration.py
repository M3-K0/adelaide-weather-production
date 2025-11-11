#!/usr/bin/env python3
"""
Adelaide Weather System - FAISS Integration Testing
Tests FAISS analog forecasting capabilities without requiring full deployment
"""

import json
import time
import numpy as np
import faiss
from pathlib import Path
import sys
import os

# Add the project root and api directories to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'api'))

class FaissIntegrationTester:
    def __init__(self):
        self.results = {
            "test_type": "faiss_integration",
            "timestamp": time.time(),
            "tests": [],
            "performance_metrics": {}
        }
        
    def log_test(self, test_name, status, details="", metrics=None):
        test_entry = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time(),
            "metrics": metrics or {}
        }
        self.results["tests"].append(test_entry)
        print(f"[{status}] {test_name}: {details}")
        if metrics:
            print(f"  Metrics: {metrics}")
    
    def test_faiss_index_loading(self):
        """Test loading FAISS indices"""
        try:
            indices_path = Path("indices")
            faiss_files = list(indices_path.glob("*.faiss"))
            
            loaded_indices = {}
            load_times = {}
            
            for faiss_file in faiss_files[:2]:  # Test first 2 to save time
                start_time = time.time()
                try:
                    index = faiss.read_index(str(faiss_file))
                    load_time = time.time() - start_time
                    
                    loaded_indices[faiss_file.name] = {
                        "ntotal": index.ntotal,
                        "d": index.d,
                        "is_trained": index.is_trained
                    }
                    load_times[faiss_file.name] = load_time
                    
                except Exception as e:
                    self.log_test("faiss_index_loading", "FAIL", 
                                 f"Failed to load {faiss_file}: {str(e)}")
                    return False
            
            avg_load_time = sum(load_times.values()) / len(load_times) if load_times else 0
            
            self.log_test("faiss_index_loading", "PASS", 
                         f"Loaded {len(loaded_indices)} indices successfully",
                         {
                             "loaded_indices": len(loaded_indices),
                             "average_load_time": f"{avg_load_time:.3f}s",
                             "index_details": loaded_indices
                         })
            return True
            
        except Exception as e:
            self.log_test("faiss_index_loading", "ERROR", str(e))
            return False
    
    def test_embeddings_loading(self):
        """Test loading embedding files"""
        try:
            embeddings_path = Path("embeddings")
            embedding_files = list(embeddings_path.glob("*.npy"))
            
            loaded_embeddings = {}
            load_times = {}
            
            for emb_file in embedding_files:
                start_time = time.time()
                try:
                    embeddings = np.load(emb_file)
                    load_time = time.time() - start_time
                    
                    loaded_embeddings[emb_file.name] = {
                        "shape": embeddings.shape,
                        "dtype": str(embeddings.dtype),
                        "size_mb": embeddings.nbytes / (1024 * 1024)
                    }
                    load_times[emb_file.name] = load_time
                    
                except Exception as e:
                    self.log_test("embeddings_loading", "FAIL", 
                                 f"Failed to load {emb_file}: {str(e)}")
                    return False
            
            avg_load_time = sum(load_times.values()) / len(load_times) if load_times else 0
            total_size_mb = sum(emb["size_mb"] for emb in loaded_embeddings.values())
            
            self.log_test("embeddings_loading", "PASS", 
                         f"Loaded {len(loaded_embeddings)} embedding files successfully",
                         {
                             "loaded_files": len(loaded_embeddings),
                             "total_size_mb": f"{total_size_mb:.1f}MB",
                             "average_load_time": f"{avg_load_time:.3f}s",
                             "embedding_details": loaded_embeddings
                         })
            return True
            
        except Exception as e:
            self.log_test("embeddings_loading", "ERROR", str(e))
            return False
            
    def test_faiss_search_performance(self):
        """Test FAISS search performance with real data"""
        try:
            indices_path = Path("indices")
            embeddings_path = Path("embeddings")
            
            # Load first available index and embedding
            faiss_files = list(indices_path.glob("*.faiss"))
            embedding_files = list(embeddings_path.glob("*.npy"))
            
            if not faiss_files or not embedding_files:
                self.log_test("faiss_search_performance", "SKIP", 
                             "No FAISS files or embeddings available")
                return True
                
            # Load index
            index = faiss.read_index(str(faiss_files[0]))
            embeddings = np.load(str(embedding_files[0]))
            
            # Prepare test query (use first embedding as query)
            if len(embeddings.shape) != 2:
                self.log_test("faiss_search_performance", "FAIL", 
                             f"Expected 2D embeddings, got shape {embeddings.shape}")
                return False
                
            query_vector = embeddings[:1].astype('float32')  # First embedding as query
            k = min(10, index.ntotal)  # Top-k results
            
            # Performance test: multiple searches
            search_times = []
            num_searches = 5
            
            for i in range(num_searches):
                start_time = time.time()
                distances, indices = index.search(query_vector, k)
                search_time = time.time() - start_time
                search_times.append(search_time)
                
            avg_search_time = sum(search_times) / len(search_times)
            min_search_time = min(search_times)
            max_search_time = max(search_times)
            
            # Validate results
            if len(distances[0]) != k or len(indices[0]) != k:
                self.log_test("faiss_search_performance", "FAIL", 
                             f"Expected {k} results, got distances: {len(distances[0])}, indices: {len(indices[0])}")
                return False
                
            performance_ok = avg_search_time < 1.0  # Should be sub-second
            
            self.log_test("faiss_search_performance", 
                         "PASS" if performance_ok else "WARNING", 
                         f"FAISS search performance test completed",
                         {
                             "index_file": faiss_files[0].name,
                             "embedding_file": embedding_files[0].name,
                             "index_size": index.ntotal,
                             "vector_dimension": index.d,
                             "queries_tested": num_searches,
                             "k_results": k,
                             "avg_search_time": f"{avg_search_time:.4f}s",
                             "min_search_time": f"{min_search_time:.4f}s",
                             "max_search_time": f"{max_search_time:.4f}s",
                             "performance_acceptable": performance_ok,
                             "sample_distances": distances[0][:3].tolist(),
                             "sample_indices": indices[0][:3].tolist()
                         })
            return True
            
        except Exception as e:
            self.log_test("faiss_search_performance", "ERROR", str(e))
            return False
            
    def test_outcomes_data_loading(self):
        """Test loading outcomes data"""
        try:
            outcomes_path = Path("outcomes")
            outcome_files = list(outcomes_path.glob("*.npy"))
            
            loaded_outcomes = {}
            
            for outcome_file in outcome_files:
                try:
                    outcomes = np.load(outcome_file)
                    loaded_outcomes[outcome_file.name] = {
                        "shape": outcomes.shape,
                        "dtype": str(outcomes.dtype),
                        "min_value": float(np.min(outcomes)),
                        "max_value": float(np.max(outcomes)),
                        "mean_value": float(np.mean(outcomes))
                    }
                except Exception as e:
                    self.log_test("outcomes_data_loading", "FAIL", 
                                 f"Failed to load {outcome_file}: {str(e)}")
                    return False
                    
            self.log_test("outcomes_data_loading", "PASS", 
                         f"Loaded {len(loaded_outcomes)} outcome files successfully",
                         {
                             "loaded_files": len(loaded_outcomes),
                             "outcome_details": loaded_outcomes
                         })
            return True
            
        except Exception as e:
            self.log_test("outcomes_data_loading", "ERROR", str(e))
            return False

    def test_analog_forecast_simulation(self):
        """Simulate the analog forecasting process"""
        try:
            indices_path = Path("indices")
            embeddings_path = Path("embeddings")
            outcomes_path = Path("outcomes")
            
            # Find matching files (same horizon)
            horizons = ["6h", "12h", "24h", "48h"]
            
            for horizon in horizons:
                # Look for matching files
                index_pattern = f"*{horizon}*.faiss"
                embedding_pattern = f"*{horizon}*.npy"
                outcome_pattern = f"*{horizon}*.npy"
                
                index_files = list(indices_path.glob(index_pattern))
                embedding_files = list(embeddings_path.glob(embedding_pattern))
                outcome_files = list(outcomes_path.glob(outcome_pattern))
                
                if index_files and embedding_files and outcome_files:
                    # Test one complete analog forecast workflow
                    start_time = time.time()
                    
                    # Load data
                    index = faiss.read_index(str(index_files[0]))
                    embeddings = np.load(str(embedding_files[0]))
                    outcomes = np.load(str(outcome_files[0]))
                    
                    # Simulate query
                    query_vector = embeddings[:1].astype('float32')
                    k = 10
                    
                    # Find analogs
                    distances, indices_found = index.search(query_vector, k)
                    
                    # Get corresponding outcomes
                    analog_outcomes = outcomes[indices_found[0]]
                    
                    # Simple ensemble forecast (mean)
                    forecast_value = np.mean(analog_outcomes)
                    
                    total_time = time.time() - start_time
                    
                    self.log_test("analog_forecast_simulation", "PASS", 
                                 f"Completed {horizon} analog forecast simulation",
                                 {
                                     "horizon": horizon,
                                     "total_time": f"{total_time:.4f}s",
                                     "analogs_found": k,
                                     "forecast_value": float(forecast_value),
                                     "analog_distances": distances[0][:3].tolist(),
                                     "sample_outcomes": analog_outcomes[:3].tolist()
                                 })
                    
                    # Test performance expectation
                    if total_time > 0.5:  # Should be sub-500ms
                        self.log_test("analog_forecast_simulation", "WARNING", 
                                     f"{horizon} forecast took {total_time:.3f}s (>0.5s threshold)")
                    
                    break  # Test one horizon successfully
                    
            else:
                self.log_test("analog_forecast_simulation", "SKIP", 
                             "No matching FAISS index, embedding, and outcome files found")
                return True
                
            return True
            
        except Exception as e:
            self.log_test("analog_forecast_simulation", "ERROR", str(e))
            return False
    
    def run_all_tests(self):
        """Run all FAISS integration tests"""
        print("🔧 Starting FAISS Integration Testing")
        print("=" * 50)
        
        test_methods = [
            self.test_faiss_index_loading,
            self.test_embeddings_loading,
            self.test_outcomes_data_loading,
            self.test_faiss_search_performance,
            self.test_analog_forecast_simulation
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"EXCEPTION in {test_method.__name__}: {str(e)}")
                
        # Calculate summary
        total_tests = len(self.results["tests"])
        passed_tests = len([t for t in self.results["tests"] if t["status"] == "PASS"])
        failed_tests = len([t for t in self.results["tests"] if t["status"] == "FAIL"])
        
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        print(f"\n📊 FAISS Integration Test Summary:")
        print(f"   Tests: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}")
        print(f"   Pass Rate: {pass_rate:.1%}")
        
        return self.results
    
    def save_results(self, filename="faiss_integration_results.json"):
        """Save results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✅ FAISS integration test results saved to {filename}")

if __name__ == "__main__":
    tester = FaissIntegrationTester()
    results = tester.run_all_tests()
    tester.save_results()
    
    # Exit with appropriate code
    total_tests = len(results["tests"])
    passed_tests = len([t for t in results["tests"] if t["status"] == "PASS"])
    pass_rate = passed_tests / total_tests if total_tests > 0 else 0
    
    sys.exit(0 if pass_rate >= 0.8 else 1)