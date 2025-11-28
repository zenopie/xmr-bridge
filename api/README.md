# XMR Bridge API Documentation

REST API for frontend integration with the Monero to Secret Network bridge.

## 🚀 Quick Start

FastAPI provides **automatic interactive documentation**:

- **Swagger UI**: http://localhost:8000/docs (try endpoints directly!)
- **ReDoc**: http://localhost:8000/redoc (clean reference)

This document provides **frontend integration examples** and usage patterns.

## Base URL

```
Development: http://localhost:8000
Production:  https://your-domain.com
```

## Endpoints

### 1. Health Check

**GET** `/`

Check if the API is online.

**Response:**
```json
{
  "status": "online",
  "service": "XMR Bridge API",
  "version": "1.0.0"
}
```

---

### 2. Generate Deposit Address

**POST** `/api/deposit-address`

Generate a unique Monero deposit address for a user.

**Request Body:**
```json
{
  "secret_address": "secret1abc123def456..."
}
```

**Response:**
```json
{
  "secret_address": "secret1abc123def456...",
  "monero_address": "8AbC...XyZ",
  "created_at": "2025-01-27T12:34:56.789Z"
}
```

**Frontend Usage:**
```javascript
// When user clicks "Deposit"
const response = await fetch('http://localhost:8000/api/deposit-address', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    secret_address: userWalletAddress
  })
});

const { monero_address } = await response.json();
// Display monero_address as QR code for user to send XMR to
```

---

### 3. Get Deposit Status

**GET** `/api/deposit/{tx_hash}`

Get status and confirmations for a specific Monero deposit.

**Response:**
```json
{
  "tx_hash": "abc123...",
  "amount": 1000000000000,
  "confirmations": 5,
  "required_confirmations": 10,
  "status": "confirming",
  "monero_address": "8AbC...XyZ",
  "secret_address": "secret1...",
  "secret_tx_hash": null,
  "block_height": 2891234,
  "processed_at": null
}
```

**Status Values:**
- `"pending"` - Detected but 0 confirmations
- `"confirming"` - Has confirmations but not enough yet
- `"completed"` - Fully confirmed and sXMR minted

**Frontend Usage:**
```javascript
// Poll every 10 seconds to show confirmation progress
setInterval(async () => {
  const response = await fetch(`http://localhost:8000/api/deposit/${txHash}`);
  const deposit = await response.json();

  updateProgressBar(deposit.confirmations, deposit.required_confirmations);

  if (deposit.status === 'completed') {
    showSuccess(`sXMR minted! Tx: ${deposit.secret_tx_hash}`);
    clearInterval(this);
  }
}, 10000);
```

---

### 4. Get All Deposits for User

**GET** `/api/deposits/{secret_address}`

Get deposit history for a Secret Network address.

**Response:**
```json
[
  {
    "tx_hash": "abc123...",
    "amount": 1000000000000,
    "confirmations": 15,
    "required_confirmations": 10,
    "status": "completed",
    "monero_address": "8AbC...XyZ",
    "secret_address": "secret1...",
    "secret_tx_hash": "def456...",
    "block_height": 2891234,
    "processed_at": "2025-01-27T12:45:00.000Z"
  }
]
```

---

### 5. Get All Withdrawals for User

**GET** `/api/withdrawals/{secret_address}`

Get withdrawal history for a Secret Network address.

**Response:**
```json
[
  {
    "secret_tx_hash": "def456...",
    "amount": 500000000000,
    "monero_address": "4xYz...AbC",
    "monero_tx_hash": "ghi789...",
    "status": "completed",
    "processed_at": "2025-01-27T13:00:00.000Z"
  }
]
```

**Status Values:**
- `"pending"` - Burn detected, not yet processed
- `"processing"` - XMR transaction being created
- `"completed"` - XMR sent

---

### 6. Get Complete Transaction History

**GET** `/api/history/{secret_address}`

Get complete transaction history with totals.

**Response:**
```json
{
  "secret_address": "secret1...",
  "deposits": [...],
  "withdrawals": [...],
  "total_deposited": 1500000000000,
  "total_withdrawn": 500000000000
}
```

**Frontend Usage:**
```javascript
// User's dashboard
const response = await fetch(`http://localhost:8000/api/history/${userAddress}`);
const history = await response.json();

displayTotalBalance(history.total_deposited - history.total_withdrawn);
displayDepositList(history.deposits);
displayWithdrawalList(history.withdrawals);
```

---

### 7. WebSocket - Real-Time Updates

**WebSocket** `/ws`

Connect for real-time updates on deposits and withdrawals.

**Messages Received:**

**Deposit Update:**
```json
{
  "type": "deposit_update",
  "tx_hash": "abc123...",
  "confirmations": 6,
  "timestamp": "2025-01-27T12:34:56.789Z"
}
```

**Deposit Completed:**
```json
{
  "type": "deposit_completed",
  "monero_tx_hash": "abc123...",
  "secret_tx_hash": "def456...",
  "timestamp": "2025-01-27T12:45:00.000Z"
}
```

**Frontend Usage:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'deposit_update') {
    updateConfirmationCount(data.tx_hash, data.confirmations);
  }

  if (data.type === 'deposit_completed') {
    showNotification('Deposit complete!', data.secret_tx_hash);
    refreshBalance();
  }
};

ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = () => console.log('WebSocket disconnected');
```

---

## Error Responses

All endpoints return standard HTTP status codes:

- `200` - Success
- `404` - Not found
- `500` - Server error
- `503` - Service unavailable (bridge not initialized)

**Error Format:**
```json
{
  "detail": "Error message here"
}
```

---

## CORS

The API has CORS enabled for all origins in development. In production, configure `allow_origins` in `api.py` to your frontend domain.

---

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Use these for testing endpoints directly in the browser!

---

## Example Frontend Flow

### Deposit Flow:

1. User enters their Secret Network address
2. Frontend calls `POST /api/deposit-address` → Gets Monero address
3. Display Monero address as QR code
4. User sends XMR from their Monero wallet
5. User pastes transaction hash
6. Frontend polls `GET /api/deposit/{tx_hash}` every 10s
7. Show confirmation progress (5/10 confirmations)
8. When status = "completed", show success + Secret tx hash

### Withdrawal Flow:

1. User burns sXMR on Secret Network via contract
2. Frontend calls `GET /api/withdrawals/{address}` to show status
3. When status = "completed", show Monero tx hash

### Dashboard:

1. On page load, call `GET /api/history/{address}`
2. Display total balance, deposit list, withdrawal list
3. Connect to WebSocket for live updates
4. Update UI when new events arrive
