// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/CampaignFactory.sol";
import "../src/AgentRegistry.sol";
import "../src/PlatformFeeManager.sol";
import "../src/MultiSigTreasury.sol";

/**
 * @title SimpleCampaignTest
 * @notice Simple test to debug the CampaignFactory issue
 */
contract SimpleCampaignTest is Test {
    CampaignFactory public factory;
    AgentRegistry public registry;
    PlatformFeeManager public feeManager;
    MultiSigTreasury public multiSigTreasury;

    address public owner;
    address public feeRecipient;
    address public genesisBot;
    address public user1;
    address public donor1;
    uint256 public agentId;

    function setUp() public {
        owner = address(this);
        feeRecipient = address(0x1);
        genesisBot = address(0x6);
        user1 = address(0x2);
        donor1 = address(0x3);

        vm.deal(user1, 10 ether);
        vm.deal(donor1, 10 ether);

        // Deploy contracts
        registry = new AgentRegistry(0);
        feeManager = new PlatformFeeManager(feeRecipient);
        multiSigTreasury = new MultiSigTreasury(genesisBot, address(feeManager));
        factory = new CampaignFactory(address(registry), address(feeManager), address(multiSigTreasury));

        // Register agent
        vm.startPrank(user1);
        agentId = registry.register{value: 0}("ipfs://QmAgent1", "@agent1");
        vm.stopPrank();

        console.log("Registry deployed at:", address(registry));
        console.log("FeeManager deployed at:", address(feeManager));
        console.log("Factory deployed at:", address(factory));
        console.log("Agent ID:", agentId);
        console.log("FeeManager owner:", feeManager.owner());
        console.log("FeeRecipient:", feeRecipient);
    }

    function test_SimpleContribute() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        console.log("Campaign ID:", campaignId);

        // Check the agent ownership
        AgentRegistry.Agent memory agent = registry.getAgent(agentId);
        console.log("Agent owner:", agent.owner);
        console.log("Agent is active:", agent.isActive);

        // Check the campaign details
        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        console.log("Campaign agentId:", campaign.agentId);
        console.log("Campaign goal:", campaign.goal);
        console.log("Campaign isActive:", campaign.isActive);

        uint256 donation = 0.1 ether;

        vm.startPrank(donor1);
        console.log("Donor balance before:", donor1.balance);
        console.log("Factory balance before:", address(factory).balance);
        console.log("FeeManager balance before:", address(feeManager).balance);

        try factory.contribute{value: donation}(campaignId) {
            console.log("Contribution successful");
        } catch Error(string memory reason) {
            console.log("Contribution failed with reason:", reason);
        } catch {
            console.log("Contribution failed without reason");
        }

        console.log("Donor balance after:", donor1.balance);
        console.log("Factory balance after:", address(factory).balance);
        console.log("FeeManager balance after:", address(feeManager).balance);

        campaign = factory.getCampaign(campaignId);

        console.log("Campaign raised:", campaign.raised);
    }
}
