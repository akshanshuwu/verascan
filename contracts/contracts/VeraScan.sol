// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title VeraScan - Face identification record verification
/// @notice Stores and verifies tamper-evident records of web discoveries
contract VeraScan {
    struct Record {
        string dataHash;
        string sourceUrl;
        uint256 timestamp;
        address verifier;
        bool exists;
    }

    mapping(bytes32 => Record) public records;
    uint256 public recordCount;

    event RecordStored(
        bytes32 indexed id,
        string dataHash,
        string sourceUrl,
        uint256 timestamp,
        address indexed verifier
    );

    event RecordVerified(
        bytes32 indexed id,
        bool matched,
        uint256 verifiedAt
    );

    /// @notice Store a new verification record on-chain
    /// @param _id Unique identifier for this record
    /// @param _dataHash SHA-256 hash of the discovered data
    /// @param _sourceUrl URL where the data was found
    function storeRecord(
        bytes32 _id,
        string calldata _dataHash,
        string calldata _sourceUrl
    ) external {
        require(!records[_id].exists, "Record already exists");
        require(bytes(_dataHash).length > 0, "Data hash cannot be empty");

        records[_id] = Record({
            dataHash: _dataHash,
            sourceUrl: _sourceUrl,
            timestamp: block.timestamp,
            verifier: msg.sender,
            exists: true
        });

        recordCount++;

        emit RecordStored(_id, _dataHash, _sourceUrl, block.timestamp, msg.sender);
    }

    /// @notice Verify a record by comparing a data hash against the stored hash
    /// @param _id Record identifier to verify
    /// @param _dataHash Hash to compare against the stored record
    /// @return matched Whether the provided hash matches the stored hash
    function verifyRecord(
        bytes32 _id,
        string calldata _dataHash
    ) external returns (bool matched) {
        require(records[_id].exists, "Record not found");

        matched = keccak256(bytes(records[_id].dataHash)) == keccak256(bytes(_dataHash));

        emit RecordVerified(_id, matched, block.timestamp);

        return matched;
    }

    /// @notice Retrieve a stored record
    /// @param _id Record identifier to look up
    /// @return The full Record struct
    function getRecord(bytes32 _id) external view returns (Record memory) {
        require(records[_id].exists, "Record not found");
        return records[_id];
    }
}
