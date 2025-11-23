# XMR Bridge - Monero to Secret Network MPC Bridge

A trustless, decentralized bridge from Monero to Secret Network using Multi-Party Computation (MPC) and FROST threshold signatures.

## Overview

This bridge enables users to lock Monero (XMR) and mint wrapped tokens on Secret Network, and vice versa. The bridge is secured by a threshold signature scheme using FROST (Flexible Round-Optimized Schnorr Threshold signatures), ensuring no single party controls the bridged funds.

### Key Features

- **Monerod Integration**: Connects to monerod via RPC, allowing you to run mining and the bridge on the same machine
- **FROST Threshold Signatures**: Implements Ed25519 threshold signatures for secure, distributed key management
- **MPC Architecture**: No single point of failure - requires threshold of participants to sign any transaction
- **Deposit Monitoring**: Automatically detects and verifies Monero deposits
- **Withdrawal Processing**: Coordinates threshold signing for Monero withdrawals
- **Secret Network Integration**: Interfaces with Secret Network smart contracts for wrapped token management

## Architecture

### Components

```
xmr-bridge/
├── core/              # Core types and errors
│   ├── __init__.py
│   ├── types.py
│   └── errors.py
├── monero/            # Monerod RPC integration
│   ├── __init__.py
│   ├── node.py
│   ├── deposit_monitor.py
│   └── withdrawal.py
├── frost/             # FROST threshold signature implementation
│   ├── __init__.py
│   ├── coordinator.py
│   └── participant.py
├── network/           # P2P networking for MPC coordination
│   ├── __init__.py
│   └── p2p.py
├── secret/            # Secret Network client
│   ├── __init__.py
│   └── client.py
├── bridge.py          # Main bridge orchestrator
├── config.py          # Configuration management
├── main.py            # Entry point
├── config.example.toml
├── requirements.txt
└── pyproject.toml
```

### Technology Stack

- **Language**: Python 3.9+
- **Monero Node**: [monerod](https://github.com/monero-project/monero) - Monero daemon with RPC interface
- **HTTP Client**: [aiohttp](https://github.com/aio-libs/aiohttp) - Async HTTP for RPC calls
- **Threshold Signatures**: FROST Ed25519 implementation
- **P2P Networking**: Custom async networking (can be upgraded to py-libp2p)
- **Secret Network**: CosmWasm smart contracts

## How It Works

### Deposit Flow

1. User sends XMR to a bridge-controlled Monero address
2. Each bridge node monitors the Monero blockchain via monerod RPC
3. Once minimum confirmations reached, nodes coordinate to:
   - Generate a deposit proof using FROST signatures
   - Submit proof to Secret Network contract
4. Secret Network contract mints wrapped XMR tokens to the user

### Withdrawal Flow

1. User burns wrapped XMR on Secret Network and requests withdrawal
2. Bridge nodes detect the withdrawal request
3. Nodes coordinate using FROST to:
   - Create a Monero withdrawal transaction
   - Generate threshold signature shares
   - Aggregate shares into final signature
4. Signed transaction is broadcast to Monero network
5. User receives XMR on Monero

## Setup

### Prerequisites

- Python 3.9+
- Git
- [Monerod](https://github.com/monero-project/monero) - Monero daemon running locally or accessible via RPC

**Note**: You need a running monerod instance. This can be the same instance you use for mining, making it easy to run both the bridge and mining on the same machine.

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

# Or install in development mode
pip install -e .

# Copy example config
cp config.example.toml config.toml

# Edit configuration
vim config.toml
```

### Configuration

First, start monerod:

```bash
# Start monerod with RPC enabled
monerod --rpc-bind-port 18081 --confirm-external-bind --rpc-access-control-origins "*"

# Or to enable mining on the same machine:
monerod --rpc-bind-port 18081 --confirm-external-bind --rpc-access-control-origins "*" \
  --start-mining YOUR_WALLET_ADDRESS --mining-threads 4
```

Then edit `config.toml`:

```toml
# Participant settings
participant_id = 1          # Unique ID for this node (1 to total_participants)
threshold = 2               # Minimum signatures required
total_participants = 3      # Total number of MPC participants

# Monero settings (monerod RPC)
monero_rpc_url = "http://127.0.0.1:18081/json_rpc"
# monero_rpc_user = "username"  # Optional: if RPC authentication is enabled
# monero_rpc_password = "password"  # Optional: if RPC authentication is enabled
monero_network = "mainnet"

# Secret Network settings
secret_network_rpc = "http://localhost:26657"
secret_network_chain_id = "secret-4"

# Bridge settings
min_confirmations = 10      # Monero confirmations before processing deposit

# P2P network settings
listen_address = "/ip4/0.0.0.0/tcp/9000"
peer_addresses = [
    "/ip4/peer1.example.com/tcp/9000",
    "/ip4/peer2.example.com/tcp/9000"
]
```

### Running a Node

```bash
# Make sure monerod is running first

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Set log level (optional)
export LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR

# Run the bridge node
xmr-bridge

# Or run directly with Python
python main.py
```

## Monerod Integration

This bridge connects to a monerod instance via RPC, providing several advantages:

### Why Monerod?

1. **Mining Support**: Run mining and the bridge on the same machine
2. **Production Ready**: Monerod is the official, battle-tested Monero implementation
3. **Full Features**: Access to all Monero network capabilities including mining
4. **Separation of Concerns**: Bridge logic is separate from the blockchain node
5. **Flexible Deployment**: Connect to local or remote monerod instances

### Setup for Mining + Bridge

To run both mining and the bridge on the same machine:

1. Start monerod with mining enabled:
```bash
monerod --rpc-bind-port 18081 --confirm-external-bind \
  --rpc-access-control-origins "*" \
  --start-mining YOUR_WALLET_ADDRESS --mining-threads 4
```

2. Configure the bridge to connect to your local monerod
3. Run the bridge - it will use the same monerod instance

This allows you to contribute to Monero network security while running bridge operations.

## MPC and FROST

### Distributed Key Generation (DKG)

On first startup, bridge participants run a DKG protocol to generate a shared public key. Each participant receives a secret share, and `threshold` shares are required to sign.

### Signing Protocol

When a withdrawal needs to be signed:

1. **Round 1**: Each participant generates and broadcasts commitments
2. **Round 2**: Each participant creates their signature share
3. **Aggregation**: Once threshold shares collected, signature is aggregated
4. **Broadcast**: Final signed transaction is broadcast to Monero network

The bridge never reconstructs the private key - signatures are created through MPC.

## Development

### Project Structure

- **`core/`**: Common types and errors used across all modules
- **`monero/`**: Monerod RPC client, deposit monitoring, withdrawal creation
- **`frost/`**: FROST DKG, signing, and coordination
- **`network/`**: Async P2P communication between MPC participants
- **`secret/`**: Secret Network RPC client and contract interfaces
- **`bridge.py`**: Main bridge orchestrator
- **`config.py`**: Configuration management
- **`main.py`**: Application entry point

### Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=.

# Format code
black .

# Type checking
mypy .

# Linting
ruff check .
```

### Adding Features

The codebase is designed for extensibility:

- Add new message types in `network/p2p.py`
- Add new error types in `core/errors.py`
- Extend monerod RPC integration in `monero/node.py`
- Implement FROST protocols in `frost/`

## Security Considerations

### Threat Model

- **No single point of failure**: Requires threshold participants to compromise
- **Byzantine fault tolerance**: Can tolerate up to `total_participants - threshold` malicious nodes
- **Deposit proofs**: Cryptographically verified using FROST signatures
- **Withdrawal authentication**: Multi-signature approval required

### Best Practices

1. **Key Management**: Secret shares should be encrypted at rest
2. **Network Security**: Use TLS for P2P communication in production
3. **Monitoring**: Monitor for unusual deposit/withdrawal patterns
4. **Updates**: Keep monerod and dependencies updated
5. **Monerod Security**: Secure your monerod RPC endpoint, use authentication in production

## Roadmap

- [x] Core architecture with monerod RPC integration
- [x] FROST threshold signature implementation
- [x] P2P communication layer
- [x] Deposit monitoring framework
- [x] Withdrawal coordination
- [ ] Production key management and HSM support
- [ ] Secret Network contract development
- [ ] Comprehensive testing suite
- [ ] Security audit
- [ ] Mainnet deployment

## Contributing

Contributions are welcome! Areas of focus:

- Monerod RPC integration improvements
- FROST protocol optimizations
- Security enhancements
- Testing and documentation

## License

MIT

## Acknowledgments

- [Monero Project](https://github.com/monero-project/monero) - Privacy-focused cryptocurrency
- [FROST](https://github.com/ZcashFoundation/frost) - Threshold signature library
- [Secret Network](https://scrt.network/) - Privacy-preserving smart contracts
- Monero community

---

**Note**: This is experimental software under active development. Do not use with real funds until thoroughly audited.
