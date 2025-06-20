#!/usr/bin/env python3
"""
Test script to demonstrate different error handling scenarios
"""
import json
import asyncio
from app.processors.download_router import UserInputError, DependencyNotFoundError, InternalError

# Example messages for testing different scenarios
test_messages = [
    # Valid Docker image
    {
        "id": 1,
        "type": "DOCKER",
        "dependency": "nginx:latest",
        "status": "STARTED",
        "date": "2024-01-01T00:00:00"
    },
    # Invalid download type (should reject)
    {
        "id": 2,
        "type": "INVALID_TYPE",
        "dependency": "something",
        "status": "STARTED",
        "date": "2024-01-01T00:00:00"
    },
    # Non-existent Docker image (should reject)
    {
        "id": 3,
        "type": "DOCKER",
        "dependency": "nonexistent-image:latest",
        "status": "STARTED",
        "date": "2024-01-01T00:00:00"
    },
    # Invalid Maven coordinate (should reject)
    {
        "id": 4,
        "type": "MAVEN",
        "dependency": "invalid:format",
        "status": "STARTED",
        "date": "2024-01-01T00:00:00"
    },
    # Non-existent Maven artifact (should reject)
    {
        "id": 5,
        "type": "MAVEN",
        "dependency": "com.example:nonexistent:1.0.0",
        "status": "STARTED",
        "date": "2024-01-01T00:00:00"
    }
]

def simulate_error_handling():
    """Simulate how different errors would be handled"""
    
    print("=== Error Handling Test Scenarios ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Test {i}: {message['type']} - {message['dependency']}")
        
        try:
            # Simulate the validation logic from download_router.py
            valid_types = ["DOCKER", "MAVEN", "PYTHON", "NPM", "FILE", "HELM", "WEBSITE"]
            
            if message['type'] not in valid_types:
                raise UserInputError(f"Invalid download type: {message['type']}. Valid types: {valid_types}")
            
            # Simulate Maven coordinate validation
            if message['type'] == "MAVEN":
                dependency = message['dependency']
                if dependency.count(":") != 2:
                    raise DependencyNotFoundError(f"Invalid Maven coordinate format: {dependency}. Expected format: group:artifact:version")
            
            # Simulate dependency not found scenarios
            if "nonexistent" in message['dependency']:
                if message['type'] == "DOCKER":
                    raise DependencyNotFoundError(f"Docker image {message['dependency']} does not exist")
                elif message['type'] == "MAVEN":
                    raise DependencyNotFoundError(f"Maven artifact {message['dependency']} does not exist")
            
            print("✅ Message would be processed successfully")
            
        except UserInputError as e:
            print(f"❌ User Input Error (REJECT): {e}")
            print("   → Message will be rejected and not retried")
            
        except DependencyNotFoundError as e:
            print(f"❌ Dependency Not Found (REJECT): {e}")
            print("   → Message will be rejected and not retried")
            
        except InternalError as e:
            print(f"⚠️  Internal Error (RETRY): {e}")
            print("   → Message will be retried later")
            
        except Exception as e:
            print(f"⚠️  Unexpected Error (RETRY): {e}")
            print("   → Message will be retried later")
        
        print()

if __name__ == "__main__":
    simulate_error_handling() 