#!/usr/bin/env python
"""Test script to check if schema generation works"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Medical_consultation.settings')
django.setup()

from drf_spectacular.generators import SchemaGenerator

print("Testing schema generation...")
try:
    generator = SchemaGenerator()
    schema = generator.get_schema(request=None, public=True)
    print("[SUCCESS] Schema generated successfully!")
    print(f"[SUCCESS] Found {len(schema.get('paths', {}))} API paths")
    print("[SUCCESS] No errors!")
    sys.exit(0)
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
