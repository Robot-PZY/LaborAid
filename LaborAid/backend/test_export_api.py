"""Test export API with real backend."""
import requests
import json

# Login first - try user 3 (3160401180@qq.com) who owns the test document
r = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'email': '3160401180@qq.com',
    'password': 'admin123'
})
print('Login:', r.status_code)
if r.status_code == 200:
    token = r.json().get('access_token', '')
    headers = {'Authorization': f'Bearer {token}'}

    # List documents
    r = requests.get('http://localhost:8000/api/v1/documents', headers=headers)
    print('List docs:', r.status_code)
    docs = r.json() if r.status_code == 200 else []
    print(f'Found {len(docs)} documents')

    if docs:
        doc_id = docs[0]['id']
        doc_title = docs[0]['title']
        print(f'Testing export for doc {doc_id}: {doc_title}')

        # Test Word export
        r = requests.post(
            f'http://localhost:8000/api/v1/documents/{doc_id}/export',
            headers=headers,
            json={'format': 'docx'}
        )
        if r.status_code == 200:
            print(f'Word export: OK ({len(r.content)} bytes)')
        else:
            print(f'Word export: {r.status_code} - {r.text[:500]}')

        # Test PDF export
        r = requests.post(
            f'http://localhost:8000/api/v1/documents/{doc_id}/export',
            headers=headers,
            json={'format': 'pdf'}
        )
        if r.status_code == 200:
            print(f'PDF export: OK ({len(r.content)} bytes)')
        else:
            print(f'PDF export: {r.status_code} - {r.text[:500]}')

        # Test HTML export
        r = requests.post(
            f'http://localhost:8000/api/v1/documents/{doc_id}/export',
            headers=headers,
            json={'format': 'html'}
        )
        if r.status_code == 200:
            print(f'HTML export: OK ({len(r.content)} bytes)')
        else:
            print(f'HTML export: {r.status_code} - {r.text[:500]}')
    else:
        print('No documents found in database')
else:
    print('Login failed:', r.text[:200])
