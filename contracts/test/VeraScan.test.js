const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("VeraScan", function () {
  let verascan;
  let owner;
  let addr1;

  const sampleHash = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2";
  const sampleUrl = "https://linkedin.com/in/johndoe";
  const sampleId = ethers.id("test-record-1");

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const VeraScan = await ethers.getContractFactory("VeraScan");
    verascan = await VeraScan.deploy();
    await verascan.waitForDeployment();
  });

  describe("storeRecord", function () {
    it("should store a new record", async function () {
      const tx = await verascan.storeRecord(sampleId, sampleHash, sampleUrl);
      await tx.wait();

      const record = await verascan.getRecord(sampleId);
      expect(record.dataHash).to.equal(sampleHash);
      expect(record.sourceUrl).to.equal(sampleUrl);
      expect(record.verifier).to.equal(owner.address);
      expect(record.exists).to.be.true;
    });

    it("should emit RecordStored event", async function () {
      await expect(verascan.storeRecord(sampleId, sampleHash, sampleUrl))
        .to.emit(verascan, "RecordStored")
        .withArgs(sampleId, sampleHash, sampleUrl, (v) => v > 0, owner.address);
    });

    it("should increment recordCount", async function () {
      expect(await verascan.recordCount()).to.equal(0);
      await verascan.storeRecord(sampleId, sampleHash, sampleUrl);
      expect(await verascan.recordCount()).to.equal(1);
    });

    it("should reject duplicate record IDs", async function () {
      await verascan.storeRecord(sampleId, sampleHash, sampleUrl);
      await expect(
        verascan.storeRecord(sampleId, sampleHash, sampleUrl)
      ).to.be.revertedWith("Record already exists");
    });

    it("should reject empty data hash", async function () {
      await expect(
        verascan.storeRecord(sampleId, "", sampleUrl)
      ).to.be.revertedWith("Data hash cannot be empty");
    });
  });

  describe("verifyRecord", function () {
    beforeEach(async function () {
      await verascan.storeRecord(sampleId, sampleHash, sampleUrl);
    });

    it("should return true for matching hash", async function () {
      const result = await verascan.verifyRecord.staticCall(sampleId, sampleHash);
      expect(result).to.be.true;
    });

    it("should return false for non-matching hash", async function () {
      const wrongHash = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";
      const result = await verascan.verifyRecord.staticCall(sampleId, wrongHash);
      expect(result).to.be.false;
    });

    it("should emit RecordVerified event", async function () {
      await expect(verascan.verifyRecord(sampleId, sampleHash))
        .to.emit(verascan, "RecordVerified");
    });

    it("should revert for non-existent record", async function () {
      const fakeId = ethers.id("does-not-exist");
      await expect(
        verascan.verifyRecord(fakeId, sampleHash)
      ).to.be.revertedWith("Record not found");
    });
  });

  describe("getRecord", function () {
    it("should return stored record data", async function () {
      await verascan.storeRecord(sampleId, sampleHash, sampleUrl);
      const record = await verascan.getRecord(sampleId);

      expect(record.dataHash).to.equal(sampleHash);
      expect(record.sourceUrl).to.equal(sampleUrl);
      expect(record.verifier).to.equal(owner.address);
      expect(record.exists).to.be.true;
      expect(record.timestamp).to.be.gt(0);
    });

    it("should revert for non-existent record", async function () {
      const fakeId = ethers.id("does-not-exist");
      await expect(verascan.getRecord(fakeId)).to.be.revertedWith("Record not found");
    });
  });
});
