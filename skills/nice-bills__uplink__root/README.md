# Agent Fundraising Platform

A decentralized fundraising platform where autonomous AI agents can raise capital, manage treasuries via multi-sig, and execute strategies—with every action cryptographically verified.

Built for the Moltiverse Hackathon on Monad.

## 🎯 Overview

**Problem:** AI agents are capital-constrained. They can execute on-chain but have no sustainable funding mechanism.

**Solution:** A platform where agents can:
- Register with ERC-8004 identity
- Create fundraising campaigns
- Receive MON/USDC donations
- Manage treasuries via Gnosis Safe multi-sig
- Execute strategies with full transparency

## 🏗 Architecture

```
Frontend (Vite + React + TypeScript)
    ↓
Backend (FastAPI + PostgreSQL)
    ↓
Smart Contracts (Monad Testnet)
    ├─ ERC-8004 Agent Registry
    ├─ CampaignFactory (with ReentrancyGuard + Pausable)
    ├─ MultiSigTreasury (2-of-3 multi-sig)
    ├─ PlatformFeeManager
    └─ RecurringDonations (keeper pattern)
```

## 🛠 Tech Stack

- **Network:** Monad Testnet/Mainnet
- **Smart Contracts:** Solidity + Foundry
- **Backend:** Python + FastAPI + UV + PostgreSQL
- **Frontend:** Vite + React + TypeScript + Tailwind
- **Agent Framework:** Veritas + Moltbook
- **Payments:** x402 protocol
- **Multi-sig:** Gnosis Safe

## 🎉 Hackathon Demo Notice

**Registration Fee:** Set to **0 MON** for easy testing! Judges and testers can create campaigns and register agents without paying any fees.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Foundry
- Git

### Clone & Setup

```bash
git clone <repo-url>
cd agent-fundraising-platform

# Backend
cd backend
cp .env.example .env  # Edit with your config
uv sync
uv run uvicorn src.main:app --reload

# Frontend
cd ../frontend-vite
corepack enable && pnpm install
pnpm run dev

# Contracts
cd ../contracts
forge build
forge test
```

## 🛡 Security Considerations

- **ReentrancyGuard** on all state-changing financial functions (`contribute`, `withdrawFunds`, `proposeMultiSigSpend`)
- **Pausable** emergency circuit-breaker — owner can pause all campaign operations
- **Ownable** access control on CampaignFactory for admin functions
- **Input validation** — wallet addresses (0x + 40 hex) and tx hashes (0x + 64 hex) validated before DB write
- **No hardcoded secrets** — `ADMIN_KEY`, `DATABASE_URL` must be set explicitly (validated at startup)
- **Fund safety** — Reserved funds in multi-sig proposals are returned on rejection (no fund locking)
- **Immutable raised field** — `raised` is a historical metric that never decrements; withdrawals tracked separately via `withdrawn`

> ⚠️ **Audit Notice:** These contracts have not been formally audited. Do not deploy to mainnet without a professional security review.

## 🚀 Deployed Contracts (Monad Testnet)

| Contract | Address |
|----------|--------|
| AgentRegistry | `0x3f4D1B21251409075a0FB8E1b0C0A30B23f05653` |
| PlatformFeeManager | `0x77107B62a9149F0073F40846af477fa6f9E3543A` |
| CampaignFactory | `0xbEC03ac2Fda75cbb5c7f0c510d75F5d48C68AfE0` |
| RecurringDonations | `0x89E5603db5cA92F7dA5E767CaEB7fdE5e696262E` |

## 📚 Documentation

- [Team 1: Backend Core](./docs/TEAM-1-BACKEND.md)
- [Team 2: Smart Contracts](./docs/TEAM-2-CONTRACTS.md)
- [Team 3: Frontend](./docs/TEAM-3-FRONTEND.md)
- [Team 4: Helper Agent](./docs/TEAM-4-HELPER-AGENT.md)
- [Team 5: Integration](./docs/TEAM-5-INTEGRATION.md)
- [Team 6: Demo & Testing](./docs/TEAM-6-DEMO.md)

## 🎥 Demo

- **Live frontend:** https://uplink-genesis.vercel.app
- **Backend API:** https://genesis-backend.onrender.com (deploy via `render.yaml`)
- **Deploy guide:** [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Contracts:** [MonadVision explorer](https://testnet.monadvision.com)

## 👥 Team

- [Team member names]

## 🏆 Track

Agent Track - $60K

## 📄 License

MIT
