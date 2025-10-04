# Bug Fix: Schema Generation Error

## Issue

When accessing `/api/schema/`, `/api/docs/`, or `/api/redoc/`, the following error occurred:

```
django.core.exceptions.ImproperlyConfigured: Field name `region` is not valid for model `Doctor` in `apps.doctors.serializers.DoctorLocationUpdateSerializer`.
```

## Root Cause

The `DoctorLocationUpdateSerializer` was trying to reference fields (`region` and `district`) that don't exist on the `Doctor` model.

### What the Doctor Model Has:
- `workplace` - CharField for workplace name
- `workplace_address` - TextField for address
- `latitude` - CharField for coordinates
- `longitude` - CharField for coordinates
- `hospital` - ForeignKey to Hospital model

### What the Serializer Was Trying to Use (WRONG):
- `region` - ❌ Doesn't exist on Doctor
- `district` - ❌ Doesn't exist on Doctor

## Fix Applied

Updated `apps/doctors/serializers.py` - `DoctorLocationUpdateSerializer`:

### Before (Broken):
```python
class DoctorLocationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating doctor location"""

    region_name = serializers.CharField(source='region.name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)

    class Meta:
        model = Doctor
        fields = ['region', 'district', 'region_name', 'district_name', 'workplace_address']
    # ...
```

### After (Fixed):
```python
class DoctorLocationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating doctor location (workplace address and coordinates)"""

    hospital_name = serializers.CharField(source='hospital.name', read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'workplace',
            'workplace_address',
            'latitude',
            'longitude',
            'hospital',
            'hospital_name'
        ]
        read_only_fields = ['hospital_name']
    # ...
```

## Changes Made

1. **Removed invalid fields**: `region`, `district`, `region_name`, `district_name`
2. **Added correct fields**:
   - `workplace` - Doctor's workplace name
   - `workplace_address` - Full address
   - `latitude` - GPS coordinate
   - `longitude` - GPS coordinate
   - `hospital` - Reference to hospital
   - `hospital_name` - Hospital name (read-only)

3. **Updated validation**: Now validates that latitude and longitude are provided together

## Testing

### 1. Check Django Configuration
```bash
python manage.py check
# Should show: System check identified no issues (0 silenced).
```

### 2. Test Schema Generation
```bash
# Start server
python manage.py runserver

# Access in browser:
# - http://localhost:8000/api/docs/
# - http://localhost:8000/api/redoc/
# - http://localhost:8000/api/schema/
```

### 3. Test the Endpoint
```bash
# Get auth token first
curl -X POST http://localhost:8000/api/v1/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Update doctor location
curl -X PATCH http://localhost:8000/api/v1/doctors/1/location/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workplace": "City Hospital",
    "workplace_address": "123 Main St, Tashkent",
    "latitude": "41.2995",
    "longitude": "69.2401"
  }'
```

## Verification

✅ Django check passes without errors
✅ No `ImproperlyConfigured` exception
✅ Serializer only uses fields that exist on the model
✅ Proper validation for location data

## Impact

- **Before**: Schema generation crashed, API docs inaccessible
- **After**: Schema generates successfully, API docs work perfectly

## Files Modified

- `apps/doctors/serializers.py` - Line 427-460

## Related

- Main implementation: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- Security improvements: [API_SECURITY_IMPROVEMENTS.md](./API_SECURITY_IMPROVEMENTS.md)
- Quick start: [QUICK_START_API.md](./QUICK_START_API.md)

---

**Status**: ✅ Fixed and Tested
