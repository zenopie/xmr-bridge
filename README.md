# Simple XMR Bridge

A simple, centralized bridge between Monero and Secret Network that allows users to:
- Deposit XMR and receive wrapped sXMR on Secret Network
- Burn sXMR and withdraw XMR

## Architecture

This is a **centralized bridge** where a single operator:
1. Controls a Monero wallet
2. Generates unique deposit subaddresses for users
3. Monitors deposits and mints sXMR on Secret Network
4. Monitors sXMR burns and sends XMR back to users

## Features

- **Per-user deposit addresses**: Each user gets a unique Monero subaddress
- **Automatic minting**: When XMR is deposited, sXMR is automatically minted
- **Bidirectional**: Supports both deposits (XMR→sXMR) and withdrawals (sXMR→XMR)
- **External node support**: Uses public Monero nodes, no need to run your own

## Setup

### Prerequisites

- Python 3.9+
- A Monero wallet (address + view key for monitoring deposits)
- A Secret Network wallet (mnemonic for signing transactions)
- An sXMR SNIP-20 contract deployed on Secret Network

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/xmr-bridge
cd xmr-bridge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example env file
cp .env.example .env

# Edit configuration
vim .env
```

### Configuration

Edit `.env` with your settings:

```bash
# Monero Configuration
MONERO_RPC_URL=http://node.moneroworld.com:18089/json_rpc
MONERO_NETWORK=mainnet
MONERO_WALLET_ADDRESS=your_monero_primary_address
MONERO_VIEW_KEY=your_private_view_key

# Secret Network Configuration
SECRET_NETWORK_RPC=https://lcd.mainnet.secretsaturn.net
SECRET_NETWORK_CHAIN_ID=secret-4
SECRET_WALLET_MNEMONIC=your 24 word mnemonic here
SXMR_CONTRACT_ADDRESS=secret1...
SXMR_CONTRACT_HASH=contract_code_hash

# Bridge Settings
MIN_CONFIRMATIONS=10
POLL_INTERVAL=60
```

### Running the Bridge

```bash
# Activate virtual environment
source venv/bin/activate

# Set log level (optional)
export LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR

# Run the bridge
python main.py
```

## How It Works

### Deposit Flow

1. User requests a deposit address from the bridge operator
2. Bridge generates a unique Monero subaddress mapped to the user's Secret address
3. User sends XMR to the subaddress
4. Bridge monitors the blockchain and detects the deposit
5. After `MIN_CONFIRMATIONS`, bridge mints equivalent sXMR to the user's Secret address

### Withdrawal Flow

1. User burns sXMR on Secret Network and includes their Monero address
2. Bridge monitors the Secret Network contract for burn events
3. Bridge sends XMR from its wallet to the user's Monero address

## API

The bridge can expose a simple API for generating deposit addresses:

```python
# Generate deposit address for a user
deposit_address = bridge.generate_deposit_address("secret1...")
```

## Security Considerations

**WARNING**: This is a centralized bridge. The operator has full control over deposited funds.

- The operator controls the Monero wallet's spend key
- The operator controls the Secret Network mnemonic that can mint sXMR
- Users must trust the operator to honor withdrawals
- Consider implementing:
  - Multi-signature requirements
  - Time locks
  - Proof of reserves
  - Regular audits

## Development

### Project Structure

```
xmr-bridge/
├── bridge.py           # Main bridge logic
├── main.py             # Entry point
├── requirements.txt    # Dependencies
├── .env.example        # Example configuration
└── README.md          # This file
```

### TODO

- [ ] Implement Monero subaddress generation
- [ ] Implement deposit monitoring via Monero node
- [ ] Implement Secret Network client for minting sXMR
- [ ] Implement withdrawal monitoring
- [ ] Add database for persistent address mappings
- [ ] Add REST API for generating deposit addresses
- [ ] Add proof of reserves
- [ ] Add multi-signature support

## License

MIT

## Disclaimer

This is experimental software. Do not use with real funds without thorough testing and security audits. The centralized nature of this bridge means users must fully trust the operator.
