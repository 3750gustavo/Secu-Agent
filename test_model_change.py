"""
Test script to verify the AI model change is working correctly.
This will test the new Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Derestricted model.
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_client import LLM_MODEL, AIClient, call_llm_with_limit

def test_config_loaded():
    """Test that the new model is loaded from config."""
    print("Testing model configuration...")
    print(f"Current LLM_MODEL: {LLM_MODEL}")
    
    expected_model = "Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Derestricted"
    
    if LLM_MODEL == expected_model:
        print(f"✓ Model correctly set to: {LLM_MODEL}")
        return True
    else:
        print(f"✗ Model mismatch! Expected: {expected_model}, Got: {LLM_MODEL}")
        return False

def test_ai_client_defaults():
    """Test that AIClient uses the correct default model."""
    print("\nTesting AIClient defaults...")
    client = AIClient()
    print(f"AIClient default model: {client.model}")
    
    expected_model = "Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-Derestricted"
    
    if client.model == expected_model:
        print(f"✓ AIClient correctly using: {client.model}")
        return True
    else:
        print(f"✗ AIClient model mismatch! Expected: {expected_model}, Got: {client.model}")
        return False

async def test_live_api_call():
    """Test a live API call with the new model."""
    print("\nTesting live API call with new model...")
    
    try:
        system_prompt = "You are a helpful assistant. Respond very briefly."
        user_message = "Say 'Hello from Qwen3.5 model!'"
        
        print(f"Making API call with model: {LLM_MODEL}")
        response = await call_llm_with_limit(
            system_prompt=system_prompt,
            user_message=user_message,
            reason="Model change test"
        )
        
        print(f"✓ API call successful!")
        print(f"Response: {response}")
        return True
        
    except Exception as e:
        print(f"✗ API call failed: {str(e)}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("AI Model Change Verification Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Config loading
    results.append(("Config Loading", test_config_loaded()))
    
    # Test 2: AIClient defaults
    results.append(("AIClient Defaults", test_ai_client_defaults()))
    
    # Test 3: Live API call
    results.append(("Live API Call", await test_live_api_call()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Model change is working correctly.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)