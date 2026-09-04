# VeraScan — Task Tracker

## Current State / Handoff Notes for OpenCode
* **Backend Architecture Swap**: Due to Python 3.14 compatibility issues with `tensorflow` and `mediapipe` on Apple Silicon, we replaced `deepface` with **OpenCV Haar Cascades** for face detection. This is fully implemented, lightweight, and tested. The Haar cascade XML is stored locally in the `backend/` folder.
* **Backend Environment**: Uses a virtual environment (`backend/venv`). Start the server with `cd backend && source venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8000`. Tests are available in `backend/test_endpoints.py`.
* **Frontend Environment**: A Next.js 14 App Router project exists in `frontend/`. Dependencies are installed. No UI implementation has been done yet. Start with `cd frontend && npm run dev`.
* **Smart Contract / Blockchain**: The Solidity contract (`contracts/contracts/VeraScan.sol`) is fully tested (11/11 passing via Hardhat).
* **Environment Variables**: `.env` (root), `backend/.env`, `frontend/.env.local` are populated locally (SERPAPI_KEY, ALCHEMY_RPC_URL, DEPLOYER_PRIVATE_KEY). Never commit.
* **Contract deployed**: `0x0fb9824673d027Fb2f2fC629706C2e1E24C39408` on Sepolia. Smoke-tested store + getRecord. Wallet `0xc3f2c045023290722e9Ec18CE0Fb6b8FeB4959F7` funded (0.132 ETH at deploy).
* **Search fix**: `services/reverse_search.py` now uploads crop to Catbox (fallback tmpfiles) and passes public URL to SerpAPI Google Lens. Live-tested: 5 results, social-first.

## Phase 1: Foundation (Sept 4)
- [x] Project scaffolding (.gitignore, .env.example)
- [x] Next.js frontend scaffold + deps (framer-motion, ethers)
- [x] FastAPI backend scaffold (main.py, routers, services, models, schemas)
- [x] Backend deps installed (Swapped `deepface` → OpenCV Haar Cascades for Python 3.14 compat)
- [x] Hardhat contracts scaffold + deps installed
- [x] Smart contract (VeraScan.sol)
- [x] Smart contract tests — **11/11 passing**
- [x] Deploy script + Hardhat config
- [x] Verify the backend starts correctly and endpoints (/api/health, /api/detect-face, /api/hash) are functional.
- [x] Deploy contract to Sepolia — `0x0fb9824673d027Fb2f2fC629706C2e1E24C39408`, smoke tx `0x4c8518b2e484e6bfdc9de9fc4ddb4c7e32b46c4af902070a5279bbe16bdf2daf` block 11632995

## Phase 2: Backend Pipeline (Sept 5 AM)
- [x] Test face detection with a real image (Tested successfully via `test_endpoints.py`)
- [x] Test hashing endpoint (Tested successfully via `test_endpoints.py`)
- [x] Implement & Test reverse search with SerpAPI (`/api/search`) — fixed public-URL upload, live test returned 5 results
- [x] End-to-end backend pipeline test — detect → search → hash all 200 OK

## Phase 3: Frontend UI (Sept 5 PM + Sept 6 AM)
- [x] Design system (globals.css — warm paper + burnt orange, Inter + Space Grotesk, 5px buttons)
- [x] Core components (Uploader, Preview, Stepper, Result, Proof, Footer)
- [x] Pages (Home `/`, Results `/results`, Verify `/verify`, Privacy `/privacy`, Terms `/terms`)
- [x] Blockchain client (ethers.js v6 + server `/api/store` wallet, read-only re-verify)
- [x] API client (`lib/api.js`: detectFace, searchFace, hashData)

## Phase 3b: Synex-style premium rebuild (approved copy, no fake metrics)
- [x] Landing hero (two-tone H1, CTAs, three.js proof-lattice scene + poster/reduced-motion fallbacks)
- [x] Live proof strip (recordCount from Sepolia, contract Etherscan link)
- [x] Tilt hook + glass stage cards with outline numerals
- [x] How-it-works, architecture diagram, honest limits sections

## Phase 4: Integration & Polish (Sept 6 PM + Sept 7)
- [x] End-to-end wiring (home pipeline + sessionStorage handoff to /results + /verify)
- [x] History archive (`src/lib/history.js` localStorage, metadata-only, cap 20; archive section inside `/results` with per-entry delete + clear-all; append on search + store; clear-current buttons on /results + /verify)
- [x] Error handling (friendly messages for no-face, no-results, rate-limit, tx fail + retry)
- [x] Responsive testing (CSS breakpoints at 768px; `npm run build` passes)
- [x] Favicon + meta tags (`src/app/icon.svg`, layout metadata)
- [x] Legal pages content
- [x] README
- [ ] Screen recording
- [ ] Submission
