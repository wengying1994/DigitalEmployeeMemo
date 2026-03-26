# Multi-Account Memo System Backend

## Project Overview
- **Project name**: Digital Employee Memo
- **Type**: REST API Backend
- **Core functionality**: Multi-account memo system where each account stores memos in individual xlsx files
- **Target users**: External systems accessing via curl/HTTP

## Technical Stack
- Python 3.x with Flask
- openpyxl for xlsx file handling
- Data stored as xlsx files (one per account)

## Functionality Specification

### Core Features
1. **Account Management**
   - Auto-create account xlsx file on first access
   - Each account file: `data/{account_id}.xlsx`

2. **Memo Operations** (CRUD)
   - `POST /api/accounts/{account_id}/memos` - Create memo
   - `GET /api/accounts/{account_id}/memos` - List all memos
   - `GET /api/accounts/{account_id}/memos/{memo_id}` - Get single memo
   - `PUT /api/accounts/{account_id}/memos/{memo_id}` - Update memo
   - `DELETE /api/accounts/{account_id}/memos/{memo_id}` - Delete memo

3. **Data Model - Memo**
   - `id`: string (UUID)
   - `title`: string (required, max 200 chars)
   - `content`: string (optional)
   - `created_at`: datetime (ISO 8601)
   - `updated_at`: datetime (ISO 8601)

4. **XLSX Structure**
   - Sheet name: "Memos"
   - Columns: id, title, content, created_at, updated_at

### API Response Format
```json
{
  "success": true,
  "data": {...}
}
```

### Error Handling
- 400: Bad request (missing fields, invalid data)
- 404: Account or memo not found
- 500: Server error

## Project Structure
```
/Users/pea/Desktop/helloworld/DigitalEmployeeMemo/
├── app.py              # Flask application
├── data/               # Directory for xlsx files
├── requirements.txt    # Dependencies
└── SPEC.md
```

## Acceptance Criteria
1. Each account's memos are stored in a separate xlsx file
2. All CRUD operations work correctly via curl
3. Xlsx file is auto-created when account is first accessed
4. Proper JSON responses for all endpoints
5. Timestamps are maintained correctly on create/update
