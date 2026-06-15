// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SimplePriceOracle.sol";
import "../src/PlatformFeeManager.sol";
import "../src/MultiSigTreasury.sol";
import "../src/AgentRegistry.sol";
import "../src/CampaignFactory.sol";

/**
 * @title RedeployAll
 * @notice Full redeployment with security fixes
 * @dev Deploys all contracts including the new price oracle
 */
contract RedeployAll is Script {
    /// @notice Registration fee for agents (set to 0 for hackathon demo)
    uint256 public constant REGISTRATION_FEE = 0 ether;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployerAddress = vm.addr(deployerPrivateKey);
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== Full Redeployment with Security Fixes ===");
        console.log("Deployer:", deployerAddress);
        console.log("Chain: Monad Testnet");
        console.log("");

        // 1. Deploy PlatformFeeManager
        address feeRecipient = deployerAddress;
        PlatformFeeManager feeManager = new PlatformFeeManager(feeRecipient);
        console.log("PlatformFeeManager:", address(feeManager));

        // 2. Deploy AgentRegistry
        AgentRegistry agentRegistry = new AgentRegistry(REGISTRATION_FEE);
        console.log("AgentRegistry:", address(agentRegistry));
        agentRegistry.setPlatformFeeManager(address(feeManager));

        // 3. Deploy SimplePriceOracle
        SimplePriceOracle priceOracle = new SimplePriceOracle(deployerAddress);
        console.log("SimplePriceOracle:", address(priceOracle));
        
        // Set initial ETH price ($2500.00)
        priceOracle.updatePrice(250000);
        console.log("Initial price: $2500.00");

        // 4. Deploy MultiSigTreasury (with security fixes)
        MultiSigTreasury multiSigTreasury = new MultiSigTreasury(
            deployerAddress,  // genesis bot
            address(feeManager)
        );
        console.log("MultiSigTreasury:", address(multiSigTreasury));
        
        // Connect price oracle
        multiSigTreasury.setPriceOracle(address(priceOracle));
        console.log("Price oracle connected");

        // 5. Deploy CampaignFactory
        CampaignFactory campaignFactory = new CampaignFactory(
            address(agentRegistry),
            address(feeManager),
            address(multiSigTreasury)
        );
        console.log("CampaignFactory:", address(campaignFactory));

        // 6. Authorize factory in treasury
        multiSigTreasury.setAuthorizedFactory(address(campaignFactory));
        console.log("Factory authorized in treasury");

        console.log("");
        console.log("=== Deployment Complete ===");
        console.log("Copy these addresses to your .env:");
        console.log("");
        console.log("AGENT_REGISTRY_ADDRESS=", address(agentRegistry));
        console.log("PLATFORM_FEE_MANAGER_ADDRESS=", address(feeManager));
        console.log("CAMPAIGN_FACTORY_ADDRESS=", address(campaignFactory));
        console.log("MULTISIG_TREASURY_ADDRESS=", address(multiSigTreasury));
        console.log("PRICE_ORACLE_ADDRESS=", address(priceOracle));
        console.log("===========================");

        vm.stopBroadcast();
    }
}
