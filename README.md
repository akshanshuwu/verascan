# VeraScan

### Face Identification & Blockchain Verification

VeraScan is a complete web application that detects and encodes a face, discovers matching public web/social-media content using genuine reverse-image search, independently verifies candidate faces, and anchors the verified evidence on Ethereum Sepolia.

## Try VeraScan

**No installation is required. The complete project is available as a live website.**

**[Live Demo](YOUR_LIVE_WEBSITE_URL)**

From the website you can:

- Upload a face image
- Detect and encode the face
- Search the public web using Google Lens
- Discover social-media matches
- Independently verify candidate faces using SFace
- View biometric similarity scores
- Generate a SHA-256 evidence fingerprint
- Store the fingerprint on Ethereum Sepolia
- Re-verify the record directly against the blockchain
- Detect tampering by comparing fingerprints

---

## How It Works

```text
Upload Face
     ↓
Face Detection + Encoding
     ↓
Google Lens Reverse Search
     ↓
Candidate Discovery
     ↓
Independent Face Verification
     ↓
SHA-256 Evidence Fingerprint
     ↓
Ethereum Sepolia
     ↓
Blockchain Re-verification
```

**Google Lens is used for discovery only.** VeraScan independently compares the uploaded face with discovered candidate images using **YuNet + SFace 128-D embeddings** and cosine similarity.

### Tech Stack

- **Frontend:** Next.js 16, React 19
- **Backend:** FastAPI, Python
- **Face Recognition:** OpenCV Haar Cascade, YuNet, SFace
- **Reverse Search:** SerpAPI Google Lens
- **Fingerprinting:** SHA-256
- **Blockchain:** Ethereum Sepolia
- **Smart Contract:** Solidity

---

# Run Locally

You can run VeraScan in three ways:

### 1. Live Website — Recommended

Use the live demo above. No setup required.

### 2. Full Local Application

Runs both the Next.js frontend and FastAPI backend.

### 3. Backend Only

The core pipeline can also run without the frontend — via the terminal CLI
(real end-to-end scan, receipt, re-verification and tamper demo) or through
the FastAPI API/Swagger interface at:

```text
http://localhost:8000/docs
```

```bash
cd backend
source venv/bin/activate
python main.py scan --image ../download.jpeg
python main.py verify --record <record_id>
python main.py verify --record <record_id> --tamper
```

`scan` detects the face, encodes it (YuNet + SFace), runs the SerpAPI Google
Lens search, verifies candidates by biometric similarity, fingerprints the
evidence with SHA-256, anchors it on Sepolia with `storeRecord`, reads the
record back, and saves a local receipt to
`backend/receipts/receipt_<timestamp>.json` (no keys stored). `verify`
compares the receipt evidence against the on-chain fingerprint (`PASS`/`FAIL`);
`--tamper` flips one evidence byte in memory only and demonstrates the
mismatch. Each scan spends one SerpAPI search plus one Sepolia transaction; if
no candidate passes the similarity threshold, nothing is written on-chain.

---

## Local Setup

### Requirements

- Python 3.14
- Node.js 18+
- npm
- Internet connection
- SerpAPI API key
- Ethereum Sepolia RPC
- Sepolia wallet with test ETH for blockchain transactions

### 1. Clone

```bash
git clone https://github.com/akshanshuwu/verascan.git
cd verascan
```

### 2. Backend

```bash
cd backend
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SERPAPI_KEY=your_serpapi_key
FACE_MATCH_THRESHOLD=0.50
ALCHEMY_RPC_URL=your_alchemy_sepolia_rpc
CONTRACT_ADDRESS=0x0fb9824673d027Fb2f2fC629706C2e1E24C39408
DEPLOYER_PRIVATE_KEY=your_sepolia_private_key
```

Start the backend:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend

In a new terminal:

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CONTRACT_ADDRESS=0x0fb9824673d027Fb2f2fC629706C2e1E24C39408
NEXT_PUBLIC_ALCHEMY_RPC_URL=your_alchemy_sepolia_rpc
```

Start:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## Blockchain

VeraScan already has a deployed contract on **Ethereum Sepolia**, so no deployment is required.

```text
Contract:
0x0fb9824673d027Fb2f2fC629706C2e1E24C39408

Network:
Ethereum Sepolia

Chain ID:
11155111
```

A private key is only required when submitting a new blockchain transaction. Read-only verification does not require one.

---

## Evidence Verification

For every verified candidate, VeraScan creates:

```text
SHA-256(source URL + exact downloaded image bytes)
```

The fingerprint is stored on Ethereum Sepolia.

The image and face embeddings are **not stored on-chain**.

During re-verification, the fingerprint is recomputed and compared with the blockchain record. If the evidence changes, the fingerprints no longer match and tampering is detected.

> The biometric similarity score represents similarity between face embeddings; it is not a probability of identity.

---

## Limitations

- Google Lens can only discover public/indexed content.
- A facial match does not prove social-media account ownership.
- Face-matching thresholds are not production-grade biometric calibration.
- Ethereum Sepolia is a testnet.
- The underlying social-media content can change after verification.
- Reverse-image search requires temporarily making the search image accessible to the external search service.

---

## Testing

Backend:

```bash
cd backend
python -m pytest tests/ -v
```

Smart contracts:

```bash
cd contracts
npx hardhat test
```

---

## Project Structure

```text
verascan/
├── backend/       # FastAPI + face recognition pipeline
├── frontend/      # Next.js web application
├── contracts/     # Ethereum smart contract
├── README.md
├── prd.md
├── implementation_plan.md
└── .env.example
```

---

## Hacker House Goa 2026

Built for **Hacker House Goa 2026 — Task 3: Face Identification & Blockchain Verification**

**Face Detection → Face Encoding → Genuine Web Search → Independent Verification → SHA-256 Fingerprinting → Blockchain Anchoring → Re-verification**