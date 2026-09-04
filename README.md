# VeraScan — Face to Blockchain Verification

Face photo in, tamper-proof proof out. Upload a face, discover matching public web content through genuine reverse-image search, independently verify the match with local face recognition, and anchor a SHA-256 fingerprint of the verified evidence on Ethereum Sepolia.

**Pipeline:** Upload → Detect (OpenCV Haar) → Encode (YuNet + SFace 128-D) → Discover (SerpAPI Google Lens: exact + visual matches) → Independently verify (cosine similarity vs threshold) → Fingerprint (SHA-256 of matched URL + image bytes) → Store (`VeraScan.storeRecord` on Sepolia) → Read-only re-verify.

Google Lens DISCOVERS. SFace independently COMPARES. SHA-256 FINGERPRINTS. Ethereum Sepolia ANCHORS. Read-only verification PROVES whether the evidence fingerprint still matches.

## Architecture

```
Browser (Next.js 16, React 19, ethers v6)
  → FastAPI backend (:8000): /api/detect-face, /api/search, /api/hash, /api/health
  → SerpAPI Google Lens (via public Catbox/tmpfiles upload; exact_matches + visual_matches)
  → Independent verification (YuNet detection + SFace 128-D embeddings, cosine similarity, FACE_MATCH_THRESHOLD)
  → Ethereum Sepolia via Alchemy: 0x0fb9824673d027Fb2f2fC629706C2e1E24C39408
```

Only the evidence fingerprint (SHA-256 of matched URL + raw candidate image bytes) and the source URL go on-chain. Images never touch the chain and are never stored on the server. Embeddings never leave the backend and are never sent to the frontend.

## Face recognition

- **Detection (primary):** OpenCV Haar Cascade (`/api/detect-face`) — unchanged.
- **Recognition (verification):** YuNet (`face_detection_yunet_2023mar.onnx`, ~0.22 MB) for alignment-quality boxes + landmarks, SFace (`face_recognition_sface_2021dec.onnx`, ~36.9 MB) for 128-D L2-normalized embeddings, cosine similarity (higher = more similar). Zero new pip dependencies — both run on the already-installed `opencv-contrib-python` (Python 3.14 + Apple Silicon safe).
- **Threshold:** `FACE_MATCH_THRESHOLD` env var (default `0.50`). Calibrated locally: same-person pairs 0.92–1.00, different-person ~0.16. Candidates score `>= threshold` become `match: true`; everything else stays visible with scores but can never anchor on-chain.
- **Models:** lazy-downloaded once from the OpenCV Zoo (Apache-2.0) into git-ignored `backend/models/`, SHA-256 pinned in `services/face_recognition.py`. Never downloaded per-request.

## Run locally

**1. Env** — copy and fill:
```bash
cp .env.example .env
# backend/.env: SERPAPI_KEY, FACE_MATCH_THRESHOLD (default 0.50)
# frontend/.env.local: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_CONTRACT_ADDRESS, NEXT_PUBLIC_ALCHEMY_RPC_URL + server ALCHEMY_RPC_URL, CONTRACT_ADDRESS, DEPLOYER_PRIVATE_KEY
```

**2. Backend:**
```bash
cd backend && source venv/bin/activate && pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
python test_endpoints.py  # health, detect-face, hash
python -m pytest tests/test_face_matching.py  # 14 embedding/verification/fingerprint tests
python calibrate_threshold.py  # similarity distribution check
```

**3. Contracts:**
```bash
cd contracts && npm install
npx hardhat test                    # 11/11 passing
npx hardhat run scripts/deploy.js --network sepolia
```

**4. Frontend:**
```bash
cd frontend && npm install && npm run dev  # http://localhost:3000
```

Routes: `/` pipeline, `/results` session results, `/verify` proof + manual re-verify, `/privacy`, `/terms`. Store txs go through `POST /api/store` (server-side wallet, no MetaMask needed).

## Blockchain

- Network: Ethereum Sepolia testnet, Alchemy RPC
- Contract: `contracts/contracts/VeraScan.sol` — `storeRecord(bytes32,string,string)`, `verifyRecord`, `getRecord`, `recordCount`
- Deployed: `0x0fb9824673d027Fb2f2fC629706C2e1E24C39408` ([Sepolia Etherscan](https://sepolia.etherscan.io/address/0x0fb9824673d027Fb2f2fC629706C2e1E24C39408))
- Verify: recompute SHA-256 of matched URL + image bytes, compare with `getRecord(id).dataHash`. Re-verify UI reports `Evidence fingerprint matches on-chain record` or `Tamper detected`.

## What VeraScan does NOT prove

- Account ownership, legal identity, or that a person controls a social-media account.
- That a biometric match is infallible — it establishes measured similarity (cosine score vs threshold), nothing more.

## What VeraScan DOES demonstrate

1. Genuine web discovery (SerpAPI Google Lens, never hardcoded).
2. Independent biometric similarity matching (YuNet + SFace, local, real scores).
3. Cryptographic evidence fingerprinting (SHA-256 of URL + image bytes).
4. Blockchain anchoring (Sepolia `storeRecord`, live tx `0xc1c27d821a112f9f458429f5c61d122b644c4fb15adf8f452ada9b50db9ac012`, block 11634046).
5. Tamper-evident re-verification (byte-flip → mismatch detected).

## Known limitations

1. Search accuracy depends on photo quality and public presence. No public face = no results.
2. SerpAPI free tier: 100 searches/month.
3. Sepolia is a testnet with no monetary value.
4. Haar cascades work best on front-facing, well-lit photos.
5. Open web only. Private accounts never appear.
6. Candidate thumbnails are small; low-resolution faces score lower and may fall below threshold even when related. Scores are shown precisely so the evidence can be judged.

## Pre-launch status

- [x] Favicon (`src/app/icon.svg`), no "made with AI" tags
- [x] Privacy + Terms pages with real content
- [x] `.env.example` documented, `.env` files gitignored
- [ ] Screen recording (run: upload → detect → search → verify → re-verify)
- [ ] Public GitHub push (verify no `.env` committed with `git status`)
