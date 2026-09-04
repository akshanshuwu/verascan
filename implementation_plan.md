# VeraScan — Implementation Plan

## Overview

Build the full VeraScan pipeline in 4 phases, starting with the foundation and working outward to the UI and polish. Each phase produces a working, testable piece.

---

## Phase 1: Foundation (Today, Sept 4)

### 1.1 Project Scaffolding

#### [NEW] Root project structure
- Initialize git repo at `/Users/akshanshsingh/VeraScan`
- Create `.gitignore` (Node, Python, env files, `__pycache__`, `.next`, `node_modules`)
- Create `.env.example` documenting all required keys

#### [NEW] `frontend/` — Next.js 14 App
- Scaffold with `npx create-next-app@latest ./frontend` (App Router, no Tailwind, no TypeScript for speed)
- Set up folder structure: `app/`, `components/`, `lib/`, `styles/`
- Install: `framer-motion`, `ethers`

#### [NEW] `backend/` — FastAPI
- Create `backend/` with `main.py`, `routers/`, `services/`, `models/`
- Create `requirements.txt`: `fastapi`, `uvicorn`, `python-multipart`, `Pillow`, `opencv-python-headless`, `google-search-results` (SerpAPI), `python-dotenv`, `requests`
- Create virtual environment and install deps

#### [NEW] `contracts/` — Hardhat + Solidity
- Scaffold with `npx hardhat init` inside `contracts/`
- Install: `@nomicfoundation/hardhat-toolbox`, `dotenv`

---

### 1.2 Smart Contract

#### [NEW] `contracts/contracts/VeraScan.sol`
- Implement `storeRecord`, `verifyRecord`, `getRecord` as specified in PRD
- Events: `RecordStored`, `RecordVerified`

#### [NEW] `contracts/test/VeraScan.test.js`
- Test: store a record, verify with correct hash (should pass)
- Test: verify with wrong hash (should fail)
- Test: duplicate record ID rejected
- Test: non-existent record query reverts

#### [NEW] `contracts/scripts/deploy.js`
- Deploy script targeting Sepolia
- Output deployed contract address

#### [NEW] `contracts/hardhat.config.js`
- Configure Sepolia network with Alchemy RPC URL
- Load private key from `.env`

**Verification**: `npx hardhat test` passes. Contract deploys to Sepolia. Contract address saved.

---

## Phase 2: Backend Pipeline (Sept 5, morning)

### 2.1 Face Detection Service

#### [MODIFY] `backend/services/face_detection.py`
- `detect_face(image_bytes) -> dict` using OpenCV Haar Cascades (`haarcascade_frontalface_default.xml`)
- Swapped from `deepface` due to Python 3.14/Apple Silicon compatibility issues with `tensorflow`.
- Handles: no face, multiple faces (pick largest), image too small
- Returns cropped face as base64, bounding box, confidence

#### [NEW] `backend/routers/face.py`
- `POST /api/detect-face` accepts `multipart/form-data`
- Validates file type (JPG, PNG, WebP) and size (< 10MB)
- Calls `face_detection.detect_face()` and returns JSON

### 2.2 Reverse Search Service

#### [NEW] `backend/services/reverse_search.py`
- `search_face(image_base64) -> dict` using SerpAPI Google Lens
- Saves temp image, uploads to SerpAPI, parses results
- Filters for social media domains, returns top 5 matches
- Cleans up temp files

#### [NEW] `backend/routers/search.py`
- `POST /api/search` accepts JSON with base64 image
- Calls `reverse_search.search_face()` and returns results

### 2.3 Hashing Service

#### [NEW] `backend/services/hasher.py`
- `hash_data(title, url, snippet, timestamp) -> str`
- SHA-256 of concatenated fields

#### [NEW] `backend/routers/hash.py`
- `POST /api/hash` accepts JSON, returns hash string

### 2.4 App Entry

#### [NEW] `backend/main.py`
- FastAPI app with CORS middleware
- Mount all routers
- Health check endpoint at `/api/health`

#### [NEW] `backend/models/schemas.py`
- Pydantic models for all request/response shapes

**Verification**: Start FastAPI with `uvicorn main:app --host 127.0.0.1 --port 8000`. Test endpoints using `backend/test_endpoints.py`. Face detection returns a cropped face. Search returns real results from SerpAPI.

---

## Phase 3: Frontend UI (Sept 5 afternoon + Sept 6 morning)

### 3.1 Design System & Stitch Exploration

- Use Stitch MCP to explore UI concepts for the pipeline interface
- Define color palette, typography scale, spacing system in `globals.css`
- No purple, no pills, no emoji icons — every choice intentional

#### [NEW] `frontend/styles/globals.css`
- CSS custom properties for colors, fonts, spacing, radii
- Base resets and typography rules

#### [NEW] `frontend/styles/typography.css`
- Font imports (Inter + Space Grotesk from Google Fonts)
- Heading hierarchy, body text, captions, labels

### 3.2 Core Components

#### [NEW] `frontend/components/FaceUploader.js`
- Drag-and-drop + click-to-upload zone
- File validation (type, size)
- Image preview before submission
- Clear/reset functionality

#### [NEW] `frontend/components/FacePreview.js`
- Shows the detected face crop with bounding box overlay on original
- Confidence indicator
- "Confirm & Search" action button

#### [NEW] `frontend/components/PipelineStepper.js`
- 4-step horizontal stepper: Upload → Detect → Search → Verify
- States: pending, active, processing, complete, error
- Smooth transitions between states
- Summary text under each completed step

#### [NEW] `frontend/components/SearchResult.js`
- Card displaying a matched post: title, source domain, snippet, thumbnail
- Link to original source
- "Verify this result" action

#### [NEW] `frontend/components/BlockchainProof.js`
- Displays: transaction hash (linked to Sepolia Etherscan), block number, timestamp
- "Re-verify" button
- Verification result badge (match/mismatch)

#### [NEW] `frontend/components/Footer.js`
- Links to Privacy Policy, Terms, GitHub repo
- No "made with AI" tag

### 3.3 Pages

#### [MODIFY] `frontend/app/page.js`
- Landing page with FaceUploader
- Pipeline stepper at top
- Minimal, direct copy (no vague hero text)

#### [NEW] `frontend/app/results/page.js`
- Display search results from API
- Each result has a "Verify on Blockchain" button
- Pipeline stepper shows Step 3 active

#### [NEW] `frontend/app/verify/page.js`
- Blockchain proof display
- Re-verification interface
- Pipeline stepper shows Step 4 complete

#### [NEW] `frontend/app/privacy/page.js`
- Real privacy policy content (data handling, face images not stored, etc.)

#### [NEW] `frontend/app/terms/page.js`
- Real terms & conditions content

#### [MODIFY] `frontend/app/layout.js`
- Global layout with fonts, metadata, favicon
- SEO tags: title, description, OG image

### 3.4 Blockchain Client

#### [NEW] `frontend/lib/blockchain.js`
- `storeRecord(id, dataHash, sourceUrl)` — calls smart contract
- `verifyRecord(id, dataHash)` — calls smart contract
- `getRecord(id)` — reads from smart contract
- Uses ethers.js v6 with Alchemy provider
- Server-side wallet (private key from env) for smooth demo — no MetaMask dependency

#### [NEW] `frontend/lib/api.js`
- `detectFace(imageFile)` — calls backend POST `/api/detect-face`
- `searchFace(imageBase64)` — calls backend POST `/api/search`
- `hashData(resultData)` — calls backend POST `/api/hash`

#### [NEW] `frontend/lib/constants.js`
- Contract address, ABI, Alchemy RPC URL, API base URL

**Verification**: Frontend runs with `npm run dev`. Can upload an image, see face preview. Pipeline stepper transitions work. Pages navigate correctly.

---

## Phase 4: Integration & Polish (Sept 6 afternoon + Sept 7)

### 4.1 End-to-End Wiring

- Connect frontend upload → backend face detection → display preview
- Connect confirm → backend search → display results
- Connect "Verify" button → hash → blockchain store → display proof
- Connect "Re-verify" → blockchain verify → display result
- Test full pipeline with a real face photo

### 4.2 Error Handling

- All API errors display user-friendly messages (not raw JSON)
- Network failures show retry options
- Blockchain failures show tx details for debugging
- Loading states for every async operation

### 4.3 Polish

- Review all spacing, typography, color consistency
- Test responsive layouts at all breakpoints
- Verify all animations are functional (not decorative excess)
- Favicon added
- OG image and meta tags
- Remove any "made with AI" artifacts

### 4.4 Legal Pages

- Write real privacy policy (what data we collect, how face images are handled, blockchain records)
- Write real terms (hackathon demo, no warranty, testnet only)

### 4.5 README

#### [MODIFY] `README.md`
- What VeraScan does
- Architecture diagram
- How to run locally (frontend, backend, contract deployment)
- Environment variables needed
- Which blockchain (Sepolia) and why
- Known limitations (from PRD Section 11)

### 4.6 Submission

- Screen recording of full pipeline (face upload → search → blockchain → verify)
- Push final code to GitHub
- Submit via Google Form

**Verification**: Full pipeline works end-to-end in screen recording. README is complete. Legal pages exist. No placeholder content. Repo is clean.

---

## Verification Plan

### Automated Tests
- `cd contracts && npx hardhat test` — Smart contract tests pass
- Backend endpoints return correct response shapes (manual curl tests)

### Manual Verification
- Upload a real face photo → face is detected and cropped correctly
- Cropped face → SerpAPI returns real search results (not hardcoded)
- Search result → SHA-256 hash → stored on Sepolia → tx hash is valid on Etherscan
- Re-verify → on-chain hash matches local hash → verification passes
- Screen recording captures the entire flow smoothly

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| SerpAPI free tier runs out | Test sparingly, use cached results during UI development |
| deepface installation issues (dlib) | **Mitigated**: Swapped to OpenCV Haar Cascades for face detection |
| Sepolia faucet slow/empty | Get test ETH from multiple faucets early (Day 1) |
| UI takes too long | Use Stitch to accelerate design exploration, don't over-polish |
| Face detection fails on poor photos | Document as known limitation, test with clear headshots |
