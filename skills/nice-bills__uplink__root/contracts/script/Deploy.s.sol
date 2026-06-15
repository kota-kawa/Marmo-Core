// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/AgentRegistry.sol";
import "../src/PlatformFeeManager.sol";
import "../src/MultiSigTreasury.sol";
import "../src/CampaignFactory.sol";

/**
 * @title Deploy
 * @notice Deployment script for Agent Fundraising Platform contracts
 * @dev Deploys all contracts in correct order with proper configuration
 */
contract Deploy is Script {
    /// @notice Registration fee for agents
    uint256 public constant REGISTRATION_FEE = 0.1 ether;

    /// @notice Platform fee recipient address
    address public feeRecipient;

    /// @notice Deployed AgentRegistry contract
    AgentRegistry public agentRegistry;

    /// @notice Deployed PlatformFeeManager contract
    PlatformFeeManager public feeManager;

    /// @notice Deployed CampaignFactory contract
    CampaignFactory public campaignFactory;

    /// @notice Deployed MultiSigTreasury contract
    MultiSigTreasury public multiSigTreasury;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployerAddress = vm.addr(deployerPrivateKey);
        vm.startBroadcast(deployerPrivateKey);

        console.log("Deployer address:", deployerAddress);
        console.log("Deployer balance:", deployerAddress.balance);

        // 1. Deploy PlatformFeeManager
        feeRecipient = deployerAddress; // Set deployer as fee recipient initially
        feeManager = new PlatformFeeManager(feeRecipient);
        console.log("PlatformFeeManager deployed at:", address(feeManager));
        console.log("Fee recipient:", feeRecipient);

        // 2. Deploy AgentRegistry
        agentRegistry = new AgentRegistry(REGISTRATION_FEE);
        console.log("AgentRegistry deployed at:", address(agentRegistry));
        console.log("Registration fee:", REGISTRATION_FEE);

        // 3. Configure AgentRegistry
        agentRegistry.setPlatformFeeManager(address(feeManager));
        console.log("AgentRegistry configured with PlatformFeeManager");

        // 4. Deploy MultiSigTreasury
        // Use deployer as genesis bot for testing
        multiSigTreasury = new MultiSigTreasury(deployerAddress, address(feeManager));
        console.log("MultiSigTreasury deployed at:", address(multiSigTreasury));
        console.log("Genesis bot:", deployerAddress);

        // 5. Deploy CampaignFactory
        campaignFactory = new CampaignFactory(
            address(agentRegistry),
            address(feeManager),
            address(multiSigTreasury)
        );
        console.log("CampaignFactory deployed at:", address(campaignFactory));
        console.log("AgentRegistry address:", address(agentRegistry));
        console.log("PlatformFeeManager address:", address(feeManager));
        console.log("MultiSigTreasury address:", address(multiSigTreasury));

        // 6. Verify deployments
        _verifyDeployments();

        // 7. Log deployment summary
        _logSummary();

        vm.stopBroadcast();
    }

    /**
     * @notice Verify that all contracts are deployed correctly
     */
    function _verifyDeployments() internal view {
        require(address(agentRegistry) != address(0), "AgentRegistry not deployed");
        require(address(feeManager) != address(0), "PlatformFeeManager not deployed");
        require(address(multiSigTreasury) != address(0), "MultiSigTreasury not deployed");
        require(address(campaignFactory) != address(0), "CampaignFactory not deployed");

        require(feeManager.feeRecipient() != address(0), "Fee recipient not set");
        require(agentRegistry.registrationFee() == REGISTRATION_FEE, "Registration fee not set");

        console.log("All deployments verified successfully");
    }

    /**
     * @notice Log deployment summary
     */
    function _logSummary() internal view {
        console.log("\n=== Deployment Summary ===");
        console.log("AgentRegistry:", address(agentRegistry));
        console.log("PlatformFeeManager:", address(feeManager));
        console.log("MultiSigTreasury:", address(multiSigTreasury));
        console.log("CampaignFactory:", address(campaignFactory));
        console.log("Registration Fee:", REGISTRATION_FEE);
        console.log("Platform Fee:", feeManager.PLATFORM_FEE_BPS(), "bps (0.5%)");
        console.log("Multi-sig Threshold: $300");
        console.log("Removal Fee Range: 1-2%");
        console.log("Fee Recipient:", feeRecipient);
        console.log("========================\n");
    }

    /**
     * @notice Deploy to Monaco testnet
     */
    function runMonaco() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployerAddress = vm.addr(deployerPrivateKey);

        vm.startBroadcast(deployerPrivateKey);

        console.log("Deploying to Monaco testnet...");
        console.log("Deployer address:", deployerAddress);

        // Deploy contracts
        feeRecipient = deployerAddress;
        feeManager = new PlatformFeeManager(feeRecipient);
        agentRegistry = new AgentRegistry(REGISTRATION_FEE);
        
        // Deploy MultiSigTreasury with deployer as genesis bot
        multiSigTreasury = new MultiSigTreasury(deployerAddress, address(feeManager));
        
        campaignFactory = new CampaignFactory(
            address(agentRegistry),
            address(feeManager),
            address(multiSigTreasury)
        );

        // Configure
        agentRegistry.setPlatformFeeManager(address(feeManager));

        console.log("\n=== Monaco Testnet Deployment ===");
        console.log("AgentRegistry:", address(agentRegistry));
        console.log("PlatformFeeManager:", address(feeManager));
        console.log("MultiSigTreasury:", address(multiSigTreasury));
        console.log("CampaignFactory:", address(campaignFactory));
        console.log("================================\n");

        vm.stopBroadcast();
    }
}
