const { ethers } = require("hardhat");

async function main() {
  console.log("Deploying VeraScan contract...");

  const VeraScan = await ethers.getContractFactory("VeraScan");
  const verascan = await VeraScan.deploy();
  await verascan.waitForDeployment();

  const address = await verascan.getAddress();
  console.log(`VeraScan deployed to: ${address}`);
  console.log("");
  console.log("Add this to your .env file:");
  console.log(`CONTRACT_ADDRESS=${address}`);
  console.log(`NEXT_PUBLIC_CONTRACT_ADDRESS=${address}`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
