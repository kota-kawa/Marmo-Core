// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/CampaignFactory.sol";
import "../src/AgentRegistry.sol";
import "../src/PlatformFeeManager.sol";
import "../src/MultiSigTreasury.sol";

/**
 * @title CampaignFactoryTest
 * @notice Comprehensive test suite for CampaignFactory contract
 * @dev Tests campaign creation, contributions, withdrawals, and fee collection
 */
contract CampaignFactoryTest is Test {
    CampaignFactory public factory;
    AgentRegistry public registry;
    PlatformFeeManager public feeManager;
    MultiSigTreasury public multiSigTreasury;

    address public owner;
    address public feeRecipient;
    address public genesisBot;
    address public user1;
    address public user2;
    address public donor1;
    address public donor2;

    uint256 public agentId1;
    uint256 public agentId2;
    uint256 public campaignId1;
    uint256 public campaignId2;

    event CampaignCreated(
        uint256 indexed campaignId,
        uint256 indexed agentId,
        uint256 goal,
        uint256 deadline
    );
    event DonationReceived(
        uint256 indexed campaignId,
        address indexed donor,
        uint256 amount
    );
    event FundsWithdrawn(uint256 indexed campaignId, uint256 amount);

    function setUp() public {
        owner = address(this);
        feeRecipient = address(0x1);
        genesisBot = address(0x6); // Genesis bot address
        user1 = address(0x2);
        user2 = address(0x3);
        donor1 = address(0x4);
        donor2 = address(0x5);

        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);
        vm.deal(donor1, 10 ether);
        vm.deal(donor2, 10 ether);

        // Deploy contracts
        registry = new AgentRegistry(0);
        feeManager = new PlatformFeeManager(feeRecipient);
        multiSigTreasury = new MultiSigTreasury(genesisBot, address(feeManager));
        factory = new CampaignFactory(address(registry), address(feeManager), address(multiSigTreasury));

        // Register agents
        vm.startPrank(user1);
        agentId1 = registry.register{value: 0}("ipfs://QmAgent1", "@agent1");
        vm.stopPrank();

        vm.startPrank(user2);
        agentId2 = registry.register{value: 0}("ipfs://QmAgent2", "@agent2");
        vm.stopPrank();
    }

    function test_CreateCampaign_Success() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        assertEq(campaignId, 1);
        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        assertEq(campaign.campaignId, campaignId);
        assertEq(campaign.agentId, agentId1);
        assertEq(campaign.goal, goal);
        assertEq(campaign.raised, 0);
        assertTrue(campaign.deadline > block.timestamp);
        assertEq(campaign.metadataURI, metadataURI);
        assertTrue(campaign.isActive);
    }

    function test_CreateCampaign_NoDeadline() public {
        uint256 goal = 1 ether;
        uint256 duration = 0;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        assertEq(campaign.deadline, 0);
    }

    function test_CreateCampaign_NotAgentOwner() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user2);
        vm.expectRevert("Not agent owner");
        factory.createCampaign(agentId1, goal, duration, metadataURI, address(0));
        vm.stopPrank();
    }

    function test_CreateCampaign_AgentNotActive() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        registry.deactivateAgent(agentId1);
        vm.expectRevert("Agent not active");
        factory.createCampaign(agentId1, goal, duration, metadataURI, address(0));
        vm.stopPrank();
    }

    function test_CreateCampaign_ZeroGoal() public {
        uint256 goal = 0;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        vm.expectRevert("Goal must be greater than 0");
        factory.createCampaign(agentId1, goal, duration, metadataURI, address(0));
        vm.stopPrank();
    }

    function test_Contribute_Success() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        uint256 donation = 0.1 ether;

        vm.startPrank(donor1);
        factory.contribute{value: donation}(campaignId);
        vm.stopPrank();

        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        uint256 expectedRaised = (donation * 9950) / 10000; // 9950/10000 = 99.5% (0.5% fee)
        assertEq(campaign.raised, expectedRaised);
        assertEq(factory.campaignFunds(campaignId), expectedRaised);
        assertEq(factory.getDonorContribution(campaignId, donor1), expectedRaised);
    }

    function test_Contribute_ExpiredCampaign() public {
        uint256 goal = 1 ether;
        uint256 duration = 1 seconds;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.warp(block.timestamp + 2 days);

        vm.startPrank(donor1);
        vm.expectRevert("Campaign expired");
        factory.contribute{value: 0.1 ether}(campaignId);
        vm.stopPrank();
    }

    function test_Contribute_InactiveCampaign() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        factory.deactivateCampaign(campaignId);
        vm.stopPrank();

        vm.startPrank(donor1);
        vm.expectRevert("Campaign not active");
        factory.contribute{value: 0.1 ether}(campaignId);
        vm.stopPrank();
    }

    function test_Contribute_ZeroDonation() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        vm.expectRevert("Donation must be greater than 0");
        factory.contribute{value: 0}(campaignId);
        vm.stopPrank();
    }

    function test_MultipleContributions() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        factory.contribute{value: 0.1 ether}(campaignId);
        factory.contribute{value: 0.2 ether}(campaignId);
        vm.stopPrank();

        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        uint256 expectedRaised1 = (0.1 ether * 9950) / 10000;
        uint256 expectedRaised2 = (0.2 ether * 9950) / 10000;
        assertEq(campaign.raised, expectedRaised1 + expectedRaised2);
        assertEq(
            factory.campaignFunds(campaignId),
            expectedRaised1 + expectedRaised2
        );
        assertEq(
            factory.getDonorContribution(campaignId, donor1),
            expectedRaised1 + expectedRaised2
        );
    }

    function test_WithdrawFunds_Success() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        factory.contribute{value: 0.1 ether}(campaignId);
        vm.stopPrank();

        // Check campaign funds before withdrawal
        uint256 fundsBefore = factory.campaignFunds(campaignId);
        console.log("Campaign funds before withdrawal:", fundsBefore);

        uint256 balanceBefore = user1.balance;

        uint256 expectedRaised = (0.1 ether * 9950) / 10000;
        
        vm.startPrank(user1);
        factory.withdrawFunds(campaignId, expectedRaised);
        vm.stopPrank();

        uint256 balanceAfter = user1.balance;

        console.log("Expected raised amount:", expectedRaised);
        console.log("Balance increase:", balanceAfter - balanceBefore);

        assertEq(balanceAfter - balanceBefore, expectedRaised);

        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        // raised stays immutable (historical metric)
        assertEq(campaign.raised, expectedRaised, "Raised should stay immutable");
        // withdrawn tracks the amount taken out
        assertEq(campaign.withdrawn, expectedRaised, "Withdrawn should track amount");

        uint256 fundsAfter = factory.campaignFunds(campaignId);
        console.log("Campaign funds after withdrawal:", fundsAfter);
        assertEq(fundsAfter, 0, "Campaign funds should be 0");
    }

    function test_WithdrawFunds_NotAgentOwner() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        factory.contribute{value: 0.5 ether}(campaignId);
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert("Not agent owner");
        factory.withdrawFunds(campaignId, 0.1 ether);
        vm.stopPrank();
    }

    function test_WithdrawFunds_NoFunds() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.expectRevert("Amount must be greater than 0");
        factory.withdrawFunds(campaignId, 0);
        vm.stopPrank();

        assertEq(factory.campaignFunds(campaignId), 0);
    }

    function test_DeactivateCampaign_Success() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(user1);
        factory.deactivateCampaign(campaignId);
        vm.stopPrank();

        CampaignFactory.Campaign memory campaign = factory.getCampaign(
            campaignId
        );
        assertFalse(campaign.isActive);
    }

    function test_GetCampaignDonors_Success() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        factory.contribute{value: 0.1 ether}(campaignId);
        vm.stopPrank();

        vm.startPrank(donor2);
        factory.contribute{value: 0.1 ether}(campaignId);
        vm.stopPrank();

        address[] memory donors = factory.getCampaignDonors(campaignId);
        assertEq(donors.length, 2);
        assertTrue(donors[0] == donor1 || donors[0] == donor2);
        assertTrue(donors[1] == donor1 || donors[1] == donor2);
    }

    function test_GetTotalCampaigns() public {
        assertEq(factory.getTotalCampaigns(), 0);

        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        factory.createCampaign(agentId1, goal, duration, metadataURI, address(0));
        assertEq(factory.getTotalCampaigns(), 1);
        vm.stopPrank();

        vm.startPrank(user2);
        factory.createCampaign(agentId2, goal, duration, metadataURI, address(0));
        assertEq(factory.getTotalCampaigns(), 2);
        vm.stopPrank();
    }

    function test_GetCampaign_NotFound() public {
        vm.expectRevert("Campaign not found");
        factory.getCampaign(999);
    }

    function test_MultipleCampaigns() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 id1 = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(user2);
        uint256 id2 = factory.createCampaign(
            agentId2,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        assertEq(id1, 1);
        assertEq(id2, 2);
        assertEq(factory.getTotalCampaigns(), 2);
    }

    function test_FeeCollection() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        factory.contribute{value: 1 ether}(campaignId);
        vm.stopPrank();

        uint256 feeBalance = address(feeManager).balance;
        uint256 expectedFee = (1 ether * 50) / 10000;
        assertEq(feeBalance, expectedFee);

        uint256 campaignBalance = factory.campaignFunds(campaignId);
        uint256 expectedRaised = (1 ether * 9950) / 10000;
        assertEq(campaignBalance, expectedRaised);
    }

    function test_DonorAlreadyContributed() public {
        uint256 goal = 1 ether;
        uint256 duration = 30 days;
        string memory metadataURI = "ipfs://QmCampaign";

        vm.startPrank(user1);
        uint256 campaignId = factory.createCampaign(
            agentId1,
            goal,
            duration,
            metadataURI,
            address(0)
        );
        vm.stopPrank();

        vm.startPrank(donor1);
        factory.contribute{value: 0.1 ether}(campaignId);
        factory.contribute{value: 0.1 ether}(campaignId);
        vm.stopPrank();

        address[] memory donors = factory.getCampaignDonors(campaignId);
        assertEq(donors.length, 1);
        assertEq(donors[0], donor1);
    }
}
