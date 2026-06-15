// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SimplePriceOracle.sol";
import "../src/MultiSigTreasury.sol";

/**
 * @title DeployPriceOracle
 * @notice Deploys the new secure price oracle and updates MultiSigTreasury
 * @dev Run this after the main deployment to add price oracle functionality
 */
contract DeployPriceOracle is Script {
    /// @notice Address of existing MultiSigTreasury
    address payable public constant MULTISIG_TREASURY = payable(0x89E5603db5cA92F7dA5E767CaEB7fdE5e696262E);
    
    /// @notice Genesis bot address (deployer)
    address public genesisBot;
    
    /// @notice Deployed price oracle
    SimplePriceOracle public priceOracle;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        genesisBot = vm.addr(deployerPrivateKey);
        
        vm.startBroadcast(deployerPrivateKey);

        console.log("Deploying price oracle...");
        console.log("Genesis bot:", genesisBot);
        console.log("MultiSigTreasury:", MULTISIG_TREASURY);

        // 1. Deploy SimplePriceOracle
        // Use genesis bot as the updater
        priceOracle = new SimplePriceOracle(genesisBot);
        console.log("SimplePriceOracle deployed at:", address(priceOracle));
        console.log("Updater:", genesisBot);

        // 2. Set the price oracle in MultiSigTreasury
        MultiSigTreasury multiSigTreasury = MultiSigTreasury(MULTISIG_TREASURY);
        multiSigTreasury.setPriceOracle(address(priceOracle));
        console.log("Price oracle set in MultiSigTreasury");

        // 3. Update the initial ETH price (optional - set to current market price)
        // Example: $2500.00 = 250000 cents
        uint256 initialPrice = 250000; // $2500.00
        priceOracle.updatePrice(initialPrice);
        console.log("Initial ETH price set to:", initialPrice, "cents ($2500.00)");

        // 4. Verify setup
        (uint256 price, uint256 timestamp) = priceOracle.getLatestPrice();
        console.log("Oracle price verified:", price, "cents");
        console.log("Oracle timestamp:", timestamp);
        
        bool isStale = priceOracle.isPriceStale();
        console.log("Price is stale:", isStale);

        console.log("\n=== Deployment Summary ===");
        console.log("SimplePriceOracle:", address(priceOracle));
        console.log("MultiSigTreasury:", MULTISIG_TREASURY);
        console.log("Price Oracle Connected: YES");
        console.log("Current Price:", price, "cents");
        console.log("===========================");

        vm.stopBroadcast();
    }
}
