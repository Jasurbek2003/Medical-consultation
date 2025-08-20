import requests
for i in range(100):
    try:
        response = requests.get('https://med.quloqai.uz/api/v1/doctors/public/detail/32/')
        print(f"Request {i+1}: Status Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Request {i+1} failed: {e}")