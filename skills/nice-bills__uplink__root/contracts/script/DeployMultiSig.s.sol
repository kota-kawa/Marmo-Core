// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "lib/forge-std/src/Script.sol";
import {console} from "lib/forge-std/src/console.sol";
import {AgentRegistry} from "../src/AgentRegistry.sol";
import {PlatformFeeManager} from "../src/PlatformFeeManager.sol";
import {MultiSigTreasury} from "../src/MultiSigTreasury.sol";
import {CampaignFactory} from "../src/CampaignFactory.sol";

/**
 * @title DeployMultiSig
 * @notice Deployment script for multi-sig treasury system
 * @dev Run with: forge script script/DeployMultiSig.s.sol --rpc-url <RPC> --broadcast
 */
contract DeployMultiSig is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        // Load environment variables
        address genesisBot = vm.envAddress("GENESIS_BOT_ADDRESS");
        address feeRecipient = vm.envAddress("FEE_RECIPIENT_ADDRESS");
        
        require(genesisBot != address(0), "Genesis bot address not set");
        require(feeRecipient != address(0), "Fee recipient address not set");

        vm.startBroadcast(deployerPrivateKey);

        console.log("========================================");
        console.log("Deploying Genesis Multi-Sig System");
        console.log("========================================");
        console.log("Genesis Bot:", genesisBot);
        console.log("Fee Recipient:", feeRecipient);
        console.log("");

        // 1. Deploy AgentRegistry
        uint256 registrationFee = 0.1 ether;
        AgentRegistry registry = new AgentRegistry(registrationFee);
        console.log("1. AgentRegistry deployed at:", address(registry));
        console.log("   Registration fee:", registrationFee);

        // 2. Deploy PlatformFeeManager
        PlatformFeeManager feeManager = new PlatformFeeManager(feeRecipient);
        console.log("2. PlatformFeeManager deployed at:", address(feeManager));

        // 3. Deploy MultiSigTreasury
        MultiSigTreasury treasury = new MultiSigTreasury(
            genesisBot,
            address(feeManager)
        );
        console.log("3. MultiSigTreasury deployed at:", address(treasury));

        // 4. Deploy CampaignFactory
        CampaignFactory factory = new CampaignFactory(
            address(registry),
            address(feeManager),
            address(treasury)
        );
        console.log("4. CampaignFactory deployed at:", address(factory));

        console.log("");
        console.log("========================================");
        console.log("Deployment Complete!");
        console.log("========================================");
        console.log("");
        console.log("Contract Addresses:");
        console.log("  AgentRegistry:     ", address(registry));
        console.log("  PlatformFeeManager:", address(feeManager));
        console.log("  MultiSigTreasury:  ", address(treasury));
        console.log("  CampaignFactory:   ", address(factory));
        console.log("");
        console.log("Configuration:");
        console.log("  Genesis Bot:       ", genesisBot);
        console.log("  Fee Recipient:     ", feeRecipient);
        console.log("  Multi-sig Threshold: $300");
        console.log("  Removal Fee Range:  1-2%");
        console.log("  Required Confirms:  2-of-3");

        vm.stopBroadcast();

        // Write deployment info to file
        string memory deploymentInfo = string.concat(
            "GENESIS_MULTISIG_DEPLOYMENT\n",
            "===========================\n\n",
            "Network: ", vm.toString(block.chainid), "\n",
            "Timestamp: ", vm.toString(block.timestamp), "\n\n",
            "CONTRACTS\n",
            "---------\n",
            "AgentRegistry: ", vm.toString(address(registry)), "\n",
            "PlatformFeeManager: ", vm.toString(address(feeManager)), "\n",
            "MultiSigTreasury: ", vm.toString(address(treasury)), "\n",
            "CampaignFactory: ", vm.toString(address(factory)), "\n\n",
            "CONFIGURATION\n",
            "-------------\n",
            "GenesisBot: ", vm.toString(genesisBot), "\n",
            "FeeRecipient: ", vm.toString(feeRecipient), "\n"
        );

        vm.writeFile("deployment-multisig.txt", deploymentInfo);
        console.log("");
        console.log("Deployment info saved to: deployment-multisig.txt");
    }
}

/**
 * @title DeployMultiSigTestnet
 * @notice Testnet deployment with mock addresses
 */
contract DeployMultiSigTestnet is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);

        // Use deployer as Genesis bot and fee recipient for testing
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("Deploying to testnet with deployer as Genesis bot");
        console.log("Deployer:", deployer);

        // Deploy all contracts
        uint256 registrationFee = 0.01 ether; // Lower fee for testnet
        AgentRegistry registry = new AgentRegistry(registrationFee);
        PlatformFeeManager feeManager = new PlatformFeeManager(deployer);
        MultiSigTreasury treasury = new MultiSigTreasury(deployer, address(feeManager));
        CampaignFactory factory = new CampaignFactory(
            address(registry),
            address(feeManager),
            address(treasury)
        );

        console.log("Contracts deployed:");
        console.log("  Registry:    ", address(registry));
        console.log("  FeeManager:  ", address(feeManager));
        console.log("  Treasury:    ", address(treasury));
        console.log("  Factory:     ", address(factory));

        vm.stopBroadcast();
    }
}
