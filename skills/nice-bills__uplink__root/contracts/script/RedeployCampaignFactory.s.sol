// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/AgentRegistry.sol";
import "../src/PlatformFeeManager.sol";
import "../src/MultiSigTreasury.sol";
import "../src/CampaignFactory.sol";

/**
 * @title RedeployCampaignFactory
 * @notice Redeploy only the CampaignFactory with correct constructor args
 */
contract RedeployCampaignFactory is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployerAddress = vm.addr(deployerPrivateKey);
        
        vm.startBroadcast(deployerPrivateKey);

        // Existing contract addresses (from previous deployment)
        address agentRegistry = 0x3f4D1B21251409075a0FB8E1b0C0A30B23f05653;
        address feeManager = 0x77107B62a9149F0073F40846af477fa6f9E3543A;
        
        // Deploy MultiSigTreasury first (if not deployed)
        MultiSigTreasury multiSigTreasury = new MultiSigTreasury(
            deployerAddress,  // Genesis bot (you)
            feeManager
        );
        console.log("MultiSigTreasury deployed at:", address(multiSigTreasury));

        // Deploy CampaignFactory with ALL 3 constructor arguments
        CampaignFactory campaignFactory = new CampaignFactory(
            agentRegistry,
            feeManager,
            address(multiSigTreasury)  // This was missing!
        );
        console.log("CampaignFactory deployed at:", address(campaignFactory));
        
        console.log("\n=== DEPLOYMENT SUMMARY ===");
        console.log("AgentRegistry:", agentRegistry);
        console.log("PlatformFeeManager:", feeManager);
        console.log("MultiSigTreasury:", address(multiSigTreasury));
        console.log("CampaignFactory:", address(campaignFactory));
        console.log("==========================");

        vm.stopBroadcast();
    }
}
