#!/usr/bin/env python3
"""
Test script for ESYA QR Ticketing System
Run this script to test the registration and validation functionality
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "name": "Test User",
    "email": "test@example.com"
}

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

def print_result(success, message):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")

def test_health_check():
    """Test health check endpoint"""
    print_header("HEALTH CHECK TEST")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, f"Health check passed")
            print(f"   Status: {data.get('status')}")
            print(f"   Firebase: {'Connected' if data.get('firebase_connected') else 'Disconnected'}")
            print(f"   Timestamp: {data.get('timestamp')}")
            return True
        else:
            print_result(False, f"Health check failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_result(False, f"Health check failed: {str(e)}")
        return False

def test_registration():
    """Test user registration"""
    print_header("REGISTRATION TEST")
    
    try:
        # Test valid registration
        response = requests.post(
            f"{BASE_URL}/register",
            json=TEST_USER,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 201:
            data = response.json()
            ticket_id = data.get('ticket_id')
            print_result(True, "Registration successful")
            print(f"   Message: {data.get('message')}")
            print(f"   Ticket ID: {ticket_id[:8]}...{ticket_id[-8:]}")
            return ticket_id
        else:
            print_result(False, f"Registration failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print_result(False, f"Registration failed: {str(e)}")
        return None

def test_invalid_registration():
    """Test invalid registration data"""
    print_header("INVALID REGISTRATION TEST")
    
    test_cases = [
        {"name": "", "email": "test@example.com"},  # Empty name
        {"name": "Test User", "email": ""},  # Empty email
        {"name": "Test User", "email": "invalid-email"},  # Invalid email
        {}  # Empty data
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            response = requests.post(
                f"{BASE_URL}/register",
                json=test_case,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                print_result(True, f"Test {i}: Correctly rejected invalid data")
            else:
                print_result(False, f"Test {i}: Should have rejected invalid data (got {response.status_code})")
                all_passed = False
                
        except requests.exceptions.RequestException as e:
            print_result(False, f"Test {i}: Request failed: {str(e)}")
            all_passed = False
    
    return all_passed

def test_validation(ticket_id):
    """Test ticket validation"""
    print_header("VALIDATION TEST")
    
    if not ticket_id:
        print_result(False, "No ticket ID provided for validation test")
        return False
    
    try:
        # Test first validation (should succeed)
        response = requests.get(f"{BASE_URL}/validate/{ticket_id}", timeout=10)
        
        if response.status_code == 200 and "Valid Ticket" in response.text:
            print_result(True, "First validation successful - ticket marked as used")
        else:
            print_result(False, f"First validation failed (status: {response.status_code})")
            return False
        
        # Test second validation (should show already used)
        time.sleep(1)  # Brief delay
        response = requests.get(f"{BASE_URL}/validate/{ticket_id}", timeout=10)
        
        if response.status_code == 200 and "Already Used" in response.text:
            print_result(True, "Second validation correctly shows ticket as already used")
            return True
        else:
            print_result(False, "Second validation should show ticket as already used")
            return False
            
    except requests.exceptions.RequestException as e:
        print_result(False, f"Validation test failed: {str(e)}")
        return False

def test_invalid_validation():
    """Test validation with invalid ticket ID"""
    print_header("INVALID VALIDATION TEST")
    
    fake_ticket_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        response = requests.get(f"{BASE_URL}/validate/{fake_ticket_id}", timeout=10)
        
        if response.status_code == 404 and "Invalid Ticket" in response.text:
            print_result(True, "Correctly rejected invalid ticket ID")
            return True
        else:
            print_result(False, f"Should have rejected invalid ticket ID (got {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print_result(False, f"Invalid validation test failed: {str(e)}")
        return False

def test_frontend():
    """Test frontend accessibility"""
    print_header("FRONTEND TEST")
    
    try:
        response = requests.get(BASE_URL, timeout=10)
        
        if response.status_code == 200 and "ESYA" in response.text:
            print_result(True, "Frontend is accessible")
            print(f"   Page title contains: ESYA")
            print(f"   Response size: {len(response.text)} characters")
            return True
        else:
            print_result(False, f"Frontend not accessible (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print_result(False, f"Frontend test failed: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("🎟️  ESYA QR Ticketing System - Test Suite")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Testing URL: {BASE_URL}")
    
    tests = []
    
    # Run tests
    tests.append(("Health Check", test_health_check()))
    tests.append(("Frontend", test_frontend()))
    tests.append(("Invalid Registration", test_invalid_registration()))
    
    # Registration test returns ticket ID for validation
    print_header("REGISTRATION & VALIDATION FLOW")
    ticket_id = test_registration()
    tests.append(("Registration", ticket_id is not None))
    
    if ticket_id:
        tests.append(("Validation", test_validation(ticket_id)))
    else:
        tests.append(("Validation", False))
        print_result(False, "Skipped validation test (no ticket ID)")
    
    tests.append(("Invalid Validation", test_invalid_validation()))
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1].rstrip('/')
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)